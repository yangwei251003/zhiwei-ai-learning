from app.main import app
from fastapi.testclient import TestClient


def test_openapi_contains_integrated_protected_routes():
    schema = app.openapi()
    paths = schema["paths"]
    for path in (
            "/api/profile/current", "/api/path/current", "/api/graph/{course}", "/api/achievements",
        "/api/challenges/today", "/api/chat/stream", "/api/agents/status",
    ):
        assert path in paths
    assert "patch" in paths["/api/auth/me"]
    assert paths["/api/agents/status"]["get"]["security"]


def test_agent_status_requires_bearer():
    with TestClient(app) as client:
        assert client.get("/api/agents/status").status_code == 401
