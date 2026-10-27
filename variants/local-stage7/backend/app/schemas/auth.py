from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    username: str = Field(
        min_length=2, max_length=50, pattern=r"^[\w\-\u4e00-\u9fff]+$"
    )
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    major: str = Field(min_length=2, max_length=100)
    learning_style: str = Field(min_length=2, max_length=100)

    @field_validator("password")
    @classmethod
    def validate_bcrypt_length(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("密码最多为 72 个 UTF-8 字节")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    is_admin: bool
    is_active: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
