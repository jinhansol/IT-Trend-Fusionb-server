"""content_summaries + content_sources.ai_summary: E1 AI summaries of News and Dev

Adds one opt-in flag per source (off for every existing source) and a table for the
summary of each item. contents rows are not changed.

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "content_sources",
        sa.Column("ai_summary", sa.Boolean(), server_default=sa.text("0"), nullable=False),
    )
    op.create_table(
        "content_summaries",
        sa.Column("content_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("kind", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("partial_input", sa.Boolean(), nullable=False),
        sa.Column("input_hash", mysql.CHAR(length=64), nullable=True),
        sa.Column("prompt_version", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("skip_reason", sa.String(length=64), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("updated_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.CheckConstraint("kind IN ('news', 'dev')", name=op.f("ck_content_summaries_kind_valid")),
        sa.CheckConstraint(
            "status IN ('done', 'failed', 'skipped')",
            name=op.f("ck_content_summaries_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["content_id"],
            ["contents.id"],
            name=op.f("fk_content_summaries_content_id_contents"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("content_id", name=op.f("pk_content_summaries")),
    )


def downgrade() -> None:
    # MariaDB DDL is not transactional: drop the new table, then the new column.
    op.drop_table("content_summaries")
    op.drop_column("content_sources", "ai_summary")
