from pathlib import Path


def test_render_manifest_does_not_require_a_persistent_disk():
    manifest = Path("render.yaml").read_text(encoding="utf-8")

    assert "disk:" not in manifest
    assert "RAG_BACKEND" in manifest
    assert "SUPABASE_SERVICE_ROLE_KEY" in manifest


def test_vercel_manifest_routes_all_requests_to_the_fastapi_app():
    root = Path(__file__).parents[1]
    manifest = (root / "vercel.json").read_text(encoding="utf-8")
    entrypoint = (root / "api" / "index.py").read_text(encoding="utf-8")

    assert '"/api/index.py"' in manifest
    assert "from app.main import app" in entrypoint
