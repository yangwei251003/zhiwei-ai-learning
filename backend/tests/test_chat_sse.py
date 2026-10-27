import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import chat
from app.api.knowledge import get_knowledge_service
from app.core.database import Base, get_db
from app.main import app
from app.schemas import ChatRequest


@pytest.fixture
def sse_client(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{(tmp_path / 'sse.db').as_posix()}", connect_args={"check_same_thread": False})
    sessions = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(engine)

    def db_override():
        db = sessions()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = db_override
    with TestClient(app) as client:
        yield client, monkeypatch
    app.dependency_overrides.clear()
    engine.dispose()


def _token(client, username):
    return client.post("/api/auth/register", json={"username": username, "password": "password123"}).json()["access_token"]


def _events(response):
    result, event_name = [], None
    for line in response.iter_lines():
        if line.startswith("event: "):
            event_name = line[7:]
        elif line.startswith("data: "):
            body = json.loads(line[6:])
            assert set(body) == {"type", "payload"}
            assert body["type"] == event_name
            result.append(body)
    return result


def test_stream_searches_before_graph_and_preserves_chunks(sse_client):
    client, monkeypatch = sse_client
    calls = []

    class Rag:
        def search(self, query, user_id, course, top_k):
            calls.append(("rag", top_k))
            return [{"content": "fact"}]

    class Graph:
        async def process_message(self, message, conversation_id, chunks):
            calls.append(("graph", chunks))
            yield {"type": "token", "payload": {"content": "A"}}
            yield {"type": "token", "payload": {"content": "BC"}}

    app.dependency_overrides[get_knowledge_service] = lambda: Rag()
    monkeypatch.setattr(chat, "get_orchestrator", lambda *args: Graph())
    token = _token(client, "stream_user")
    with client.stream("POST", "/api/chat/stream", json={"message": " hi ", "course": " AI "},
                       headers={"Authorization": f"Bearer {token}"}) as response:
        assert response.status_code == 200
        events = _events(response)
    assert calls == [("rag", 5), ("graph", [{"content": "fact"}])]
    assert [event["type"] for event in events] == ["thinking", "token", "token", "done"]
    assert [event["payload"].get("content") for event in events[1:3]] == ["A", "BC"]


def test_stream_requires_jwt_and_rejects_foreign_conversation(sse_client):
    client, _ = sse_client
    assert client.post("/api/chat/stream", json={"message": "hi"}).status_code == 401
    first = _token(client, "owner_user")
    second = _token(client, "other_user")
    # Validation/ownership occurs before retrieval.
    from app.models import Conversation
    db = next(app.dependency_overrides[get_db]())
    try:
        from app.core.security import get_current_user
        owner = client.get("/api/auth/me", headers={"Authorization": f"Bearer {first}"}).json()
        row = Conversation(user_id=owner["id"], role="user", content="x", metadata_json={})
        db.add(row); db.commit(); db.refresh(row)
        response = client.post("/api/chat/stream", json={"message": "hi", "conversation_id": row.id},
                               headers={"Authorization": f"Bearer {second}"})
        assert response.status_code == 403
    finally:
        db.close()


def test_chat_request_accepts_five_thousand_characters():
    request = ChatRequest(message="学" * 5000, course="Python")
    assert len(request.message) == 5000
