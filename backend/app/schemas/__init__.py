from datetime import datetime
from typing import Annotated, Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


NonBlank200 = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]
NonBlank500 = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
]


# ---------- 用户认证 ----------
class UserCreate(BaseModel):
    username: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: str


class UserUpdate(BaseModel):
    username: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=50)] | None = None
    password: Annotated[str, StringConstraints(min_length=8)] | None = None

    @model_validator(mode="after")
    def require_change(self):
        if self.username is None and self.password is None:
            raise ValueError("至少提供一个更新字段")
        return self

# ---------- 对话 ----------
class ChatRequest(BaseModel):
    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]
    course: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)] = "人工智能导论"
    conversation_id: int | None = Field(default=None, gt=0)


class ChatResponse(BaseModel):
    reply: str
    resources: list[dict] = []


# ---------- 画像 ----------
class WeakPoint(BaseModel):
    name: NonBlank200
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = 0
    user_id: int = 0
    knowledge_base: str = ""
    cognitive_style: Literal["visual", "auditory", "hands_on", "theoretical"] = "visual"
    weak_points: list[WeakPoint] = Field(default_factory=list)
    learning_goal: str = ""
    major: str = ""
    interests: str = ""
    extra_dimensions: dict = Field(default_factory=dict)
    current_version: int = 1
    learning_pace: Literal["fast", "medium", "slow"] = "medium"
    short_term_goal: str = ""
    medium_term_goal: str = ""
    knowledge_state: dict = Field(default_factory=dict)
    energy_scores: dict = Field(default_factory=dict)
    constellation_points: dict = Field(default_factory=dict)


class ProfilePatch(BaseModel):
    knowledge_base: Annotated[str, StringConstraints(max_length=10000)] | None = None
    cognitive_style: Literal["visual", "auditory", "hands_on", "theoretical"] | None = None
    weak_points: list[WeakPoint] | None = None
    learning_goal: Annotated[str, StringConstraints(max_length=4000)] | None = None
    major: Annotated[str, StringConstraints(max_length=100)] | None = None
    interests: Annotated[str, StringConstraints(max_length=2000)] | None = None
    extra_dimensions: dict[str, Any] | None = None
    learning_pace: Literal["fast", "medium", "slow"] | None = None
    short_term_goal: Annotated[str, StringConstraints(max_length=2000)] | None = None
    medium_term_goal: Annotated[str, StringConstraints(max_length=4000)] | None = None
    knowledge_state: dict[str, Any] | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_explicit_nulls(cls, data):
        if isinstance(data, dict):
            cleaned = dict(data)
            null_fields = []
            for field in cls.model_fields:
                if field not in cleaned:
                    continue
                value = cleaned[field]
                if value is None:
                    null_fields.append(field)
                elif isinstance(value, str):
                    value = value.strip()
                    if not value:
                        null_fields.append(field)
                    cleaned[field] = value
            if null_fields:
                raise ValueError(
                    f"画像字段不可为空: {', '.join(sorted(null_fields))}"
                )
            return cleaned
        return data


class ProfileUpdateRequest(ProfilePatch):
    reason: NonBlank500
    source_conversation_id: int | None = Field(default=None, gt=0)


class ProfileRollbackRequest(BaseModel):
    reason: NonBlank500 = "rollback"
    source_conversation_id: int | None = Field(default=None, gt=0)

    @model_validator(mode="before")
    @classmethod
    def normalize_strings(cls, data):
        if not isinstance(data, dict):
            return data
        cleaned = dict(data)
        if "reason" in cleaned and isinstance(cleaned["reason"], str):
            cleaned["reason"] = cleaned["reason"].strip()
        if "source_conversation_id" in cleaned and cleaned["source_conversation_id"] is None:
            raise ValueError("来源对话不可为空")
        return cleaned


class ProfileVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    version: int
    snapshot: dict[str, Any]
    source_conversation_id: int | None = None
    created_at: datetime


class ProfileChangeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    changes: dict[str, Any]
    reason: str
    conversation_id: int | None = None
    created_at: datetime


# ---------- 资源 ----------
class ResourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    resource_type: str
    title: str
    content: str
    rendered_html: str = ""

class ResourceList(BaseModel):
    resources: list[ResourceOut]
    total: int


# ---------- 学习路径 ----------
class LearningPathOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    path_data: list
    current_step: int
    is_active: bool


# ---------- 知识库 ----------
class KnowledgeDocumentOut(BaseModel):
    id: int
    course: str
    original_filename: str
    mime: str
    size: int
    status: str
    summary: str = ""
    keywords: list[str] = Field(default_factory=list)
    chunk_count: int = 0
    created_at: datetime
    updated_at: datetime


class KnowledgeSearchRequest(BaseModel):
    query: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
    course: NonBlank200
    top_k: int = Field(default=5, ge=1, le=20)


class HighlightSpan(BaseModel):
    start: int
    end: int


class KnowledgeSearchHit(BaseModel):
    content: str
    document_id: int
    filename: str
    source_type: str
    page: int | None = None
    paragraph: int | None = None
    char_start: int
    char_end: int
    similarity: float = Field(ge=0, le=1)
    citation_id: str
    highlight_spans: list[HighlightSpan]
