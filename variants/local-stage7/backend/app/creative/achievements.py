from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.models.database import (
    Achievement,
    Message,
    Resource,
    User,
    UserAchievement,
)


DEFINITIONS = (
    ("first_chat", "初次相遇", "完成第一次学习对话", "chat-spark"),
    ("five_resources", "资源收藏家", "累计生成五个学习资源", "resource-star"),
    ("three_day_streak", "三日不辍", "连续学习三天", "streak-fire"),
)


class AchievementService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def evaluate(self, user_id: int) -> list[dict]:
        with self.session_factory() as db:
            achievements = self._ensure_definitions(db)
            user = db.get(User, user_id)
            conditions = {
                "first_chat": db.scalar(
                    select(func.count(Message.id))
                    .join(Message.conversation)
                    .where(
                        Message.role == "user",
                        Message.conversation.has(user_id=user_id),
                    )
                )
                > 0,
                "five_resources": db.scalar(
                    select(func.count(Resource.id)).where(Resource.user_id == user_id)
                )
                >= 5,
                "three_day_streak": bool(user and user.learning_streak >= 3),
            }
            existing = {
                item.achievement_id: item
                for item in db.scalars(
                    select(UserAchievement).where(UserAchievement.user_id == user_id)
                )
            }
            for achievement in achievements:
                if conditions[achievement.code] and achievement.id not in existing:
                    unlocked = UserAchievement(
                        user_id=user_id, achievement_id=achievement.id
                    )
                    db.add(unlocked)
                    db.flush()
                    existing[achievement.id] = unlocked
            db.commit()
            return [
                {
                    "code": achievement.code,
                    "name": achievement.name,
                    "description": achievement.description,
                    "icon": achievement.icon,
                    "unlocked": achievement.id in existing,
                    "unlocked_at": (
                        existing[achievement.id].unlocked_at
                        if achievement.id in existing
                        else None
                    ),
                }
                for achievement in achievements
            ]

    @staticmethod
    def _ensure_definitions(db: Session) -> list[Achievement]:
        existing = {item.code: item for item in db.scalars(select(Achievement))}
        for code, name, description, icon in DEFINITIONS:
            if code not in existing:
                achievement = Achievement(
                    code=code, name=name, description=description, icon=icon
                )
                db.add(achievement)
                existing[code] = achievement
        db.flush()
        return [existing[code] for code, *_ in DEFINITIONS]
