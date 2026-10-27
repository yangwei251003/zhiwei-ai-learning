from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import envelope
from app.core.database import get_db
from app.core.security import require_admin
from app.models.database import SystemSetting, User
from app.schemas.admin import UpdateSettingsRequest


router = APIRouter(prefix="/admin", tags=["管理后台"])


@router.get("/users")
def list_users(
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    users = db.scalars(select(User).order_by(User.id)).all()
    return envelope(
        [
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_admin": user.is_admin,
                "is_active": user.is_active,
                "learning_streak": user.learning_streak,
            }
            for user in users
        ]
    )


def settings_dict(db: Session) -> dict[str, str]:
    return {item.key: item.value for item in db.scalars(select(SystemSetting))}


@router.get("/settings")
def get_system_settings(
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    return envelope(settings_dict(db))


@router.patch("/settings")
def update_system_settings(
    payload: UpdateSettingsRequest,
    request: Request,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    for key, value in payload.settings.items():
        setting = db.scalar(select(SystemSetting).where(SystemSetting.key == key))
        if setting is None:
            setting = SystemSetting(key=key, value=value)
            db.add(setting)
        else:
            setting.value = value
        if key.startswith("agent."):
            request.app.state.agent_status.set_enabled(
                key.removeprefix("agent."), value == "true"
            )
    db.commit()
    return envelope(settings_dict(db), "系统设置已更新")
