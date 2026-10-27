from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.auth import envelope
from app.core.security import get_current_user
from app.models.database import User
from app.schemas.path import GeneratePathRequest, PathProgressRequest
from app.services.agent_storage import StorageNotFoundError


router = APIRouter(prefix="/path", tags=["学习路径"])


@router.post("/generate", status_code=status.HTTP_201_CREATED)
async def generate_path(
    payload: GeneratePathRequest,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    path = await request.app.state.path_service.generate(current_user.id, payload.goal)
    return envelope(path, "学习路径生成成功", 201)


@router.get("/{path_id}")
def get_path(
    path_id: int,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    try:
        path = request.app.state.path_service.get(current_user.id, path_id)
    except StorageNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return envelope(path)


@router.patch("/{path_id}/progress")
def update_path_progress(
    path_id: int,
    payload: PathProgressRequest,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    try:
        path = request.app.state.path_service.update_progress(
            current_user.id, path_id, payload.step_id, payload.progress
        )
    except StorageNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return envelope(path, "学习进度已更新")
