from pathlib import Path

from PIL import Image


ROOT = Path(__file__).parents[3]


def test_architecture_mermaid_names_every_graph_node():
    text = (ROOT / "documents" / "agent-architecture.mmd").read_text(encoding="utf-8")
    for node in ("memory_node", "intent_classifier", "profile_agent", "resource_agent",
                 "path_agent", "tutor_agent", "response_agent", "END"):
        assert node in text


def test_architecture_png_is_valid_and_readable_size():
    with Image.open(ROOT / "documents" / "agent-architecture.png") as image:
        image.verify()
    with Image.open(ROOT / "documents" / "agent-architecture.png") as image:
        assert image.width >= 1200
        assert image.height >= 700
