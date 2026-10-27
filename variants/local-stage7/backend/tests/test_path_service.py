from __future__ import annotations

import asyncio

import pytest

from app.core.database import Base, build_engine, build_session_factory
from app.models.database import StudentProfile, User
from app.services.agent_storage import PathStore, StorageNotFoundError
from app.services.knowledge import RetrievalResult
from app.services.paths import PathService


class Knowledge:
    def __init__(self, events: list[str]) -> None:
        self.events = events

    def retrieve(self, query: str) -> RetrievalResult:
        self.events.append("retrieve")
        return RetrievalResult(is_hit=False, hits=[])


class Profiles:
    def get(self, user_id: int) -> dict[str, str]:
        return {"learning_goal": "通过考试"}


class LLM:
    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.prompt = ""

    def chat(self, prompt: str) -> str:
        self.events.append("llm")
        self.prompt = prompt
        return (
            '{"title":"Python进阶路线","goal":"掌握递归",'
            '"steps":[{"title":"基础复习","description":"函数与调用栈"},'
            '{"title":"递归实践","description":"完成三道练习"}]}'
        )


def context(tmp_path):
    engine = build_engine(f"sqlite:///{tmp_path / 'paths.db'}")
    Base.metadata.create_all(engine)
    factory = build_session_factory(engine)
    with factory() as db:
        user = User(
            username="learner", email="learner@example.com", hashed_password="hash"
        )
        user.profile = StudentProfile(learning_goal="通过考试")
        other = User(
            username="other", email="other@example.com", hashed_password="hash"
        )
        db.add_all([user, other])
        db.commit()
        db.refresh(user)
        db.refresh(other)
    return engine, factory, user.id, other.id


def test_path_service_retrieves_before_high_quality_generation_and_persists(
    tmp_path,
) -> None:
    engine, factory, user_id, _ = context(tmp_path)
    events: list[str] = []
    llm = LLM(events)
    service = PathService(
        Knowledge(events), Profiles(), lambda level: llm, PathStore(factory)
    )

    result = asyncio.run(service.generate(user_id, "帮我规划递归学习"))

    assert events == ["retrieve", "llm"]
    assert "我不确定" in llm.prompt
    assert result["title"] == "Python进阶路线"
    assert [step["position"] for step in result["steps"]] == [1, 2]
    assert service.get(user_id, result["id"])["goal"] == "掌握递归"
    engine.dispose()


def test_path_progress_recalculates_overall_and_checks_ownership(tmp_path) -> None:
    engine, factory, user_id, other_id = context(tmp_path)
    store = PathStore(factory)
    path = store.save(
        user_id,
        {
            "title": "路线",
            "goal": "目标",
            "steps": [
                {"title": "步骤1", "description": "内容1"},
                {"title": "步骤2", "description": "内容2"},
            ],
        },
    )

    updated = store.update_progress(user_id, path["id"], path["steps"][0]["id"], 100)

    assert updated["progress"] == pytest.approx(50)
    assert updated["steps"][0]["status"] == "completed"
    with pytest.raises(StorageNotFoundError):
        store.get(other_id, path["id"])
    engine.dispose()
