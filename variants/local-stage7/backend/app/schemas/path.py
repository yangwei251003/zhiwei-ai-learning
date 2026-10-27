from __future__ import annotations

from pydantic import BaseModel, Field


class GeneratePathRequest(BaseModel):
    goal: str = Field(min_length=2, max_length=500)


class PathProgressRequest(BaseModel):
    step_id: int = Field(gt=0)
    progress: float = Field(ge=0, le=100)
