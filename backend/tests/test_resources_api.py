from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.resources import router
from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.models import LearningResource, User


def test_resource_crud_enforces_owner_and_patch_whitelist():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine); Session = sessionmaker(bind=engine); db = Session()
    owner = User(id=1, username="owner", hashed_password="x")
    db.add_all([owner, User(id=2, username="other", hashed_password="x"), LearningResource(id=9, user_id=2, resource_type="document", title="private", content="x")]); db.commit()
    app = FastAPI(); app.include_router(router, prefix="/resources")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: owner
    client = TestClient(app)
    assert client.get("/resources/9").status_code == 404
    created = client.post("/resources/", json={"resource_type": "document", "title": "mine", "content": "# mine", "metadata": {"topic": "t"}})
    assert created.status_code == 201
    rid = created.json()["id"]
    assert client.patch(f"/resources/{rid}", json={"title": "new", "metadata": {"topic": "new"}}).json()["title"] == "new"
    assert client.patch(f"/resources/{rid}", json={"content": "forbidden"}).status_code == 422
    assert client.delete(f"/resources/{rid}").status_code == 200
