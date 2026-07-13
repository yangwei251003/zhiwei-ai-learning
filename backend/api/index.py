"""Vercel serverless entrypoint for the FastAPI application."""

import sys
from pathlib import Path

# Vercel invokes this file from the function directory; include backend/ so
# the existing application package remains importable in the serverless image.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from app.main import app
except Exception as startup_error:  # temporary safe diagnostic for serverless startup
    from fastapi import FastAPI

    app = FastAPI()

    @app.get("/{path:path}")
    def startup_diagnostic(path: str):
        return {"status": "startup_error", "type": type(startup_error).__name__}
