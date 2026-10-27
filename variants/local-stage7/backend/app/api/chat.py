from __future__ import annotations

import asyncio
import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.api.auth import envelope
from app.core.llm import SparkAPIError
from app.core.security import get_current_user
from app.models.database import User
from app.schemas.chat import (
    ChatRequest,
    ConversationDetailResponse,
    ConversationSummaryResponse,
)
from app.services.agent_storage import StorageNotFoundError


router = APIRouter(prefix="/chat", tags=["对话"])
CUSTOM_EVENT_TYPES = {
    "thinking",
    "token",
    "resource",
    "profile_update",
}


def encode_sse(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}\n\n"


@router.get("/conversations")
def list_conversations(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    history = request.app.state.conversations.list_for_user(current_user.id)
    return envelope(
        [
            ConversationSummaryResponse.model_validate(item).model_dump(mode="json")
            for item in history
        ]
    )


@router.get("/conversations/{conversation_id}")
def get_conversation(
    conversation_id: int,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    try:
        detail = request.app.state.conversations.get_for_user(
            current_user.id, conversation_id
        )
    except StorageNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return envelope(
        ConversationDetailResponse.model_validate(detail).model_dump(mode="json")
    )


@router.post("/stream")
async def stream_chat(
    payload: ChatRequest,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
) -> StreamingResponse:
    try:
        conversation_id = await asyncio.to_thread(
            request.app.state.conversations.start_turn,
            current_user.id,
            payload.conversation_id,
            payload.message,
        )
    except StorageNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    graph = request.app.state.agent_graph_builder()
    graph_input = {
        "user_id": current_user.id,
        "conversation_id": conversation_id,
        "message": payload.message,
    }

    async def event_stream():
        sequence = 0
        final_response = ""
        iterator = graph.astream(
            graph_input, stream_mode=["updates", "custom"], version="v2"
        ).__aiter__()
        pending: asyncio.Task | None = None

        def numbered(event: dict[str, Any]) -> dict[str, Any]:
            nonlocal sequence
            sequence += 1
            return {**event, "sequence": sequence}

        try:
            while True:
                if pending is None:
                    pending = asyncio.create_task(anext(iterator))
                done, _ = await asyncio.wait({pending}, timeout=15)
                if not done:
                    if await request.is_disconnected():
                        return
                    yield ": ping\n\n"
                    continue
                try:
                    event = pending.result()
                except StopAsyncIteration:
                    break
                finally:
                    pending = None

                if await request.is_disconnected():
                    return
                if event.get("type") == "custom":
                    custom = event.get("data")
                    if (
                        not isinstance(custom, dict)
                        or custom.get("type") not in CUSTOM_EVENT_TYPES
                    ):
                        raise SparkAPIError("LangGraph emitted an invalid custom event")
                    yield encode_sse(numbered(custom))
                elif event.get("type") == "updates":
                    update = event.get("data", {})
                    # final_response can come from response_agent (general case)
                    # OR from tutor_agent/path_agent (when they return a complete draft)
                    for source in ("response_agent", "tutor_agent", "path_agent"):
                        src = update.get(source, {})
                        if isinstance(src, dict) and isinstance(src.get("final_response"), str):
                            final_response = src["final_response"]
                            break

            if not final_response:
                raise SparkAPIError("LangGraph produced no final response")
            await asyncio.to_thread(
                request.app.state.conversations.finish_turn,
                conversation_id,
                final_response,
            )
        except SparkAPIError as exc:
            yield encode_sse(numbered({"type": "error", "message": str(exc)}))
        except asyncio.CancelledError:
            raise
        except Exception:
            yield encode_sse(
                numbered({"type": "error", "message": "服务暂时不可用，请稍后重试"})
            )
        finally:
            if pending is not None and not pending.done():
                pending.cancel()
                await asyncio.gather(pending, return_exceptions=True)
            close = getattr(iterator, "aclose", None)
            if close is not None:
                await close()
        yield encode_sse(numbered({"type": "done", "conversation_id": conversation_id}))

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
