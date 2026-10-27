from __future__ import annotations

from copy import deepcopy
import html
import json
from math import cos, pi, sin
import re

from sqlalchemy import select, update as sql_update
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.models import (
    Conversation,
    ProfileChangeLog,
    StudentProfile,
    StudentProfileVersion,
    User,
)
from app.schemas import ProfilePatch


PROFILE_FIELDS = (
    "knowledge_base",
    "cognitive_style",
    "weak_points",
    "learning_goal",
    "major",
    "interests",
    "extra_dimensions",
    "learning_pace",
    "short_term_goal",
    "medium_term_goal",
    "knowledge_state",
    "energy_scores",
    "constellation_points",
)

ENERGY_DIMENSIONS = (
    ("knowledge", "knowledge_base"),
    ("cognition", "cognitive_style"),
    ("goals", "learning_goal"),
    ("major", "major"),
    ("interests", "interests"),
    ("pace", "learning_pace"),
    ("resilience", "weak_points"),
)

_MARKDOWN_CONTROL = re.compile(r"([`*_{}\[\]()#+!|>])")


class ProfileVersionNotFound(LookupError):
    pass


class ProfileConflictError(RuntimeError):
    pass


class ProfileSourceNotFound(LookupError):
    pass


class ProfileService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _snapshot(profile: StudentProfile) -> dict:
        return {field: deepcopy(getattr(profile, field)) for field in PROFILE_FIELDS}

    @staticmethod
    def _energy(snapshot: dict, field: str) -> int:
        value = snapshot[field]
        if field == "weak_points":
            if not value:
                return 20
            confidence = sum(point["confidence"] for point in value) / len(value)
            return round(40 + confidence * 60)
        if isinstance(value, str):
            if not value:
                return 20
            return 55 if value in {"visual", "medium"} else min(100, 55 + len(value) * 3)
        return 20 if not value else min(100, 55 + len(value) * 5)

    def _calculate_visualization(self, snapshot: dict) -> dict:
        energy_scores = {
            name: self._energy(snapshot, field) for name, field in ENERGY_DIMENSIONS
        }
        count = len(energy_scores)
        constellation_points = {}
        for index, (name, score) in enumerate(energy_scores.items()):
            angle = -pi / 2 + 2 * pi * index / count
            radius = score / 100
            constellation_points[name] = {
                "x": round(50 + 45 * radius * cos(angle), 2),
                "y": round(50 + 45 * radius * sin(angle), 2),
                "energy": score,
            }
        return {
            "energy_scores": energy_scores,
            "constellation_points": constellation_points,
        }

    def _complete_snapshot(self, snapshot: dict) -> dict:
        completed = deepcopy(snapshot)
        completed.update(self._calculate_visualization(completed))
        return completed

    def _ensure_profile(self, user_id: int) -> StudentProfile:
        profile = self.db.scalar(
            select(StudentProfile).where(StudentProfile.user_id == user_id)
        )
        if profile is not None:
            return profile

        profile = StudentProfile(user_id=user_id, current_version=1)
        self.db.add(profile)
        try:
            self.db.flush()
        except IntegrityError as exc:
            self.db.rollback()
            winner = self.db.scalar(
                select(StudentProfile).where(StudentProfile.user_id == user_id)
            )
            if winner is None:
                raise ProfileConflictError("画像创建冲突，请重试") from exc
            return winner

        snapshot = self._complete_snapshot(self._snapshot(profile))
        for field in ("energy_scores", "constellation_points"):
            setattr(profile, field, deepcopy(snapshot[field]))
        self.db.add(
            StudentProfileVersion(profile_id=profile.id, version=1, snapshot=snapshot)
        )
        return profile

    def get_or_create(self, user_id: int) -> StudentProfile:
        try:
            profile = self._ensure_profile(user_id)
            self.db.commit()
            self.db.refresh(profile)
            return profile
        except Exception:
            self.db.rollback()
            raise

    def current(self, user_id: int) -> StudentProfile:
        return self.get_or_create(user_id)

    @staticmethod
    def _normalize(field: str, value):
        if field == "weak_points":
            return [
                {
                    "name": point["name"].strip(),
                    "confidence": float(point.get("confidence", 0.5)),
                }
                for point in value
            ]
        if isinstance(value, str):
            return value.strip()
        return deepcopy(value)

    def _validate_source(self, user_id: int, source_conversation_id: int | None) -> None:
        if source_conversation_id is None:
            return
        source = self.db.scalar(
            select(Conversation.id).where(
                Conversation.id == source_conversation_id,
                Conversation.user_id == user_id,
            )
        )
        if source is None:
            raise ProfileSourceNotFound(source_conversation_id)

    @staticmethod
    def _audit_reason(reason: str) -> str:
        normalized = reason.strip()
        if not normalized:
            raise ValueError("画像变更原因不可为空")
        if len(normalized) > 500:
            raise ValueError("画像变更原因不可超过 500 个字符")
        return normalized

    def _cas_write(
        self,
        profile: StudentProfile,
        candidate: dict,
        changes: dict,
        source_conversation_id: int | None,
        reason: str,
    ) -> StudentProfile:
        expected = profile.current_version
        next_version = expected + 1
        try:
            result = self.db.execute(
                sql_update(StudentProfile)
                .where(
                    StudentProfile.id == profile.id,
                    StudentProfile.user_id == profile.user_id,
                    StudentProfile.current_version == expected,
                )
                .values(**candidate, current_version=next_version)
                .execution_options(synchronize_session=False)
            )
        except OperationalError as exc:
            raise ProfileConflictError("画像正在被其他请求更新，请重试") from exc
        if result.rowcount != 1:
            raise ProfileConflictError("画像已被其他请求更新，请刷新后重试")

        version = StudentProfileVersion(
            profile_id=profile.id,
            version=next_version,
            snapshot=deepcopy(candidate),
            source_conversation_id=source_conversation_id,
        )
        self.db.add(version)
        self.db.flush()
        self.db.add(
            ProfileChangeLog(
                profile_version_id=version.id,
                conversation_id=source_conversation_id,
                changes=changes,
                reason=self._audit_reason(reason),
            )
        )
        self.db.commit()
        self.db.expire(profile)
        self.db.refresh(profile)
        return profile

    def update(
        self,
        user_id: int,
        patch: ProfilePatch,
        source_conversation_id: int | None = None,
        reason: str = "",
    ) -> StudentProfile:
        try:
            profile = self._ensure_profile(user_id)
            self._validate_source(user_id, source_conversation_id)
            before = self._snapshot(profile)
            candidate = deepcopy(before)
            for field, raw_value in patch.model_dump(exclude_unset=True).items():
                candidate[field] = self._normalize(field, raw_value)
            candidate = self._complete_snapshot(candidate)
            changes = {
                field: {"before": before[field], "after": deepcopy(candidate[field])}
                for field in PROFILE_FIELDS
                if before[field] != candidate[field]
            }
            if not changes:
                self.db.commit()
                self.db.refresh(profile)
                return profile
            return self._cas_write(
                profile, candidate, changes, source_conversation_id, reason
            )
        except Exception:
            self.db.rollback()
            raise

    def versions(self, user_id: int) -> list[StudentProfileVersion]:
        profile = self.get_or_create(user_id)
        return list(
            self.db.scalars(
                select(StudentProfileVersion)
                .where(StudentProfileVersion.profile_id == profile.id)
                .order_by(StudentProfileVersion.version.desc())
            )
        )

    def changes(self, user_id: int) -> list[ProfileChangeLog]:
        profile = self.get_or_create(user_id)
        return list(
            self.db.scalars(
                select(ProfileChangeLog)
                .join(StudentProfileVersion)
                .where(StudentProfileVersion.profile_id == profile.id)
                .order_by(ProfileChangeLog.created_at.desc(), ProfileChangeLog.id.desc())
            )
        )

    def rollback(
        self,
        user_id: int,
        target_version: int,
        reason: str = "rollback",
        source_conversation_id: int | None = None,
    ) -> StudentProfile:
        try:
            profile = self._ensure_profile(user_id)
            self._validate_source(user_id, source_conversation_id)
            target = self.db.scalar(
                select(StudentProfileVersion).where(
                    StudentProfileVersion.profile_id == profile.id,
                    StudentProfileVersion.version == target_version,
                )
            )
            if target is None:
                raise ProfileVersionNotFound(target_version)

            before = self._snapshot(profile)
            candidate = deepcopy(before)
            candidate.update(
                {key: deepcopy(value) for key, value in target.snapshot.items() if key in PROFILE_FIELDS}
            )
            candidate = self._complete_snapshot(candidate)
            changes = {
                field: {"before": before[field], "after": deepcopy(candidate[field])}
                for field in PROFILE_FIELDS
                if before[field] != candidate[field]
            }
            return self._cas_write(
                profile, candidate, changes, source_conversation_id, reason
            )
        except Exception:
            self.db.rollback()
            raise

    def visualization(self, user_id: int) -> dict:
        profile = self.current(user_id)
        current = self._snapshot(profile)
        expected = self._complete_snapshot(current)
        if any(current[field] != expected[field] for field in expected):
            profile = self.update(
                user_id, ProfilePatch(), reason="补全画像可视化数据"
            )
        return {
            "energy_scores": deepcopy(profile.energy_scores),
            "constellation_points": deepcopy(profile.constellation_points),
        }

    @staticmethod
    def _inline(value) -> str:
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False, sort_keys=True)
        text = re.sub(r"[\r\n]+", " ", str(value))
        text = html.escape(text, quote=True)
        text = text.replace("\\", "\\\\")
        return _MARKDOWN_CONTROL.sub(r"\\\1", text)

    def export_markdown(self, user_id: int) -> str:
        profile = self.current(user_id)
        user = self.db.get(User, user_id)
        visualization = self.visualization(user_id)
        recent = self.changes(user_id)[:5]
        dimensions = [
            ("知识基础", profile.knowledge_base),
            ("认知风格", profile.cognitive_style),
            ("学习目标", profile.learning_goal),
            ("专业", profile.major),
            ("兴趣方向", profile.interests),
            ("学习节奏", profile.learning_pace),
            ("知识状态", profile.knowledge_state),
        ]
        lines = [
            f"# {self._inline(user.username)} 的学习画像",
            "",
            f"当前版本：{profile.current_version}",
            "",
            "## 七维画像",
        ]
        lines.extend(
            f"- {label}：{self._inline(value) if value else '未填写'}"
            for label, value in dimensions
        )
        lines.extend(["", "## 能量数据"])
        lines.extend(
            f"- {name}：{score}" for name, score in visualization["energy_scores"].items()
        )
        lines.extend(["", "## 易错点"])
        lines.extend(
            f"- {self._inline(point['name'])}（置信度 {point['confidence']:.0%}）"
            for point in profile.weak_points
        )
        if not profile.weak_points:
            lines.append("- 暂无")
        lines.extend(["", "## 最近变化"])
        lines.extend(
            f"- 版本 {change.profile_version.version}：{self._inline(change.reason or '画像更新')}"
            for change in recent
        )
        if not recent:
            lines.append("- 暂无")
        return "\n".join(lines) + "\n"
