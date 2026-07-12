"""add Supabase pgvector knowledge chunks

Revision ID: c1d2e3f4a5b6
Revises: 9b2f3d4c5e6f
Create Date: 2026-07-13
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import TSVECTOR


revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, None] = "9b2f3d4c5e6f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
        vector_type = Vector(384)
        search_type = TSVECTOR()
    else:
        vector_type = sa.Text()
        search_type = sa.Text()
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("knowledge_documents.id"), nullable=False),
        sa.Column("course", sa.String(length=100), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("page", sa.Integer()),
        sa.Column("paragraph", sa.Integer()),
        sa.Column("char_start", sa.Integer(), nullable=False),
        sa.Column("char_end", sa.Integer(), nullable=False),
        sa.Column("embedding", vector_type, nullable=True),
        sa.Column("search_vector", search_type, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_knowledge_chunk_document_index"),
    )
    op.create_index("ix_knowledge_chunk_tenant_course", "knowledge_chunks", ["user_id", "course"])
    if bind.dialect.name == "postgresql":
        op.execute("CREATE INDEX ix_knowledge_chunk_embedding ON knowledge_chunks USING ivfflat (embedding vector_cosine_ops)")
        op.execute("CREATE INDEX ix_knowledge_chunk_search ON knowledge_chunks USING gin (search_vector)")


def downgrade() -> None:
    op.drop_table("knowledge_chunks")
