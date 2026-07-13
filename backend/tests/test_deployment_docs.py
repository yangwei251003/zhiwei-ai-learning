from pathlib import Path


def test_free_deployment_guide_names_hugging_face_and_vercel():
    guide = Path(__file__).parents[2] / "documents" / "上线部署说明.md"

    content = guide.read_text(encoding="utf-8")

    assert "Hugging Face" in content
    assert "Vercel" in content
    assert "SUPABASE_SERVICE_ROLE_KEY" in content
