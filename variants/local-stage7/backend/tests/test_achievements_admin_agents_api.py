from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.security import create_access_token, hash_password
from app.main import create_app
from app.models.database import Conversation, Message, Resource, User


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
        learner = User(
            username="learner",
            email="learner@example.com",
            hashed_password=hash_password("LearnerPass123!"),
            learning_streak=3,
        )
        admin = User(
            username="admin",
            email="admin@example.com",
            hashed_password=hash_password("AdminPass123!"),
            is_admin=True,
        )
        db.add_all([learner, admin])
        db.flush()
        conversation = Conversation(user_id=learner.id, title="首次对话")
        db.add(conversation)
        db.flush()
        db.add(Message(conversation_id=conversation.id, role="user", content="你好"))
        db.add_all(
            [
                Resource(
                    user_id=learner.id,
                    resource_type="document",
                    title=f"资源{index}",
                    content="内容",
                )
                for index in range(5)
            ]
        )
        db.commit()
        db.refresh(learner)
        db.refresh(admin)
    tokens = {
        "learner": create_access_token(str(learner.id), settings),
        "admin": create_access_token(str(admin.id), settings),
    }
    return TestClient(app), tokens


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_achievement_endpoint_unlocks_verified_learning_milestones(tmp_path) -> None:
    api, tokens = api_context(tmp_path)
    with api:
        response = api.get("/api/achievements/", headers=auth(tokens["learner"]))

        assert response.status_code == 200
        achievements = {item["code"]: item for item in response.json()["data"]}
        assert achievements["first_chat"]["unlocked"] is True
        assert achievements["five_resources"]["unlocked"] is True
        assert achievements["three_day_streak"]["unlocked"] is True
        assert all(item["unlocked_at"] for item in achievements.values())


def test_agent_status_is_authenticated_and_reports_all_roles(tmp_path) -> None:
    api, tokens = api_context(tmp_path)
    with api:
        response = api.get("/api/agents/status", headers=auth(tokens["learner"]))

        assert response.status_code == 200
        names = {item["name"] for item in response.json()["data"]}
        assert names >= {
            "retriever",
            "profile_agent",
            "intent_classifier",
            "resource_agent",
            "path_agent",
            "tutor_agent",
            "response_agent",
        }


def test_admin_can_list_users_and_manage_safe_runtime_settings(tmp_path) -> None:
    api, tokens = api_context(tmp_path)
    with api:
        assert (
            api.get("/api/admin/users", headers=auth(tokens["learner"])).status_code
            == 403
        )

        users = api.get("/api/admin/users", headers=auth(tokens["admin"]))
        assert users.status_code == 200
        assert {user["username"] for user in users.json()["data"]} == {
            "learner",
            "admin",
        }

        updated = api.patch(
            "/api/admin/settings",
            headers=auth(tokens["admin"]),
            json={
                "settings": {
                    "model_level": "high",
                    "temperature": "0.6",
                    "agent.tutor_agent": "false",
                }
            },
        )
        assert updated.status_code == 200
        assert updated.json()["data"]["temperature"] == "0.6"
        fetched = api.get("/api/admin/settings", headers=auth(tokens["admin"]))
        assert fetched.json()["data"]["agent.tutor_agent"] == "false"

        rejected = api.patch(
            "/api/admin/settings",
            headers=auth(tokens["admin"]),
            json={"settings": {"secret_key": "do-not-store"}},
        )
        assert rejected.status_code == 422
