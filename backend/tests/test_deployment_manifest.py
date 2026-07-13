from pathlib import Path


def test_render_manifest_does_not_require_a_persistent_disk():
    manifest = Path("render.yaml").read_text(encoding="utf-8")

    assert "disk:" not in manifest
    assert "RAG_BACKEND" in manifest
    assert "SUPABASE_SERVICE_ROLE_KEY" in manifest


def test_vercel_uses_native_python_file_routing_without_legacy_rewrites():
    root = Path(__file__).parents[1]

    assert not (root / "vercel.json").exists()


def test_vercel_keeps_a_direct_runtime_probe_module():
    root = Path(__file__).parents[1]
    probe = (root / "api" / "probe.py").read_text(encoding="utf-8")

    assert '"status": "ok"' in probe


def test_vercel_keeps_a_zero_dependency_handler_probe():
    root = Path(__file__).parents[1]
    probe = (root / "api" / "plain.py").read_text(encoding="utf-8")

    assert "class handler(BaseHTTPRequestHandler)" in probe
