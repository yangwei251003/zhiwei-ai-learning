from __future__ import annotations

from dataclasses import dataclass
import re

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.security import hash_password
from app.models.database import User


USERNAME_PATTERN = re.compile(r"^[\w\-\u4e00-\u9fff]{2,50}$")
EMAIL_ADAPTER = TypeAdapter(EmailStr)


class AdminBootstrapError(ValueError):
    """Raised when the first administrator cannot be created safely."""


@dataclass(frozen=True)
class AdminBootstrapResult:
    id: int
    username: str
    email: str


def _validate_credentials(username: str, email: str, password: str) -> tuple[str, str]:
    username = username.strip()
    if not USERNAME_PATTERN.fullmatch(username):
        raise AdminBootstrapError(
            "用户名需为 2 到 50 个中英文字符、数字、下划线或连字符"
        )
    try:
        normalized_email = str(EMAIL_ADAPTER.validate_python(email.strip()))
    except ValidationError as exc:
        raise AdminBootstrapError("邮箱格式无效") from exc
    encoded = password.encode("utf-8")
    if len(password) < 12 or len(encoded) > 72:
        raise AdminBootstrapError("管理员密码需至少 12 个字符且不超过 72 个 UTF-8 字节")
    if not (
        re.search(r"[a-z]", password)
        and re.search(r"[A-Z]", password)
        and re.search(r"\d", password)
        and re.search(r"[^\w\s]", password)
    ):
        raise AdminBootstrapError("管理员密码必须包含大小写字母、数字和特殊字符")
    return username, normalized_email


def bootstrap_admin(
    session_factory: sessionmaker[Session],
    *,
    username: str,
    email: str,
    password: str,
) -> AdminBootstrapResult:
    username, email = _validate_credentials(username, email, password)
    with session_factory() as db:
        if db.scalar(select(User.id).where(User.is_admin.is_(True))) is not None:
            raise AdminBootstrapError("管理员已存在，拒绝重复初始化")
        if (
            db.scalar(
                select(User.id).where(
                    or_(User.username == username, User.email == email)
                )
            )
            is not None
        ):
            raise AdminBootstrapError("用户名或邮箱已被现有账户使用")
        user = User(
            username=username,
            email=email,
            hashed_password=hash_password(password),
            is_admin=True,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return AdminBootstrapResult(
            id=user.id, username=user.username, email=user.email
        )
