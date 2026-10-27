from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ResourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    resource_type: str
    title: str
    content: str
    difficulty: str | None
    created_at: datetime
