from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import User
from app.core.security import get_current_user
from app.core import get_settings

router = APIRouter()


@router.get("/status")
def get_agent_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取当前可用的智能体列表与状态"""
    from app.agents.orchestrator import AgentOrchestrator
    orchestrator = AgentOrchestrator(user_id=user.id, db=db)
    return {
        "agents": [{"name": name, "status": "ready", "engine": "langgraph"} for name in (
            "memory_node", "intent_classifier", "profile_agent", "resource_agent",
            "path_agent", "tutor_agent", "response_agent",
        )],
        "llm_configured": orchestrator.llm.is_connected(),
        "rag_configured": bool(get_settings().vector_db_path),
    }
