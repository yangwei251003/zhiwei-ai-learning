from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_learning_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    learning_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    profile: Mapped[StudentProfile | None] = relationship(back_populates="user", cascade="all, delete-orphan", uselist=False)
    conversations: Mapped[list[Conversation]] = relationship(back_populates="user", cascade="all, delete-orphan")


class StudentProfile(TimestampMixin, Base):
    __tablename__ = "student_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    knowledge_base: Mapped[str | None] = mapped_column(Text)
    cognitive_style: Mapped[str | None] = mapped_column(Text)
    weak_points: Mapped[str | None] = mapped_column(Text)
    learning_goal: Mapped[str | None] = mapped_column(Text)
    professional_direction: Mapped[str | None] = mapped_column(Text)
    interest_preferences: Mapped[str | None] = mapped_column(Text)
    completeness: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    user: Mapped[User] = relationship(back_populates="profile")


class Conversation(TimestampMixin, Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200), default="新对话")
    summary: Mapped[str | None] = mapped_column(Text)
    user: Mapped[User] = relationship(back_populates="conversations")
    messages: Mapped[list[Message]] = relationship(back_populates="conversation", cascade="all, delete-orphan")


class Message(TimestampMixin, Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    citations_json: Mapped[str | None] = mapped_column(Text)
    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class Resource(TimestampMixin, Base):
    __tablename__ = "resources"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    conversation_id: Mapped[int | None] = mapped_column(ForeignKey("conversations.id", ondelete="SET NULL"), index=True)
    resource_type: Mapped[str] = mapped_column(String(30), index=True)
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    difficulty: Mapped[str | None] = mapped_column(String(30))
    metadata_json: Mapped[str | None] = mapped_column(Text)


class KnowledgeDocument(TimestampMixin, Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(String(500), unique=True)
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30), default="processing")
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    chunks: Mapped[list[KnowledgeChunk]] = relationship(back_populates="document", cascade="all, delete-orphan")


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("knowledge_documents.id", ondelete="CASCADE"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[str | None] = mapped_column(Text)
    document: Mapped[KnowledgeDocument] = relationship(back_populates="chunks")
    __table_args__ = (UniqueConstraint("document_id", "chunk_index", name="uq_knowledge_chunk_position"),)


class LearningPath(TimestampMixin, Base):
    __tablename__ = "learning_paths"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    goal: Mapped[str] = mapped_column(Text)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(30), default="active")
    steps: Mapped[list[LearningPathStep]] = relationship(back_populates="path", cascade="all, delete-orphan", order_by="LearningPathStep.position")


class LearningPathStep(TimestampMixin, Base):
    __tablename__ = "learning_path_steps"

    id: Mapped[int] = mapped_column(primary_key=True)
    path_id: Mapped[int] = mapped_column(ForeignKey("learning_paths.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    resource_ids_json: Mapped[str | None] = mapped_column(Text)
    path: Mapped[LearningPath] = relationship(back_populates="steps")
    __table_args__ = (UniqueConstraint("path_id", "position", name="uq_learning_path_step_position"),)


class Achievement(Base):
    __tablename__ = "achievements"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    icon: Mapped[str] = mapped_column(String(255))


class UserAchievement(Base):
    __tablename__ = "user_achievements"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    achievement_id: Mapped[int] = mapped_column(ForeignKey("achievements.id", ondelete="CASCADE"), index=True)
    unlocked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    __table_args__ = (UniqueConstraint("user_id", "achievement_id", name="uq_user_achievement"),)


class SystemSetting(TimestampMixin, Base):
    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True)
    value: Mapped[str] = mapped_column(Text)
    value_type: Mapped[str] = mapped_column(String(30), default="string")
    description: Mapped[str | None] = mapped_column(Text)

