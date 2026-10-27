from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def client(tmp_path) -> TestClient:
    settings = Settings(
        _env_file=None,
        spark_api_key="test-key",
        secret_key="x" * 32,
        database_url=f"sqlite:///{tmp_path / 'api.db'}",
        auto_create_tables=True,
    )
    return TestClient(create_app(settings))


def test_register_login_and_me_flow(tmp_path) -> None:
    with client(tmp_path) as api:
        registration = {
            "username": "learner",
            "email": "learner@example.com",
            "password": "StrongPass123!",
            "major": "人工智能",
            "learning_style": "视觉型",
        }
        response = api.post("/api/auth/register", json=registration)
        assert response.status_code == 201
        assert response.json()["data"]["email"] == registration["email"]
        assert "password" not in response.text

        duplicate = api.post("/api/auth/register", json=registration)
        assert duplicate.status_code == 409
        assert duplicate.json()["code"] == 409

        login = api.post(
            "/api/auth/login",
            json={"email": registration["email"], "password": registration["password"]},
        )
        assert login.status_code == 200
        token = login.json()["data"]["access_token"]
        me = api.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json()["data"]["username"] == "learner"


def test_login_failure_and_missing_token_are_explicit(tmp_path) -> None:
    with client(tmp_path) as api:
        response = api.post(
            "/api/auth/login",
            json={"email": "none@example.com", "password": "WrongPass123!"},
        )
        assert response.status_code == 401
        assert response.json()["code"] == 401
        assert api.get("/api/auth/me").status_code == 401


def test_registration_rejects_password_over_bcrypt_byte_limit(tmp_path) -> None:
    with client(tmp_path) as api:
        response = api.post(
            "/api/auth/register",
            json={
                "username": "learner",
                "email": "learner@example.com",
                "password": "密" * 30,
                "major": "人工智能",
                "learning_style": "视觉型",
            },
        )
        assert response.status_code == 422
        assert response.json()["code"] == 422
        assert response.json()["message"] == "请求参数验证失败"
