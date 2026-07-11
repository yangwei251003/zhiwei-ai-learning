import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.agents.orchestrator import AgentOrchestrator
from app.api.knowledge import get_knowledge_service
from app.core.database import get_db
from app.core.security import get_current_user
from app.models import Conversation, User
from app.schemas import ChatRequest
from app.services.achievement_service import AchievementService

router = APIRouter()
_END = object()
ALLOWED_EVENTS = {"thinking", "token", "resource", "profile_update", "error", "done"}


def get_chat_timeout() -> float:
    return 60.0


def get_orchestrator(user: User, db: Session, course: str) -> AgentOrchestrator:
    return AgentOrchestrator(user_id=user.id, db=db, course=course)


def _sse(item: dict) -> dict:
    event_type = item["type"]
    body = {"type": event_type, "payload": item.get("payload", {})}
    return {"event": event_type, "data": json.dumps(body, ensure_ascii=False)}


def _conversation_key(db: Session, user_id: int, requested: int | None) -> int | None:
    if requested is None:
        return None
    row = db.query(Conversation).filter(Conversation.id == requested).first()
    if row is None:
        raise HTTPException(404, "conversation not found")
    if row.user_id != user_id:
        raise HTTPException(403, "conversation does not belong to current user")
    return requested


@router.post("/stream")
async def chat_stream(
    req: ChatRequest, request: Request, user: User = Depends(get_current_user),
    db: Session = Depends(get_db), rag=Depends(get_knowledge_service),
    timeout_seconds: float = Depends(get_chat_timeout),
):
    conversation_key = _conversation_key(db, user.id, req.conversation_id)
    try:
        rag_chunks = await asyncio.to_thread(
            rag.search, req.message, user.id, req.course, 5
        )
    except Exception as exc:
        raise HTTPException(503, "knowledge search is unavailable") from exc

    queue: asyncio.Queue = asyncio.Queue()
    orchestrator = get_orchestrator(user, db, req.course)

    async def produce():
        reply_parts = []
        key = conversation_key
        try:
            await queue.put({"type": "thinking", "payload": {"status": "processing"}})
            async with asyncio.timeout(timeout_seconds):
                async for raw in orchestrator.process_message(req.message, key, rag_chunks):
                    event_type = raw.get("type")
                    if event_type == "text":
                        event_type = "token"
                    if event_type not in ALLOWED_EVENTS - {"thinking", "error", "done"}:
                        continue
                    item = {"type": event_type, "payload": raw.get("payload", {})}
                    if event_type == "token":
                        reply_parts.append(str(item["payload"].get("content", "")))
                    await queue.put(item)
            user_row = Conversation(user_id=user.id, role="user", content=req.message,
                                    metadata_json={"conversation_id": key, "course": req.course})
            db.add(user_row)
            db.flush()
            if key is None:
                key = user_row.id
                user_row.metadata_json = {"conversation_id": key, "course": req.course}
            db.add(Conversation(user_id=user.id, role="assistant", content="".join(reply_parts),
                                metadata_json={"conversation_id": key, "course": req.course}))
            db.commit()
            AchievementService(db).record_chat_completed(user.id)
            await queue.put({"type": "done", "payload": {"conversation_id": key}})
        except asyncio.CancelledError:
            db.rollback()
            raise
        except Exception as exc:
            db.rollback()
            await queue.put({"type": "error", "payload": {"detail": str(exc)}})
            await queue.put({"type": "done", "payload": {"success": False}})
        finally:
            await queue.put(_END)

    producer = asyncio.create_task(produce())

    async def events():
        try:
            while True:
                if await request.is_disconnected():
                    producer.cancel()
                    break
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=0.1)
                except asyncio.TimeoutError:
                    continue
                if item is _END:
                    break
                yield _sse(item)
        finally:
            if not producer.done():
                producer.cancel()
            await asyncio.gather(producer, return_exceptions=True)

    return EventSourceResponse(events())


@router.post("/send")
async def chat_send(req: ChatRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    orchestrator = get_orchestrator(user, db, req.course)
    try:
        return await orchestrator.process_message_sync(req.message)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
