from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def profile_client(tmp_path, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "profile-api-secret")
    from app.core import get_settings

    get_settings.cache_clear()
    from app.core.database import Base, get_db
    from app.main import app

    engine = create_engine(
        f"sqlite:///{(tmp_path / 'profile-api.db').as_posix()}",
        connect_args={"check_same_thread": False},
    )
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(engine)

    def override_get_db():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()
        get_settings.cache_clear()


def _register(client):
    username = f"profile-{uuid4().hex[:8]}"
    response = client.post(
        "/api/auth/register", json={"username": username, "password": "secret123"}
    )
    return username, {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_profile_endpoints_require_jwt(profile_client):
    assert profile_client.get("/api/profile/current").status_code == 401


def test_profile_update_versions_changes_rollback_and_export(profile_client):
    username, headers = _register(profile_client)
    current = profile_client.get("/api/profile/current", headers=headers)
    assert current.status_code == 200
    assert current.json()["current_version"] == 1

    updated = profile_client.patch(
        "/api/profile/current",
        headers=headers,
        json={"major": "Computer Science", "reason": "manual"},
    )
    assert updated.status_code == 200
    assert updated.json()["current_version"] == 2

    versions = profile_client.get("/api/profile/versions", headers=headers)
    assert [item["version"] for item in versions.json()] == [2, 1]
    changes = profile_client.get("/api/profile/changes", headers=headers)
    assert changes.json()[0]["reason"] == "manual"

    rolled_back = profile_client.post("/api/profile/rollback/1", headers=headers)
    assert rolled_back.status_code == 200
    assert rolled_back.json()["current_version"] == 3

    exported = profile_client.get("/api/profile/export", headers=headers)
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("text/markdown")
    assert "attachment" in exported.headers["content-disposition"]
    assert username in exported.text


def test_profile_api_validation_and_missing_version(profile_client):
    _, headers = _register(profile_client)
    assert profile_client.get("/api/profile/current", headers=headers).status_code == 200
    invalid = profile_client.patch(
        "/api/profile/current",
        headers=headers,
        json={"learning_pace": "warp", "reason": "bad"},
    )
    assert invalid.status_code == 422
    null_major = profile_client.patch(
        "/api/profile/current",
        headers=headers,
        json={"major": None, "reason": "bad"},
    )
    assert null_major.status_code == 422
    null_weak_points = profile_client.patch(
        "/api/profile/current",
        headers=headers,
        json={"weak_points": None, "reason": "bad"},
    )
    assert null_weak_points.status_code == 422
    blank_major = profile_client.patch(
        "/api/profile/current",
        headers=headers,
        json={"major": "   ", "reason": "bad"},
    )
    assert blank_major.status_code == 422
    blank_reason = profile_client.patch(
        "/api/profile/current",
        headers=headers,
        json={"major": "Math", "reason": "  \n  "},
    )
    assert blank_reason.status_code == 422
    blank_weak_point = profile_client.patch(
        "/api/profile/current",
        headers=headers,
        json={"weak_points": [{"name": "   ", "confidence": 0.5}], "reason": "bad"},
    )
    assert blank_weak_point.status_code == 422
    long_major = profile_client.patch(
        "/api/profile/current",
        headers=headers,
        json={"major": "x" * 101, "reason": "bad"},
    )
    assert long_major.status_code == 422
    missing_source = profile_client.patch(
        "/api/profile/current",
        headers=headers,
        json={"major": "Math", "reason": "bad source", "source_conversation_id": 999},
    )
    assert missing_source.status_code == 404
    missing_rollback_source = profile_client.post(
        "/api/profile/rollback/1",
        headers=headers,
        json={"reason": "bad source", "source_conversation_id": 999},
    )
    assert missing_rollback_source.status_code == 404
    missing = profile_client.post("/api/profile/rollback/99", headers=headers)
    assert missing.status_code == 404


def test_users_only_see_their_own_profile(profile_client):
    _, first_headers = _register(profile_client)
    _, second_headers = _register(profile_client)
    profile_client.patch(
        "/api/profile/current",
        headers=first_headers,
        json={"major": "Private Major", "reason": "private"},
    )

    second_current = profile_client.get(
        "/api/profile/current", headers=second_headers
    ).json()
    second_changes = profile_client.get(
        "/api/profile/changes", headers=second_headers
    ).json()

    assert second_current["major"] == ""
    assert second_current["current_version"] == 1
    assert second_changes == []
