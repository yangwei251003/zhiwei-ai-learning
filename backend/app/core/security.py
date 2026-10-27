from datetime import datetime, timedelta

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core import get_settings
from app.core.database import get_db
from app.models import User

oauth2_scheme = HTTPBearer(auto_error=False)


def create_access_token(data: dict) -> str:
    settings = get_settings()
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def get_current_user(
    token: HTTPAuthorizationCredentials | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    if token is None:
        raise HTTPException(status_code=401, detail="未登录")

    settings = get_settings()
    try:
        payload = jwt.decode(
            token.credentials,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError):
        raise HTTPException(status_code=401, detail="无效的 Token")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user
