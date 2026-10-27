"""Minimal Vercel Python runtime probe, independent from application startup."""

from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def probe():
    return {"status": "ok"}
