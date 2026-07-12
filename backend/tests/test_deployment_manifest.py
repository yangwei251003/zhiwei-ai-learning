from pathlib import Path


def test_render_manifest_does_not_require_a_persistent_disk():
    manifest = Path("render.yaml").read_text(encoding="utf-8")

    assert "disk:" not in manifest
    assert "RAG_BACKEND" in manifest
    assert "SUPABASE_SERVICE_ROLE_KEY" in manifest
