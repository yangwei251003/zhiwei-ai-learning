from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.database import User


bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    encoded = password.encode("utf-8")
    if len(encoded) > 72:
        raise ValueError("Password must be at most 72 UTF-8 bytes")
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(
    subject: str, settings: Settings, expires_delta: timedelta | None = None
) -> str:
    expires = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    return jwt.encode(
        {"sub": str(subject), "exp": expires},
        settings.secret_key,
        algorithm=settings.algorithm,
    )


def decode_access_token(token: str, settings: Settings) -> int:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证登录凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        subject = payload.get("sub")
        if subject is None:
            raise credentials_error
        return int(subject)
    except (JWTError, ValueError) as exc:
        raise credentials_error from exc


def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=401, detail="请先登录", headers={"WWW-Authenticate": "Bearer"}
        )
    settings: Settings = request.app.state.settings
    user_id = decode_access_token(credentials.credentials, settings)
    session: Session = request.app.state.session_factory()
    try:
        user = session.get(User, user_id)
        if user is None or not user.is_active:
            raise HTTPException(status_code=401, detail="用户不存在或已停用")
        session.expunge(user)
        return user
    finally:
        session.close()


def require_admin(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user
