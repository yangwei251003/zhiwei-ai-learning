from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10_000)
    conversation_id: int | None = Field(default=None, gt=0)


class ConversationSummaryResponse(BaseModel):
    id: int
    title: str
    message_count: int
    last_message: str
    created_at: datetime
    updated_at: datetime


class ConversationMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime


class ConversationDetailResponse(BaseModel):
    id: int
    user_id: int
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[ConversationMessageResponse]
