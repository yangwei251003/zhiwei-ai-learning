from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import Settings
from app.core.security import create_access_token, hash_password
from app.creative.vector_store import SearchResult
from app.main import create_app
from app.models.database import User


class FakeVectorStore:
    def __init__(self) -> None:
        self.ids: list[int] = []

    def add(self, chunk_ids: list[int], texts: list[str]) -> None:
        self.ids.extend(chunk_ids)

    def delete(self, chunk_ids: list[int]) -> int:
        removed = len(set(self.ids).intersection(chunk_ids))
        self.ids = [chunk_id for chunk_id in self.ids if chunk_id not in chunk_ids]
        return removed

    def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        return []


def api_context(tmp_path):
    settings = Settings(
        _env_file=None,
        spark_api_key="test-key",
        secret_key="x" * 32,
        database_url=f"sqlite:///{tmp_path / 'api.db'}",
        auto_create_tables=True,
        faiss_index_path=tmp_path / "index.faiss",
        knowledge_upload_dir=tmp_path / "uploads",
        max_upload_mb=1,
    )
    app = create_app(settings)
    app.state.vector_store = FakeVectorStore()
    with app.state.session_factory() as db:
        admin = User(
            username="admin",
            email="admin@example.com",
            hashed_password=hash_password("AdminPass123!"),
            is_admin=True,
        )
        learner = User(
            username="learner",
            email="learner@example.com",
            hashed_password=hash_password("LearnerPass123!"),
        )
        db.add_all([admin, learner])
        db.commit()
        db.refresh(admin)
        db.refresh(learner)
    tokens = {
        "admin": create_access_token(str(admin.id), settings),
        "learner": create_access_token(str(learner.id), settings),
    }
    return TestClient(app), tokens


def authorization(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_admin_upload_list_and_delete_knowledge_document(tmp_path) -> None:
    api, tokens = api_context(tmp_path)
    with api:
        upload = api.post(
            "/api/knowledge/upload",
            headers=authorization(tokens["admin"]),
            files={"file": ("lesson.txt", "Python 基础知识".encode(), "text/plain")},
        )
        assert upload.status_code == 201
        document = upload.json()["data"]
        assert document["filename"] == "lesson.txt"
        assert document["status"] == "ready"
        assert document["chunk_count"] == 1

        listing = api.get("/api/knowledge/", headers=authorization(tokens["learner"]))
        assert listing.status_code == 200
        assert [item["id"] for item in listing.json()["data"]] == [document["id"]]

        deleted = api.delete(
            f"/api/knowledge/{document['id']}",
            headers=authorization(tokens["admin"]),
        )
        assert deleted.status_code == 200
        assert (
            api.get("/api/knowledge/", headers=authorization(tokens["learner"])).json()[
                "data"
            ]
            == []
        )


def test_knowledge_mutations_require_admin_and_validate_upload(tmp_path) -> None:
    api, tokens = api_context(tmp_path)
    with api:
        forbidden = api.post(
            "/api/knowledge/upload",
            headers=authorization(tokens["learner"]),
            files={"file": ("lesson.txt", b"content", "text/plain")},
        )
        assert forbidden.status_code == 403

        unsupported = api.post(
            "/api/knowledge/upload",
            headers=authorization(tokens["admin"]),
            files={"file": ("archive.zip", b"content", "application/zip")},
        )
        assert unsupported.status_code == 400
        assert "不支持" in unsupported.json()["message"]

        too_large = api.post(
            "/api/knowledge/upload",
            headers=authorization(tokens["admin"]),
            files={"file": ("huge.txt", b"x" * (1024 * 1024 + 1), "text/plain")},
        )
        assert too_large.status_code == 413


def test_delete_missing_document_returns_404(tmp_path) -> None:
    api, tokens = api_context(tmp_path)
    with api:
        response = api.delete(
            "/api/knowledge/404", headers=authorization(tokens["admin"])
        )
        assert response.status_code == 404
        assert response.json()["message"] == "知识文档不存在"

        with api.app.state.session_factory() as db:
            assert db.scalars(select(User)).all()


def test_upload_rejects_extension_mime_mismatch_before_indexing(tmp_path) -> None:
    api, tokens = api_context(tmp_path)
    with api:
        response = api.post(
            "/api/knowledge/upload",
            headers=authorization(tokens["admin"]),
            files={"file": ("lesson.txt", b"plain text", "application/pdf")},
        )

        assert response.status_code == 400
        assert "类型" in response.json()["message"]
