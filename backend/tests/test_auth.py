from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def auth_client(tmp_path, monkeypatch):
    database_path = tmp_path / "auth.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")

    from app.core import get_settings

    get_settings.cache_clear()

    from app.core.database import Base, get_db
    from app.main import app

    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
    )
    testing_session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client, database_path
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()
        get_settings.cache_clear()


def test_register_login_and_me(auth_client):
    client, database_path = auth_client
    username = f"stage1_{uuid4().hex[:8]}"
    password = "password123"

    registered = client.post(
        "/api/auth/register",
        json={"username": username, "password": password},
    )
    assert registered.status_code == 200

    logged_in = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert logged_in.status_code == 200
    token = logged_in.json()["access_token"]

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["username"] == username
    assert database_path.exists()


def test_patch_me_updates_username_and_password(auth_client):
    client, _ = auth_client
    token = client.post("/api/auth/register", json={"username": "original", "password": "password123"}).json()["access_token"]
    response = client.patch(
        "/api/auth/me", json={"username": "  updated  ", "password": "newpassword"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["username"] == "updated"
    assert client.post("/api/auth/login", json={"username": "updated", "password": "newpassword"}).status_code == 200


def test_patch_me_rejects_empty_and_duplicate(auth_client):
    client, _ = auth_client
    client.post("/api/auth/register", json={"username": "taken_name", "password": "password123"})
    token = client.post("/api/auth/register", json={"username": "other_name", "password": "password123"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.patch("/api/auth/me", json={}, headers=headers).status_code == 422
    assert client.patch("/api/auth/me", json={"username": "taken_name"}, headers=headers).status_code == 400


def test_register_duplicate_username_returns_conflict(auth_client):
    client, _ = auth_client
    payload = {"username": "duplicate_name", "password": "password123"}
    assert client.post("/api/auth/register", json=payload).status_code == 200
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 409
    assert response.json()["detail"] == "用户名已存在"


def test_admin_can_list_users_but_student_cannot(auth_client):
    client, _ = auth_client
    student_token = client.post(
        "/api/auth/register", json={"username": "student_user", "password": "password123"}
    ).json()["access_token"]
    admin_token = client.post(
        "/api/auth/register", json={"username": "admin_user", "password": "password123"}
    ).json()["access_token"]

    from app.core.database import get_db
    from app.main import app
    from app.models import User

    db = next(app.dependency_overrides[get_db]())
    try:
        admin = db.query(User).filter(User.username == "admin_user").one()
        admin.role = "admin"
        db.commit()
    finally:
        db.close()

    assert client.get(
        "/api/auth/users", headers={"Authorization": f"Bearer {student_token}"}
    ).status_code == 403
    response = client.get(
        "/api/auth/users", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert {item["username"] for item in response.json()} >= {"student_user", "admin_user"}
