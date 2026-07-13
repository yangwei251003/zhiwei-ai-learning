from pathlib import Path


def test_free_deployment_guide_names_vercel_serverless_and_supabase():
    guide = Path(__file__).parents[2] / "documents" / "上线部署说明.md"

    content = guide.read_text(encoding="utf-8")

    assert "Vercel Serverless" in content
    assert "Supabase" in content
    assert "SUPABASE_SERVICE_ROLE_KEY" in content
