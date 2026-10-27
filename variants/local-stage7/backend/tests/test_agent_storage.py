from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.database import Base, build_engine, build_session_factory
from app.models.database import Conversation, Message, Resource, StudentProfile, User
from app.services.agent_storage import (
    ConversationStore,
    ProfileStore,
    ResourceStore,
    StorageNotFoundError,
)


def storage_context(tmp_path):
    engine = build_engine(f"sqlite:///{tmp_path / 'agents.db'}")
    Base.metadata.create_all(engine)
    factory = build_session_factory(engine)
    with factory() as db:
        user = User(
            username="learner", email="learner@example.com", hashed_password="hash"
        )
        user.profile = StudentProfile(learning_goal="学会 Python", completeness=1 / 6)
        other = User(
            username="other", email="other@example.com", hashed_password="hash"
        )
        db.add_all([user, other])
        db.commit()
        db.refresh(user)
        db.refresh(other)
    return engine, factory, user.id, other.id


def test_profile_store_gets_and_incrementally_updates_six_dimensions(tmp_path) -> None:
    engine, factory, user_id, _ = storage_context(tmp_path)
    profiles = ProfileStore(factory)

    assert profiles.get(user_id) == {"learning_goal": "学会 Python"}
    updated = profiles.update(
        user_id,
        {"professional_direction": "人工智能", "cognitive_style": "视觉型"},
    )

    assert updated["learning_goal"] == "学会 Python"
    assert updated["professional_direction"] == "人工智能"
    with factory() as db:
        profile = db.scalar(
            select(StudentProfile).where(StudentProfile.user_id == user_id)
        )
        assert profile.completeness == pytest.approx(3 / 6)
    engine.dispose()


def test_conversation_store_validates_owner_and_persists_both_roles(tmp_path) -> None:
    engine, factory, user_id, other_id = storage_context(tmp_path)
    conversations = ConversationStore(factory)

    conversation_id = conversations.start_turn(user_id, None, "什么是递归？")
    conversations.finish_turn(conversation_id, "递归是函数调用自身。")

    with factory() as db:
        conversation = db.get(Conversation, conversation_id)
        messages = list(
            db.scalars(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.id)
            )
        )
        assert conversation.user_id == user_id
        assert [message.role for message in messages] == ["user", "assistant"]
        assert [message.content for message in messages] == [
            "什么是递归？",
            "递归是函数调用自身。",
        ]

    with pytest.raises(StorageNotFoundError):
        conversations.start_turn(other_id, conversation_id, "越权消息")
    engine.dispose()


def test_resource_store_saves_generated_resources_for_user_and_conversation(
    tmp_path,
) -> None:
    engine, factory, user_id, _ = storage_context(tmp_path)
    conversation_id = ConversationStore(factory).start_turn(user_id, None, "生成资源")
    resources = ResourceStore(factory)

    saved = resources.save_many(
        user_id,
        conversation_id,
        [
            {"type": "document", "title": "讲解", "content": "正文"},
            {"type": "code", "title": "案例", "content": "print('ok')"},
        ],
    )

    assert [item["id"] for item in saved] == [1, 2]
    with factory() as db:
        records = list(db.scalars(select(Resource).order_by(Resource.id)))
        assert [record.resource_type for record in records] == ["document", "code"]
        assert all(record.user_id == user_id for record in records)
    engine.dispose()


def test_conversation_store_updates_daily_learning_streak_once_per_day(
    tmp_path,
) -> None:
    engine, factory, user_id, _ = storage_context(tmp_path)
    with factory() as db:
        user = db.get(User, user_id)
        user.learning_streak = 2
        user.last_learning_date = datetime.now(timezone.utc) - timedelta(days=1)
        db.commit()

    conversations = ConversationStore(factory)
    conversation_id = conversations.start_turn(user_id, None, "今天学习")
    conversations.start_turn(user_id, conversation_id, "继续学习")

    with factory() as db:
        user = db.get(User, user_id)
        assert user.learning_streak == 3
        assert user.last_learning_date.date() == datetime.now(timezone.utc).date()
    engine.dispose()


def test_conversation_store_lists_owned_history_and_returns_ordered_detail(
    tmp_path,
) -> None:
    engine, factory, user_id, other_id = storage_context(tmp_path)
    conversations = ConversationStore(factory)
    first_id = conversations.start_turn(user_id, None, "第一轮问题")
    conversations.finish_turn(first_id, "第一轮回答")
    second_id = conversations.start_turn(user_id, None, "第二轮问题")
    conversations.start_turn(other_id, None, "其他用户问题")

    history = conversations.list_for_user(user_id)

    assert [item["id"] for item in history] == [second_id, first_id]
    assert history[0]["title"] == "第二轮问题"
    assert history[0]["message_count"] == 1
    assert history[1]["last_message"] == "第一轮回答"
    detail = conversations.get_for_user(user_id, first_id)
    assert [message["role"] for message in detail["messages"]] == [
        "user",
        "assistant",
    ]
    assert [message["content"] for message in detail["messages"]] == [
        "第一轮问题",
        "第一轮回答",
    ]
    with pytest.raises(StorageNotFoundError, match="对话不存在"):
        conversations.get_for_user(other_id, first_id)
    engine.dispose()
