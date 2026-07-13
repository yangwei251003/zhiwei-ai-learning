"""Vercel serverless entrypoint for the FastAPI application."""

import sys
from pathlib import Path

# Vercel invokes this file from the function directory; include backend/ so
# the existing application package remains importable in the serverless image.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app
