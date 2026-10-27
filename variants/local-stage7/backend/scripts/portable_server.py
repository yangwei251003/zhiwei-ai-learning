"""Windows portable entry point for the packaged 小智析析 demo."""

from __future__ import annotations

import sys
from pathlib import Path

import uvicorn
from fastapi.staticfiles import StaticFiles

from app.main import create_app


def bundled_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))


app = create_app()
frontend_dist = bundled_root() / "frontend_dist"
if frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
