from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class KnowledgeDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    content_type: str
    size_bytes: int
    status: str
    chunk_count: int
    error_message: str | None
    created_at: datetime
