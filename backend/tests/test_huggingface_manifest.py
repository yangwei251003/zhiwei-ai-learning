from pathlib import Path


def test_huggingface_space_manifest_exposes_docker_port():
    root = Path(__file__).parents[2] / "hf-space"
    readme = (root / "README.md").read_text(encoding="utf-8")
    dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")

    assert "sdk: docker" in readme
    assert "app_port: 7860" in readme
    assert "EXPOSE 7860" in dockerfile
    assert "--port 7860" in dockerfile
