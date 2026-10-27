from operator import add
from typing import Annotated, Any, Literal, TypedDict


Intent = Literal["profile", "resource", "path", "tutor", "chat"]


class AgentEvent(TypedDict):
    type: str
    payload: dict[str, Any]


class AgentState(TypedDict, total=False):
    user_id: int
    conversation_id: str | int | None
    message: str
    course: str
    intent: Intent
    profile: dict[str, Any]
    history: list[dict[str, Any]]
    rag_chunks: list[dict[str, Any]]
    resources: list[dict[str, Any]]
    path: dict[str, Any] | None
    response_text: str
    events: Annotated[list[AgentEvent], add]
    errors: Annotated[list[str], add]
