from app.core.database import Base
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator
from sqlalchemy.dialects.postgresql import TSVECTOR
from pgvector.sqlalchemy import Vector
from datetime import datetime, timezone
import json


def _normalize_weak_points(value):
    if value is None or value == "":
        return []
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except (TypeError, ValueError):
            decoded = value
        value = decoded
    if not isinstance(value, list):
        value = [value]

    normalized = []
    for item in value:
        if item is None or item == "":
            continue
        point = dict(item) if isinstance(item, dict) else {"name": str(item)}
        if not point.get("name"):
            continue
        try:
            confidence = float(point.get("confidence", 0.5))
        except (TypeError, ValueError):
            confidence = 0.5
        point["confidence"] = min(1.0, max(0.0, confidence))
        normalized.append(point)
    return normalized


class WeakPointsJSON(TypeDecorator):
    impl = JSON
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return _normalize_weak_points(value)

    def process_result_value(self, value, dialect):
        return _normalize_weak_points(value)


def utc_now():
    return datetime.now(timezone.utc)


class StudentProfile(Base):
    """学生画像"""
    __tablename__ = "student_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    # 6+ 维度画像
    knowledge_base = Column(Text, default="")  # 知识基础
    cognitive_style = Column(String(50), default="visual")  # 认知风格
    # MutableList tracks list edits; replace nested dicts instead of mutating them in place.
    weak_points = Column(
        MutableList.as_mutable(WeakPointsJSON()), nullable=False, default=list
    )  # 易错点偏好
    learning_goal = Column(Text, default="")  # 学习目标
    major = Column(String(100), default="")  # 专业
    interests = Column(Text, default="")  # 兴趣方向
    extra_dimensions = Column(JSON, default=dict)  # 额外维度
    current_version = Column(Integer, nullable=False, default=1)
    learning_pace = Column(String(30), default="medium")
    short_term_goal = Column(Text, default="")
    medium_term_goal = Column(Text, default="")
    knowledge_state = Column(JSON, default=dict)
    energy_scores = Column(JSON, default=dict)
    constellation_points = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="profile")
    versions = relationship(
        "StudentProfileVersion", back_populates="profile", cascade="all, delete-orphan"
    )


class User(Base):
    """用户"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    hashed_password = Column(String(255))
    role = Column(String(20), default="student")  # student / admin
    created_at = Column(DateTime, default=datetime.utcnow)

    profile = relationship("StudentProfile", back_populates="user", uselist=False)
    resources = relationship("LearningResource", back_populates="user")
    learning_paths = relationship("LearningPath", back_populates="user")
    knowledge_documents = relationship("KnowledgeDocument", back_populates="user")
    graph_nodes = relationship("KnowledgeGraphNode", back_populates="user")
    graph_edges = relationship("KnowledgeGraphEdge", back_populates="user")
    achievements = relationship("UserAchievement", back_populates="user")
    daily_challenges = relationship("DailyChallenge", back_populates="user")
    point_transactions = relationship("PointTransaction", back_populates="user")


class LearningResource(Base):
    """生成的学习资源"""
    __tablename__ = "learning_resources"
    __table_args__ = (
        UniqueConstraint("id", "user_id", name="uq_learning_resource_tenant"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    resource_type = Column(String(50))  # document / mindmap / quiz / video_script / code_case
    title = Column(String(200))
    content = Column(Text)  # 原始内容（Markdown / JSON）
    rendered_html = Column(Text, default="")  # 渲染后的 HTML
    metadata_json = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="resources")
    outgoing_links = relationship(
        "ResourceLink",
        foreign_keys="[ResourceLink.source_resource_id, ResourceLink.user_id]",
        back_populates="source_resource",
        passive_deletes="all",
        overlaps="incoming_links,target_resource",
    )
    incoming_links = relationship(
        "ResourceLink",
        foreign_keys="[ResourceLink.target_resource_id, ResourceLink.user_id]",
        back_populates="target_resource",
        passive_deletes="all",
        overlaps="outgoing_links,source_resource",
    )


class LearningPath(Base):
    """个性化学习路径"""
    __tablename__ = "learning_paths"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    path_data = Column(JSON)  # [{step: 1, topic: "...", resource_ids: [...], status: "pending|completed"}]
    current_step = Column(Integer, default=0)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="learning_paths")


class Conversation(Base):
    """对话历史"""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    role = Column(String(20))  # user / assistant / system
    content = Column(Text)
    metadata_json = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


class StudentProfileVersion(Base):
    __tablename__ = "student_profile_versions"
    __table_args__ = (
        UniqueConstraint("profile_id", "version", name="uq_profile_version"),
    )

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(
        Integer, ForeignKey("student_profiles.id"), nullable=False, index=True
    )
    version = Column(Integer, nullable=False)
    snapshot = Column(JSON, nullable=False)
    source_conversation_id = Column(Integer, ForeignKey("conversations.id"))
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    profile = relationship("StudentProfile", back_populates="versions")
    source_conversation = relationship("Conversation")
    change_logs = relationship(
        "ProfileChangeLog", back_populates="profile_version", cascade="all, delete-orphan"
    )


class ProfileChangeLog(Base):
    __tablename__ = "profile_change_logs"
    __table_args__ = (
        Index("ix_profile_change_logs_version", "profile_version_id"),
        Index("ix_profile_change_logs_conversation", "conversation_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    profile_version_id = Column(
        Integer, ForeignKey("student_profile_versions.id"), nullable=False
    )
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    changes = Column(JSON, nullable=False, default=dict)
    reason = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    profile_version = relationship("StudentProfileVersion", back_populates="change_logs")
    conversation = relationship("Conversation")


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    course = Column(String(100), nullable=False, index=True)
    original_filename = Column(String(255), nullable=False)
    storage_name = Column(String(255), nullable=False, unique=True)
    mime = Column(String(100), nullable=False)
    size = Column(Integer, nullable=False)
    status = Column(String(30), nullable=False, default="pending", index=True)
    summary = Column(Text, default="")
    keywords = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    user = relationship("User", back_populates="knowledge_documents")


class KnowledgeChunk(Base):
    """Durable, tenant-scoped retrieval chunks for the Supabase backend."""

    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_knowledge_chunk_document_index"),
        Index("ix_knowledge_chunk_tenant_course", "user_id", "course"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    document_id = Column(Integer, ForeignKey("knowledge_documents.id"), nullable=False)
    course = Column(String(100), nullable=False)
    filename = Column(String(255), nullable=False)
    source_type = Column(String(50), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    page = Column(Integer)
    paragraph = Column(Integer)
    char_start = Column(Integer, nullable=False)
    char_end = Column(Integer, nullable=False)
    embedding = Column(Vector(384).with_variant(Text(), "sqlite"), nullable=True)
    search_vector = Column(TSVECTOR().with_variant(Text(), "sqlite"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
class ResourceLink(Base):
    __tablename__ = "resource_links"
    __table_args__ = (
        UniqueConstraint(
            "source_resource_id",
            "target_resource_id",
            "relation",
            name="uq_resource_link_relation",
        ),
        Index("ix_resource_links_source", "source_resource_id"),
        Index("ix_resource_links_target", "target_resource_id"),
        ForeignKeyConstraint(
            ["source_resource_id", "user_id"],
            ["learning_resources.id", "learning_resources.user_id"],
            name="fk_resource_link_source_tenant",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["target_resource_id", "user_id"],
            ["learning_resources.id", "learning_resources.user_id"],
            name="fk_resource_link_target_tenant",
            ondelete="CASCADE",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    source_resource_id = Column(Integer, nullable=False)
    target_resource_id = Column(Integer, nullable=False)
    relation = Column(String(50), nullable=False)
    metadata_json = Column("metadata", JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    source_resource = relationship(
        "LearningResource",
        foreign_keys=[source_resource_id, user_id],
        back_populates="outgoing_links",
        overlaps="incoming_links,target_resource",
    )
    target_resource = relationship(
        "LearningResource",
        foreign_keys=[target_resource_id, user_id],
        back_populates="incoming_links",
        overlaps="outgoing_links,source_resource",
    )


class KnowledgeGraphNode(Base):
    __tablename__ = "knowledge_graph_nodes"
    __table_args__ = (
        UniqueConstraint("user_id", "course", "key", name="uq_graph_node_key"),
        UniqueConstraint("id", "user_id", "course", name="uq_graph_node_tenant"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    course = Column(String(100), nullable=False, index=True)
    key = Column(String(150), nullable=False)
    label = Column(String(200), nullable=False)
    difficulty = Column(Float, nullable=False, default=0.0)
    mastery = Column(Float, nullable=False, default=0.0)
    status = Column(String(30), nullable=False, default="locked", index=True)
    resource_ids = Column(JSON, nullable=False, default=list)
    metadata_json = Column("metadata", JSON, nullable=False, default=dict)

    user = relationship("User", back_populates="graph_nodes")


class KnowledgeGraphEdge(Base):
    __tablename__ = "knowledge_graph_edges"
    __table_args__ = (
        UniqueConstraint(
            "source_node_id",
            "target_node_id",
            "relation",
            name="uq_graph_edge_relation",
        ),
        ForeignKeyConstraint(
            ["source_node_id", "user_id", "course"],
            [
                "knowledge_graph_nodes.id",
                "knowledge_graph_nodes.user_id",
                "knowledge_graph_nodes.course",
            ],
            name="fk_graph_edge_source_tenant",
        ),
        ForeignKeyConstraint(
            ["target_node_id", "user_id", "course"],
            [
                "knowledge_graph_nodes.id",
                "knowledge_graph_nodes.user_id",
                "knowledge_graph_nodes.course",
            ],
            name="fk_graph_edge_target_tenant",
        ),
        Index("ix_knowledge_graph_edges_source", "source_node_id"),
        Index("ix_knowledge_graph_edges_target", "target_node_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    course = Column(String(100), nullable=False, index=True)
    source_node_id = Column(Integer, nullable=False)
    target_node_id = Column(Integer, nullable=False)
    relation = Column(String(50), nullable=False)
    weight = Column(Float, nullable=False, default=1.0)
    metadata_json = Column("metadata", JSON, nullable=False, default=dict)

    user = relationship("User", back_populates="graph_edges")
    source_node = relationship(
        "KnowledgeGraphNode", foreign_keys=[source_node_id, user_id, course], viewonly=True
    )
    target_node = relationship(
        "KnowledgeGraphNode", foreign_keys=[target_node_id, user_id, course], viewonly=True
    )


class AchievementDefinition(Base):
    __tablename__ = "achievement_definitions"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(80), nullable=False, unique=True)
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=False, default="")
    badge = Column(String(255), nullable=False, default="")
    points = Column(Integer, nullable=False, default=0)
    rule_type = Column(String(50), nullable=False)
    threshold = Column(Float, nullable=False, default=1.0)

    user_achievements = relationship("UserAchievement", back_populates="achievement")


class UserAchievement(Base):
    __tablename__ = "user_achievements"
    __table_args__ = (
        UniqueConstraint("user_id", "achievement_id", name="uq_user_achievement"),
        Index("ix_user_achievements_achievement", "achievement_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    achievement_id = Column(
        Integer, ForeignKey("achievement_definitions.id"), nullable=False
    )
    progress = Column(Float, nullable=False, default=0.0)
    unlocked_at = Column(DateTime(timezone=True))

    user = relationship("User", back_populates="achievements")
    achievement = relationship("AchievementDefinition", back_populates="user_achievements")


class DailyChallenge(Base):
    __tablename__ = "daily_challenges"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "challenge_date", "course", name="uq_daily_challenge"
        ),
        Index("ix_daily_challenges_date", "challenge_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    course = Column(String(100), nullable=False, index=True)
    challenge_date = Column(Date, nullable=False)
    question_type = Column(String(50), nullable=False)
    question = Column(Text, nullable=False)
    options = Column(JSON, nullable=False, default=list)
    answer = Column(Text, nullable=False)
    explanation = Column(Text, nullable=False, default="")
    difficulty = Column(Float, nullable=False, default=0.0)
    concept = Column(String(150), nullable=False)
    reward_points = Column(Integer, nullable=False, default=0)
    status = Column(String(30), nullable=False, default="active", index=True)

    user = relationship("User", back_populates="daily_challenges")
    submissions = relationship(
        "ChallengeSubmission", back_populates="challenge", cascade="all, delete-orphan"
    )


class ChallengeSubmission(Base):
    __tablename__ = "challenge_submissions"
    __table_args__ = (
        UniqueConstraint("challenge_id", name="uq_challenge_submission"),
        Index("ix_challenge_submissions_challenge", "challenge_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    challenge_id = Column(
        Integer, ForeignKey("daily_challenges.id"), nullable=False
    )
    answer = Column(Text, nullable=False)
    is_correct = Column(Boolean, nullable=False, default=False)
    awarded_points = Column(Integer, nullable=False, default=0)
    submitted_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    challenge = relationship("DailyChallenge", back_populates="submissions")


class PointTransaction(Base):
    __tablename__ = "point_transactions"
    __table_args__ = (
        Index("ix_point_transactions_reference", "reference_type", "reference_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    delta = Column(Integer, nullable=False)
    reason = Column(String(255), nullable=False)
    reference_type = Column(String(50))
    reference_id = Column(Integer)
    idempotency_key = Column(String(150), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    user = relationship("User", back_populates="point_transactions")
