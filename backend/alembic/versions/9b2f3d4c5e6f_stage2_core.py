"""stage2 core data model

Revision ID: 9b2f3d4c5e6f
Revises: e27f9f829dda
Create Date: 2026-07-11
"""

import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9b2f3d4c5e6f"
down_revision: Union[str, None] = "e27f9f829dda"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _encode_legacy_weak_points() -> None:
    connection = op.get_bind()
    rows = list(connection.execute(sa.text("SELECT id, weak_points FROM student_profiles")))
    for row in rows:
        value = row.weak_points
        if value:
            try:
                value = json.loads(value)
            except (TypeError, ValueError):
                pass
        if not isinstance(value, list):
            value = [] if value in (None, "") else [value]
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
        connection.execute(
            sa.text("UPDATE student_profiles SET weak_points=:value WHERE id=:id"),
            {"id": row.id, "value": json.dumps(normalized)},
        )


def upgrade() -> None:
    _encode_legacy_weak_points()
    with op.batch_alter_table("student_profiles") as batch_op:
        batch_op.alter_column(
            "weak_points",
            existing_type=sa.Text(),
            type_=sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
            postgresql_using="weak_points::json",
        )
        batch_op.add_column(
            sa.Column("current_version", sa.Integer(), server_default="1", nullable=False)
        )
        batch_op.add_column(sa.Column("learning_pace", sa.String(30), nullable=True))
        batch_op.add_column(sa.Column("short_term_goal", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("medium_term_goal", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("knowledge_state", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("energy_scores", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("constellation_points", sa.JSON(), nullable=True))

    with op.batch_alter_table("learning_resources") as batch_op:
        batch_op.create_unique_constraint(
            "uq_learning_resource_tenant", ["id", "user_id"]
        )

    op.create_table(
        "student_profile_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("source_conversation_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["student_profiles.id"]),
        sa.ForeignKeyConstraint(["source_conversation_id"], ["conversations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("profile_id", "version", name="uq_profile_version"),
    )
    op.create_index("ix_student_profile_versions_id", "student_profile_versions", ["id"])
    op.create_index("ix_student_profile_versions_profile_id", "student_profile_versions", ["profile_id"])

    op.create_table(
        "profile_change_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("profile_version_id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=True),
        sa.Column("changes", sa.JSON(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.ForeignKeyConstraint(["profile_version_id"], ["student_profile_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_profile_change_logs_id", "profile_change_logs", ["id"])
    op.create_index("ix_profile_change_logs_version", "profile_change_logs", ["profile_version_id"])
    op.create_index("ix_profile_change_logs_conversation", "profile_change_logs", ["conversation_id"])

    op.create_table(
        "knowledge_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("course", sa.String(100), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("storage_name", sa.String(255), nullable=False),
        sa.Column("mime", sa.String(100), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("keywords", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_name", name="uq_knowledge_document_storage_name"),
    )
    op.create_index("ix_knowledge_documents_id", "knowledge_documents", ["id"])
    op.create_index("ix_knowledge_documents_user_id", "knowledge_documents", ["user_id"])
    op.create_index("ix_knowledge_documents_course", "knowledge_documents", ["course"])
    op.create_index("ix_knowledge_documents_status", "knowledge_documents", ["status"])

    op.create_table(
        "resource_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("source_resource_id", sa.Integer(), nullable=False),
        sa.Column("target_resource_id", sa.Integer(), nullable=False),
        sa.Column("relation", sa.String(50), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["source_resource_id", "user_id"],
            ["learning_resources.id", "learning_resources.user_id"],
            name="fk_resource_link_source_tenant",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_resource_id", "user_id"],
            ["learning_resources.id", "learning_resources.user_id"],
            name="fk_resource_link_target_tenant",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_resource_id", "target_resource_id", "relation",
            name="uq_resource_link_relation",
        ),
    )
    op.create_index("ix_resource_links_id", "resource_links", ["id"])
    op.create_index("ix_resource_links_user_id", "resource_links", ["user_id"])
    op.create_index("ix_resource_links_source", "resource_links", ["source_resource_id"])
    op.create_index("ix_resource_links_target", "resource_links", ["target_resource_id"])

    op.create_table(
        "knowledge_graph_nodes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("course", sa.String(100), nullable=False),
        sa.Column("key", sa.String(150), nullable=False),
        sa.Column("label", sa.String(200), nullable=False),
        sa.Column("difficulty", sa.Float(), nullable=False),
        sa.Column("mastery", sa.Float(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("resource_ids", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "course", "key", name="uq_graph_node_key"),
        sa.UniqueConstraint("id", "user_id", "course", name="uq_graph_node_tenant"),
    )
    op.create_index("ix_knowledge_graph_nodes_id", "knowledge_graph_nodes", ["id"])
    op.create_index("ix_knowledge_graph_nodes_user_id", "knowledge_graph_nodes", ["user_id"])
    op.create_index("ix_knowledge_graph_nodes_course", "knowledge_graph_nodes", ["course"])
    op.create_index("ix_knowledge_graph_nodes_status", "knowledge_graph_nodes", ["status"])

    op.create_table(
        "knowledge_graph_edges",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("course", sa.String(100), nullable=False),
        sa.Column("source_node_id", sa.Integer(), nullable=False),
        sa.Column("target_node_id", sa.Integer(), nullable=False),
        sa.Column("relation", sa.String(50), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_node_id", "user_id", "course"],
            ["knowledge_graph_nodes.id", "knowledge_graph_nodes.user_id", "knowledge_graph_nodes.course"],
            name="fk_graph_edge_source_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["target_node_id", "user_id", "course"],
            ["knowledge_graph_nodes.id", "knowledge_graph_nodes.user_id", "knowledge_graph_nodes.course"],
            name="fk_graph_edge_target_tenant",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_node_id", "target_node_id", "relation",
            name="uq_graph_edge_relation",
        ),
    )
    op.create_index("ix_knowledge_graph_edges_id", "knowledge_graph_edges", ["id"])
    op.create_index("ix_knowledge_graph_edges_user_id", "knowledge_graph_edges", ["user_id"])
    op.create_index("ix_knowledge_graph_edges_course", "knowledge_graph_edges", ["course"])
    op.create_index("ix_knowledge_graph_edges_source", "knowledge_graph_edges", ["source_node_id"])
    op.create_index("ix_knowledge_graph_edges_target", "knowledge_graph_edges", ["target_node_id"])

    op.create_table(
        "achievement_definitions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("title", sa.String(150), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("badge", sa.String(255), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("rule_type", sa.String(50), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_achievement_definition_code"),
    )
    op.create_index("ix_achievement_definitions_id", "achievement_definitions", ["id"])

    op.create_table(
        "user_achievements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("achievement_id", sa.Integer(), nullable=False),
        sa.Column("progress", sa.Float(), nullable=False),
        sa.Column("unlocked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["achievement_id"], ["achievement_definitions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "achievement_id", name="uq_user_achievement"),
    )
    op.create_index("ix_user_achievements_id", "user_achievements", ["id"])
    op.create_index("ix_user_achievements_user_id", "user_achievements", ["user_id"])
    op.create_index("ix_user_achievements_achievement", "user_achievements", ["achievement_id"])

    op.create_table(
        "daily_challenges",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("course", sa.String(100), nullable=False),
        sa.Column("challenge_date", sa.Date(), nullable=False),
        sa.Column("question_type", sa.String(50), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("options", sa.JSON(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("difficulty", sa.Float(), nullable=False),
        sa.Column("concept", sa.String(150), nullable=False),
        sa.Column("reward_points", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "challenge_date", "course", name="uq_daily_challenge"
        ),
    )
    op.create_index("ix_daily_challenges_id", "daily_challenges", ["id"])
    op.create_index("ix_daily_challenges_user_id", "daily_challenges", ["user_id"])
    op.create_index("ix_daily_challenges_course", "daily_challenges", ["course"])
    op.create_index("ix_daily_challenges_date", "daily_challenges", ["challenge_date"])
    op.create_index("ix_daily_challenges_status", "daily_challenges", ["status"])

    op.create_table(
        "challenge_submissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("challenge_id", sa.Integer(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("awarded_points", sa.Integer(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["challenge_id"], ["daily_challenges.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("challenge_id", name="uq_challenge_submission"),
    )
    op.create_index("ix_challenge_submissions_id", "challenge_submissions", ["id"])
    op.create_index("ix_challenge_submissions_challenge", "challenge_submissions", ["challenge_id"])

    op.create_table(
        "point_transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(255), nullable=False),
        sa.Column("reference_type", sa.String(50), nullable=True),
        sa.Column("reference_id", sa.Integer(), nullable=True),
        sa.Column("idempotency_key", sa.String(150), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_point_transaction_idempotency"),
    )
    op.create_index("ix_point_transactions_id", "point_transactions", ["id"])
    op.create_index("ix_point_transactions_user_id", "point_transactions", ["user_id"])
    op.create_index(
        "ix_point_transactions_reference",
        "point_transactions",
        ["reference_type", "reference_id"],
    )


def downgrade() -> None:
    op.drop_table("point_transactions")
    op.drop_table("challenge_submissions")
    op.drop_table("daily_challenges")
    op.drop_table("user_achievements")
    op.drop_table("achievement_definitions")
    op.drop_table("knowledge_graph_edges")
    op.drop_table("knowledge_graph_nodes")
    op.drop_table("resource_links")
    op.drop_table("knowledge_documents")
    op.drop_table("profile_change_logs")
    op.drop_table("student_profile_versions")

    with op.batch_alter_table("learning_resources") as batch_op:
        batch_op.drop_constraint("uq_learning_resource_tenant", type_="unique")

    with op.batch_alter_table("student_profiles") as batch_op:
        batch_op.drop_column("constellation_points")
        batch_op.drop_column("energy_scores")
        batch_op.drop_column("knowledge_state")
        batch_op.drop_column("medium_term_goal")
        batch_op.drop_column("short_term_goal")
        batch_op.drop_column("learning_pace")
        batch_op.drop_column("current_version")
        batch_op.alter_column(
            "weak_points",
            existing_type=sa.JSON(),
            type_=sa.Text(),
            nullable=True,
            server_default=None,
            postgresql_using="weak_points::text",
        )
