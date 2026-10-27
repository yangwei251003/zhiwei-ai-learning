from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.models.database import StudentProfile, User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse


router = APIRouter(prefix="/auth", tags=["认证"])


def envelope(data, message: str = "ok", code: int = 200) -> dict:
    if hasattr(data, "model_dump"):
        data = data.model_dump(mode="json")
    return {"code": code, "data": data, "message": message}


def get_runtime_settings(request: Request) -> Settings:
    return request.app.state.settings


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Annotated[Session, Depends(get_db)]) -> dict:
    existing = db.scalar(
        select(User).where(
            or_(User.email == payload.email, User.username == payload.username)
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="邮箱或用户名已注册")
    user = User(
        username=payload.username,
        email=str(payload.email),
        hashed_password=hash_password(payload.password),
    )
    user.profile = StudentProfile(
        professional_direction=payload.major,
        cognitive_style=payload.learning_style,
        completeness=2 / 6,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return envelope(UserResponse.model_validate(user), "注册成功", 201)


@router.post("/login")
def login(
    payload: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_runtime_settings)],
) -> dict:
    user = db.scalar(select(User).where(User.email == str(payload.email)))
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="邮箱或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已停用")
    return envelope(
        TokenResponse(access_token=create_access_token(str(user.id), settings))
    )


@router.get("/me")
def me(current_user: Annotated[User, Depends(get_current_user)]) -> dict:
    return envelope(UserResponse.model_validate(current_user))
