from __future__ import annotations

from typing import Any, Literal, TypedDict

from app.services.knowledge import RetrievalResult


Intent = Literal["resource", "path", "tutor", "general"]


class AgentState(TypedDict, total=False):
    user_id: int
    conversation_id: int | None
    message: str
    retrieval: RetrievalResult
    retrieval_performed: bool
    profile: dict[str, str]
    profile_updates: dict[str, str]
    intent: Intent
    resources: list[dict[str, Any]]
    path: dict[str, Any]
    draft_response: str
    final_response: str
