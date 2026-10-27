from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.auth import envelope
from app.core.security import get_current_user
from app.models.database import User


router = APIRouter(prefix="/achievements", tags=["成就"])


@router.get("/")
def list_achievements(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    return envelope(request.app.state.achievements.evaluate(current_user.id))
