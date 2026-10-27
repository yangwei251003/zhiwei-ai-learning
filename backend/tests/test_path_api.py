import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.path import get_path_service, router
from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.models import LearningPath, LearningResource, StudentProfile, User
from app.services.path_service import PathNotFound, PathService, PathValidationError


class FakeLLM:
    def __init__(self): self.prompts = []
    async def complete(self, prompt, **kwargs):
        self.prompts.append(prompt)
        return json.dumps({"steps": [{"step": i, "topic": f"T{i}", "description": "study", "estimated_minutes": 20, "resource_types_needed": ["document"], "status": "pending"} for i in range(1, 6)]})


class FakeRAG:
    def __init__(self): self.calls = []
    def search(self, query, user_id, course, top_k=5):
        self.calls.append((query, user_id, course, top_k)); return [{"content": "RAG context"}]


class FakeProfile:
    def current(self, user_id): return {"major": "CS", "learning_goal": "master graphs"}


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine); session = sessionmaker(bind=engine)()
    session.add_all([User(id=1, username="u", hashed_password="x"), User(id=2, username="v", hashed_password="x"), LearningResource(user_id=1, resource_type="document", title="Graph notes", content="x"), LearningPath(user_id=1, path_data=[], is_active=1)])
    session.commit(); yield session; session.close()


@pytest.mark.asyncio
async def test_generate_uses_context_and_deactivates_old_path(db):
    llm, rag = FakeLLM(), FakeRAG(); service = PathService(db, llm, rag, FakeProfile())
    result = await service.generate(1, "learn graph", "algorithms")
    assert rag.calls == [("learn graph", 1, "algorithms", 5)]
    assert "master graphs" in llm.prompts[0] and "Graph notes" in llm.prompts[0] and "RAG context" in llm.prompts[0]
    assert len(result.path_data) == 5 and all(s["status"] == "pending" for s in result.path_data)
    assert db.query(LearningPath).filter(LearningPath.user_id == 1, LearningPath.is_active == 1).count() == 1


@pytest.mark.asyncio
async def test_generate_rejects_invalid_llm_without_replacing_current(db):
    class BadLLM:
        async def complete(self, prompt, **kwargs): return "not json"
    with pytest.raises(PathValidationError): await PathService(db, BadLLM(), FakeRAG(), FakeProfile()).generate(1, "x", "c")
    assert db.query(LearningPath).filter(LearningPath.user_id == 1, LearningPath.is_active == 1).count() == 1


@pytest.mark.asyncio
async def test_generate_accepts_json_wrapped_in_markdown_fence(db):
    class FencedLLM:
        async def complete(self, prompt, **kwargs):
            body = {"steps": [{"step": i, "topic": f"T{i}", "description": "study", "estimated_minutes": 20, "resource_types_needed": ["document"], "status": "pending"} for i in range(1, 6)]}
            return f"```json\n{json.dumps(body)}\n```"
    result = await PathService(db, FencedLLM(), FakeRAG(), FakeProfile()).generate(1, "learn", "Python")
    assert len(result.path_data) == 5


def test_progress_owner_bounds_and_no_regression(db):
    path = db.query(LearningPath).filter_by(user_id=1).first()
    path.path_data = [{"step": i, "topic": "t", "description": "d", "estimated_minutes": 1, "resource_types_needed": [], "status": "pending"} for i in range(1, 6)]; db.commit()
    service = PathService(db, FakeLLM(), FakeRAG(), FakeProfile())
    service.update_progress(1, path.id, 1, "completed")
    assert service.update_progress(1, path.id, 1, "pending").current_step == 1
    with pytest.raises(PathValidationError): service.update_progress(1, path.id, 6, "completed")
    with pytest.raises(PathNotFound): service.update_progress(2, path.id, 1, "completed")


def test_path_api_validation_and_ownership(db):
    owner = db.get(User, 1); service = PathService(db, FakeLLM(), FakeRAG(), FakeProfile())
    app = FastAPI(); app.include_router(router, prefix="/paths")
    app.dependency_overrides[get_db] = lambda: db; app.dependency_overrides[get_current_user] = lambda: owner
    app.dependency_overrides[get_path_service] = lambda: service
    client = TestClient(app)
    assert client.get("/paths/current").status_code == 200
    created = client.post("/paths/generate", json={"message": "graphs", "course": "algo"})
    assert created.status_code == 201
    pid = created.json()["id"]
    assert client.patch(f"/paths/{pid}/progress", json={"step": 1, "status": "completed"}).json()["current_step"] == 1
    assert client.patch(f"/paths/{pid}/progress", json={"step": 0, "status": "completed"}).status_code == 422


def test_path_status_returns_null_instead_of_404_for_empty_state(db):
    student_without_path = db.get(User, 2)
    service = PathService(db, FakeLLM(), FakeRAG(), FakeProfile())
    app = FastAPI(); app.include_router(router, prefix="/paths")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: student_without_path
    app.dependency_overrides[get_path_service] = lambda: service
    response = TestClient(app).get("/paths/status")
    assert response.status_code == 200
    assert response.json() == {"path": None}
