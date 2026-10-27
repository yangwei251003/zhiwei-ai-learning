from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User
from app.schemas import (
    ProfileChangeOut,
    ProfileOut,
    ProfilePatch,
    ProfileRollbackRequest,
    ProfileUpdateRequest,
    ProfileVersionOut,
)
from app.services import (
    ProfileConflictError,
    ProfileService,
    ProfileSourceNotFound,
    ProfileVersionNotFound,
)

router = APIRouter()


@router.get("/current", response_model=ProfileOut)
def current_profile(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    try:
        return ProfileService(db).current(user.id)
    except ProfileConflictError:
        raise HTTPException(status_code=409, detail="画像创建冲突，请重试")


@router.patch("/current", response_model=ProfileOut)
def update_profile(
    request: ProfileUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    patch = ProfilePatch.model_validate(
        request.model_dump(exclude={"reason", "source_conversation_id"}, exclude_unset=True)
    )
    try:
        return ProfileService(db).update(
            user.id,
            patch,
            source_conversation_id=request.source_conversation_id,
            reason=request.reason,
        )
    except ProfileSourceNotFound:
        raise HTTPException(status_code=404, detail="来源对话不存在")
    except ProfileConflictError:
        raise HTTPException(status_code=409, detail="画像已更新，请刷新后重试")


@router.get("/versions", response_model=list[ProfileVersionOut])
def profile_versions(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    try:
        return ProfileService(db).versions(user.id)
    except ProfileConflictError:
        raise HTTPException(status_code=409, detail="画像创建冲突，请重试")


@router.get("/changes", response_model=list[ProfileChangeOut])
def profile_changes(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    try:
        return ProfileService(db).changes(user.id)
    except ProfileConflictError:
        raise HTTPException(status_code=409, detail="画像创建冲突，请重试")


@router.post("/rollback/{version}", response_model=ProfileOut)
def rollback_profile(
    version: int,
    request: ProfileRollbackRequest | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if version < 1:
        raise HTTPException(status_code=422, detail="版本号必须大于 0")
    try:
        return ProfileService(db).rollback(
            user.id,
            version,
            reason=request.reason if request else f"回滚到版本 {version}",
            source_conversation_id=(
                request.source_conversation_id if request else None
            ),
        )
    except ProfileVersionNotFound:
        raise HTTPException(status_code=404, detail="画像版本不存在")
    except ProfileSourceNotFound:
        raise HTTPException(status_code=404, detail="来源对话不存在")
    except ProfileConflictError:
        raise HTTPException(status_code=409, detail="画像已更新，请刷新后重试")


@router.get("/export")
def export_profile(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    try:
        content = ProfileService(db).export_markdown(user.id)
    except ProfileConflictError:
        raise HTTPException(status_code=409, detail="画像创建冲突，请重试")
    return Response(
        content=content,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="profile.md"'},
    )
