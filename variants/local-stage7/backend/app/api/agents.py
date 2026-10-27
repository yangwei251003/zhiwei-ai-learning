from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.auth import envelope
from app.core.security import get_current_user
from app.models.database import User


router = APIRouter(prefix="/agents", tags=["智能体"])


@router.get("/status")
def agent_status(
    request: Request,
    _: Annotated[User, Depends(get_current_user)],
) -> dict:
    return envelope(request.app.state.agent_status.snapshot())
