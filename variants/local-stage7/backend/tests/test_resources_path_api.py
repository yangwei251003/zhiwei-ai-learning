from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.security import create_access_token, hash_password
from app.main import create_app
from app.models.database import Resource, User
from app.services.agent_storage import PathStore


def api_context(tmp_path):
    settings = Settings(
        _env_file=None,
        spark_api_key="test-key",
        secret_key="x" * 32,
        database_url=f"sqlite:///{tmp_path / 'api.db'}",
        auto_create_tables=True,
        faiss_index_path=tmp_path / "index.faiss",
        knowledge_upload_dir=tmp_path / "uploads",
    )
    app = create_app(settings)
    with app.state.session_factory() as db:
        user = User(
            username="learner",
            email="learner@example.com",
            hashed_password=hash_password("LearnerPass123!"),
        )
        other = User(
            username="other",
            email="other@example.com",
            hashed_password=hash_password("OtherPass123!"),
        )
        db.add_all([user, other])
        db.flush()
        db.add_all(
            [
                Resource(
                    user_id=user.id,
                    resource_type="document",
                    title="Python 讲解",
                    content="文档内容",
                ),
                Resource(
                    user_id=user.id,
                    resource_type="code",
                    title="Python 案例",
                    content="print('ok')",
                ),
                Resource(
                    user_id=other.id,
                    resource_type="document",
                    title="他人资源",
                    content="不可见",
                ),
            ]
        )
        db.commit()
        db.refresh(user)
    token = create_access_token(str(user.id), settings)
    app.state.path_store = PathStore(app.state.session_factory)
    return TestClient(app), app, user.id, token


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_resources_support_owner_scoped_filter_search_sort_and_detail(tmp_path) -> None:
    api, _, _, token = api_context(tmp_path)
    with api:
        listing = api.get(
            "/api/resources/?type=document&search=Python&sort=oldest",
            headers=auth(token),
        )
        assert listing.status_code == 200
        assert [item["title"] for item in listing.json()["data"]] == ["Python 讲解"]
        resource_id = listing.json()["data"][0]["id"]
        detail = api.get(f"/api/resources/{resource_id}", headers=auth(token))
        assert detail.json()["data"]["content"] == "文档内容"
        assert api.get("/api/resources/999", headers=auth(token)).status_code == 404


def test_path_generate_get_and_progress_contract(tmp_path) -> None:
    api, app, user_id, token = api_context(tmp_path)

    class FakePathService:
        async def generate(self, target_user_id: int, goal: str):
            assert target_user_id == user_id
            return app.state.path_store.save(
                user_id,
                {
                    "title": "个性化路线",
                    "goal": goal,
                    "steps": [{"title": "第一步", "description": "先学基础"}],
                },
            )

        def get(self, target_user_id: int, path_id: int):
            return app.state.path_store.get(target_user_id, path_id)

        def update_progress(self, target_user_id, path_id, step_id, progress):
            return app.state.path_store.update_progress(
                target_user_id, path_id, step_id, progress
            )

    app.state.path_service = FakePathService()
    with api:
        generated = api.post(
            "/api/path/generate",
            headers=auth(token),
            json={"goal": "掌握 Python"},
        )
        assert generated.status_code == 201
        path = generated.json()["data"]
        fetched = api.get(f"/api/path/{path['id']}", headers=auth(token))
        assert fetched.json()["data"]["steps"][0]["title"] == "第一步"

        updated = api.patch(
            f"/api/path/{path['id']}/progress",
            headers=auth(token),
            json={"step_id": path["steps"][0]["id"], "progress": 100},
        )
        assert updated.status_code == 200
        assert updated.json()["data"]["progress"] == 100
