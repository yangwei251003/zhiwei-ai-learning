from __future__ import annotations

import json

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import Settings
from app.core.llm import SparkAPIError
from app.core.security import create_access_token, hash_password
from app.main import create_app
from app.models.database import Message, User
from app.agents.orchestrator import build_agent_graph
from tests.test_agent_graph import dependencies


class FakeGraph:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.inputs: list[dict] = []

    async def astream(self, graph_input, **kwargs):
        self.inputs.append(graph_input)
        assert kwargs == {"stream_mode": ["updates", "custom"], "version": "v2"}
        yield {
            "type": "custom",
            "data": {
                "type": "thinking",
                "agent": "retriever",
                "content": "正在检索",
            },
        }
        if self.fail:
            raise SparkAPIError("upstream unavailable")
        yield {
            "type": "custom",
            "data": {"type": "token", "agent": "response_agent", "content": "你"},
        }
        yield {
            "type": "custom",
            "data": {"type": "token", "agent": "response_agent", "content": "好"},
        }
        yield {
            "type": "updates",
            "data": {"response_agent": {"final_response": "你好"}},
        }


def chat_context(tmp_path, graph: FakeGraph):
    settings = Settings(
        _env_file=None,
        spark_api_key="test-key",
        secret_key="x" * 32,
        database_url=f"sqlite:///{tmp_path / 'chat.db'}",
        auto_create_tables=True,
        faiss_index_path=tmp_path / "index.faiss",
        knowledge_upload_dir=tmp_path / "uploads",
    )
    app = create_app(settings)
    app.state.agent_graph_builder = lambda: graph
    with app.state.session_factory() as db:
        user = User(
            username="learner",
            email="learner@example.com",
            hashed_password=hash_password("LearnerPass123!"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    token = create_access_token(str(user.id), settings)
    return TestClient(app), app, user.id, token


def parse_sse(response_text: str) -> list[dict]:
    return [
        json.loads(line.removeprefix("data: "))
        for line in response_text.splitlines()
        if line.startswith("data: ")
    ]


def test_chat_stream_forwards_graph_events_and_persists_messages(tmp_path) -> None:
    graph = FakeGraph()
    api, app, user_id, token = chat_context(tmp_path, graph)
    with api:
        response = api.post(
            "/api/chat/stream",
            headers={"Authorization": f"Bearer {token}"},
            json={"message": "你好，小智析析"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        assert response.headers["cache-control"] == "no-cache"
        assert response.headers["x-accel-buffering"] == "no"
        events = parse_sse(response.text)
        assert [event["type"] for event in events] == [
            "thinking",
            "token",
            "token",
            "done",
        ]
        assert [event["sequence"] for event in events] == [1, 2, 3, 4]
        assert [event["content"] for event in events if event["type"] == "token"] == [
            "你",
            "好",
        ]
        assert graph.inputs[0]["user_id"] == user_id
        assert graph.inputs[0]["conversation_id"] == events[-1]["conversation_id"]

        with app.state.session_factory() as db:
            messages = list(db.scalars(select(Message).order_by(Message.id)))
            assert [(message.role, message.content) for message in messages] == [
                ("user", "你好，小智析析"),
                ("assistant", "你好"),
            ]


def test_chat_stream_exposes_real_error_then_done_without_fake_answer(tmp_path) -> None:
    api, app, _, token = chat_context(tmp_path, FakeGraph(fail=True))
    with api:
        response = api.post(
            "/api/chat/stream",
            headers={"Authorization": f"Bearer {token}"},
            json={"message": "测试失败"},
        )

        events = parse_sse(response.text)
        assert [event["type"] for event in events] == ["thinking", "error", "done"]
        assert events[1]["message"] == "upstream unavailable"
        with app.state.session_factory() as db:
            messages = list(db.scalars(select(Message).order_by(Message.id)))
            assert [(message.role, message.content) for message in messages] == [
                ("user", "测试失败")
            ]


def test_chat_stream_requires_authentication(tmp_path) -> None:
    api, _, _, _ = chat_context(tmp_path, FakeGraph())
    with api:
        response = api.post("/api/chat/stream", json={"message": "你好"})
        assert response.status_code == 401


def test_chat_api_consumes_real_langgraph_v2_update_shape(tmp_path) -> None:
    deps, _, _, _ = dependencies("general")
    graph = build_agent_graph(deps)
    api, app, _, token = chat_context(tmp_path, graph)

    with api:
        response = api.post(
            "/api/chat/stream",
            headers={"Authorization": f"Bearer {token}"},
            json={"message": "真实图事件"},
        )

        events = parse_sse(response.text)
        assert events[-1]["type"] == "done"
        assert not any(event["type"] == "error" for event in events)
        with app.state.session_factory() as db:
            assistant = db.scalar(select(Message).where(Message.role == "assistant"))
            assert assistant.content == "回答完成"


def test_chat_history_api_lists_and_loads_only_the_current_users_messages(
    tmp_path,
) -> None:
    graph = FakeGraph()
    api, app, user_id, token = chat_context(tmp_path, graph)
    with app.state.session_factory() as db:
        other = User(
            username="other",
            email="other@example.com",
            hashed_password=hash_password("OtherPass123!"),
        )
        db.add(other)
        db.commit()
        db.refresh(other)
    other_token = create_access_token(str(other.id), app.state.settings)

    with api:
        streamed = api.post(
            "/api/chat/stream",
            headers={"Authorization": f"Bearer {token}"},
            json={"message": "历史里的问题"},
        )
        conversation_id = parse_sse(streamed.text)[-1]["conversation_id"]

        listing = api.get(
            "/api/chat/conversations",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert listing.status_code == 200
        assert listing.json()["data"] == [
            {
                "id": conversation_id,
                "title": "历史里的问题",
                "message_count": 2,
                "last_message": "你好",
                "created_at": listing.json()["data"][0]["created_at"],
                "updated_at": listing.json()["data"][0]["updated_at"],
            }
        ]

        detail = api.get(
            f"/api/chat/conversations/{conversation_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert detail.status_code == 200
        assert detail.json()["data"]["user_id"] == user_id
        assert [item["content"] for item in detail.json()["data"]["messages"]] == [
            "历史里的问题",
            "你好",
        ]
        assert (
            api.get(
                f"/api/chat/conversations/{conversation_id}",
                headers={"Authorization": f"Bearer {other_token}"},
            ).status_code
            == 404
        )


def test_chat_history_api_requires_authentication(tmp_path) -> None:
    api, _, _, _ = chat_context(tmp_path, FakeGraph())
    with api:
        assert api.get("/api/chat/conversations").status_code == 401
