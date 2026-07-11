import asyncio
import json
import threading

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models import LearningResource, ResourceLink, User
from app.services.resource_service import ResourceGenerationError, ResourceGenerationService


def payload(kind):
    common = {"summary_card": {"title": kind, "highlights": ["a", "b", "c"], "duration": "10 min", "difficulty": 2}, "tips": ["1", "2", "3"], "citations": ["notes p1"]}
    bodies = {
        "document": {"markdown": "# T\n## Basics\n```python\nprint(1)\n```\n## Summary\nDone"},
        "mindmap": {"mindmap": "mindmap\n  root((T))\n    A"},
        "quiz": {"questions": [{"question": f"q{i}", "options": ["a", "b"], "answer": "a", "explanation": "x", "difficulty": 2} for i in range(5)]},
        "video_script": {"scenes": [{"shot": 1, "visual": "board", "narration": "hello", "duration_seconds": 10, "bgm": "soft"}]},
        "code_case": {"language": "python", "code": "# input/output\nprint(input())", "input": "x", "output": "x", "complexity": "O(n)"},
    }
    return {**common, **bodies[kind]}


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(User(id=1, username="u", hashed_password="x"))
    session.commit()
    yield session
    session.close()


@pytest.mark.asyncio
async def test_generate_all_starts_five_jobs_together_searches_each_and_persists_links(db):
    barrier = asyncio.Event()
    started = []

    class Rag:
        def search(self, query, user_id, course, top_k=5):
            assert top_k == 5
            return [{"text": "course note", "source": "notes p1"}]

    class Llm:
        async def chat(self, prompt, **kwargs):
            kind = prompt.split("RESOURCE_TYPE:")[1].split()[0]
            started.append(kind)
            if len(started) == 5:
                barrier.set()
            await asyncio.wait_for(barrier.wait(), .5)
            return json.dumps(payload(kind))

    class Achievements:
        def __init__(self): self.calls=[]
        def evaluate(self, *args, **kwargs): self.calls.append(args)
    achievements = Achievements()
    cards = await ResourceGenerationService(Llm(), Rag(), db, achievements).generate_all(
        db.get(User, 1), "loops", "python", {"knowledge_base": "基础弱", "cognitive_style": "hands_on"}
    )
    assert len(cards) == 5 and all(card["type"] == "resource" for card in cards)
    assert db.query(LearningResource).count() == 5
    assert db.query(ResourceLink).count() == 4
    assert all(len(card["payload"]["tips"]) == 3 for card in cards)
    assert achievements.calls == [(1, "resources_generated", {"resource_types": list(ResourceGenerationService.TYPES)})]


@pytest.mark.asyncio
async def test_generate_all_rolls_back_whole_batch_on_one_invalid_result(db):
    class Rag:
        def search(self, *args, **kwargs): return []
    class Llm:
        async def chat(self, prompt, **kwargs):
            kind = prompt.split("RESOURCE_TYPE:")[1].split()[0]
            return "{}" if kind == "quiz" else json.dumps(payload(kind))

    with pytest.raises(ResourceGenerationError):
        await ResourceGenerationService(Llm(), Rag(), db).generate_all(db.get(User, 1), "loops", "python", {})
    assert db.query(LearningResource).count() == 0


@pytest.mark.asyncio
async def test_achievement_failure_rolls_back_the_resource_batch(db):
    class Rag:
        def search(self, *args, **kwargs): return []
    class Llm:
        async def chat(self, prompt, **kwargs):
            return json.dumps(payload(prompt.split("RESOURCE_TYPE:")[1].split()[0]))
    class BrokenAchievements:
        def evaluate(self, *args, **kwargs): raise RuntimeError("achievement unavailable")
    with pytest.raises(ResourceGenerationError):
        await ResourceGenerationService(Llm(), Rag(), db, BrokenAchievements()).generate_all(db.get(User, 1), "loops", "python", {})
    assert db.query(LearningResource).count() == 0
    assert db.query(ResourceLink).count() == 0


@pytest.mark.asyncio
async def test_sync_rag_searches_run_in_parallel_and_finish_before_each_llm(db):
    barrier = threading.Barrier(5, timeout=1)
    lock = threading.Lock()
    searched = set()

    class BlockingRag:
        def search(self, query, user_id, course, top_k=5):
            kind = query.rsplit(" ", 1)[-1]
            barrier.wait()
            with lock:
                searched.add(kind)
            return []

    class Llm:
        async def chat(self, prompt, **kwargs):
            kind = prompt.split("RESOURCE_TYPE:")[1].split()[0]
            with lock:
                assert kind in searched
            return json.dumps(payload(kind))

    cards = await ResourceGenerationService(Llm(), BlockingRag(), db).generate_all(
        db.get(User, 1), "loops", "python", {}
    )
    assert len(cards) == 5
