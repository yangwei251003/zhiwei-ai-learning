from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload, sessionmaker

from app.models.database import (
    Conversation,
    LearningPath,
    LearningPathStep,
    Message,
    Resource,
    StudentProfile,
    User,
    utc_now,
)


PROFILE_FIELDS = (
    "knowledge_base",
    "cognitive_style",
    "weak_points",
    "learning_goal",
    "professional_direction",
    "interest_preferences",
)


class StorageNotFoundError(LookupError):
    pass


class ProfileStore:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    @staticmethod
    def _as_dict(profile: StudentProfile) -> dict[str, str]:
        return {
            field: value
            for field in PROFILE_FIELDS
            if (value := getattr(profile, field)) is not None and value.strip()
        }

    def get(self, user_id: int) -> dict[str, str]:
        with self.session_factory() as db:
            profile = db.scalar(
                select(StudentProfile).where(StudentProfile.user_id == user_id)
            )
            return self._as_dict(profile) if profile else {}

    def update(self, user_id: int, updates: dict[str, str]) -> dict[str, str]:
        with self.session_factory() as db:
            profile = db.scalar(
                select(StudentProfile).where(StudentProfile.user_id == user_id)
            )
            if profile is None:
                profile = StudentProfile(user_id=user_id)
                db.add(profile)
            for field, value in updates.items():
                if field in PROFILE_FIELDS:
                    setattr(profile, field, value)
            profile.completeness = sum(
                bool((getattr(profile, field) or "").strip())
                for field in PROFILE_FIELDS
            ) / len(PROFILE_FIELDS)
            db.commit()
            db.refresh(profile)
            return self._as_dict(profile)


class ConversationStore:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def start_turn(
        self, user_id: int, conversation_id: int | None, message: str
    ) -> int:
        with self.session_factory() as db:
            user = db.get(User, user_id)
            if user is None:
                raise StorageNotFoundError("用户不存在")
            today = datetime.now(timezone.utc).date()
            last_date = (
                user.last_learning_date.date() if user.last_learning_date else None
            )
            if last_date != today:
                if last_date and (today - last_date).days == 1:
                    user.learning_streak += 1
                else:
                    user.learning_streak = 1
                user.last_learning_date = datetime.now(timezone.utc)
            if conversation_id is None:
                conversation = Conversation(
                    user_id=user_id, title=message.strip()[:80] or "新对话"
                )
                db.add(conversation)
                db.flush()
            else:
                conversation = db.get(Conversation, conversation_id)
                if conversation is None or conversation.user_id != user_id:
                    raise StorageNotFoundError("对话不存在")
                conversation.updated_at = utc_now()
            db.add(
                Message(conversation_id=conversation.id, role="user", content=message)
            )
            db.commit()
            return conversation.id

    def finish_turn(self, conversation_id: int, response: str) -> None:
        with self.session_factory() as db:
            conversation = db.get(Conversation, conversation_id)
            if conversation is None:
                raise StorageNotFoundError("对话不存在")
            conversation.updated_at = utc_now()
            db.add(
                Message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=response,
                )
            )
            db.commit()

    @staticmethod
    def _message_as_dict(message: Message) -> dict[str, Any]:
        return {
            "id": message.id,
            "role": message.role,
            "content": message.content,
            "created_at": message.created_at,
        }

    def list_for_user(self, user_id: int) -> list[dict[str, Any]]:
        with self.session_factory() as db:
            conversations = db.scalars(
                select(Conversation)
                .options(selectinload(Conversation.messages))
                .where(Conversation.user_id == user_id)
                .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
            ).all()
            return [
                {
                    "id": conversation.id,
                    "title": conversation.title,
                    "message_count": len(conversation.messages),
                    "last_message": (
                        max(conversation.messages, key=lambda item: item.id).content
                        if conversation.messages
                        else ""
                    ),
                    "created_at": conversation.created_at,
                    "updated_at": conversation.updated_at,
                }
                for conversation in conversations
            ]

    def get_for_user(self, user_id: int, conversation_id: int) -> dict[str, Any]:
        with self.session_factory() as db:
            conversation = db.scalar(
                select(Conversation)
                .options(selectinload(Conversation.messages))
                .where(
                    Conversation.id == conversation_id,
                    Conversation.user_id == user_id,
                )
            )
            if conversation is None:
                raise StorageNotFoundError("对话不存在")
            return {
                "id": conversation.id,
                "user_id": conversation.user_id,
                "title": conversation.title,
                "created_at": conversation.created_at,
                "updated_at": conversation.updated_at,
                "messages": [
                    self._message_as_dict(message)
                    for message in sorted(
                        conversation.messages, key=lambda item: item.id
                    )
                ],
            }


class ResourceStore:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def save_many(
        self,
        user_id: int,
        conversation_id: int | None,
        resources: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        with self.session_factory() as db:
            records = [
                Resource(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    resource_type=str(resource["type"]),
                    title=str(resource["title"]),
                    content=str(resource["content"]),
                )
                for resource in resources
            ]
            db.add_all(records)
            db.commit()
            for record in records:
                db.refresh(record)
            return [
                {
                    "id": record.id,
                    "type": record.resource_type,
                    "title": record.title,
                    "content": record.content,
                }
                for record in records
            ]


class PathStore:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    @staticmethod
    def _as_dict(path: LearningPath) -> dict[str, Any]:
        return {
            "id": path.id,
            "title": path.title,
            "goal": path.goal,
            "progress": path.progress,
            "status": path.status,
            "steps": [
                {
                    "id": step.id,
                    "position": step.position,
                    "title": step.title,
                    "description": step.description,
                    "status": step.status,
                    "progress": step.progress,
                }
                for step in path.steps
            ],
        }

    def save(self, user_id: int, plan: dict[str, Any]) -> dict[str, Any]:
        with self.session_factory() as db:
            path = LearningPath(
                user_id=user_id,
                title=str(plan["title"]),
                goal=str(plan["goal"]),
            )
            path.steps = [
                LearningPathStep(
                    position=position,
                    title=str(step["title"]),
                    description=str(step["description"]),
                )
                for position, step in enumerate(plan["steps"], start=1)
            ]
            db.add(path)
            db.commit()
            db.refresh(path)
            return self._as_dict(path)

    def get(self, user_id: int, path_id: int) -> dict[str, Any]:
        with self.session_factory() as db:
            path = db.scalar(
                select(LearningPath)
                .options(selectinload(LearningPath.steps))
                .where(LearningPath.id == path_id, LearningPath.user_id == user_id)
            )
            if path is None:
                raise StorageNotFoundError("学习路径不存在")
            return self._as_dict(path)

    def update_progress(
        self, user_id: int, path_id: int, step_id: int, progress: float
    ) -> dict[str, Any]:
        if not 0 <= progress <= 100:
            raise ValueError("进度必须在 0 到 100 之间")
        with self.session_factory() as db:
            path = db.scalar(
                select(LearningPath)
                .options(selectinload(LearningPath.steps))
                .where(LearningPath.id == path_id, LearningPath.user_id == user_id)
            )
            if path is None:
                raise StorageNotFoundError("学习路径不存在")
            step = next((item for item in path.steps if item.id == step_id), None)
            if step is None:
                raise StorageNotFoundError("学习步骤不存在")
            step.progress = progress
            step.status = (
                "completed"
                if progress == 100
                else "in_progress"
                if progress
                else "pending"
            )
            path.progress = sum(item.progress for item in path.steps) / len(path.steps)
            path.status = "completed" if path.progress == 100 else "active"
            db.commit()
            db.refresh(path)
            return self._as_dict(path)
