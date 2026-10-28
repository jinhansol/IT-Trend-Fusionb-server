"""content collection: technologies, sources, contents, tags, job runs

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "content_sources",
        sa.Column("id", mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("adapter", sa.String(length=20), nullable=False),
        sa.Column("site_url", sa.String(length=2048), nullable=False),
        sa.Column("feed_url", sa.String(length=2048), nullable=True),
        sa.Column("language", sa.String(length=10), nullable=False),
        sa.Column("options", sa.JSON(), nullable=False),
        sa.Column("max_items", sa.Integer(), nullable=False),
        sa.Column("channel", sa.String(length=64), nullable=True),
        sa.Column("channel_name", sa.String(length=100), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("updated_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.CheckConstraint(
            "adapter IN ('rss', 'devto', 'hackernews', 'stackoverflow')",
            name=op.f("ck_content_sources_adapter_valid"),
        ),
        sa.CheckConstraint(
            "kind IN ('news', 'blog', 'community', 'qna')",
            name=op.f("ck_content_sources_kind_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('active', 'paused', 'retired')",
            name=op.f("ck_content_sources_status_valid"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_content_sources")),
        sa.UniqueConstraint("slug", name=op.f("uq_content_sources_slug")),
    )
    op.create_table(
        "technologies",
        sa.Column("id", mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("updated_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.CheckConstraint(
            "kind IN ('language', 'framework', 'library', 'tool', 'platform', 'field')",
            name=op.f("ck_technologies_kind_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('published', 'retired')", name=op.f("ck_technologies_status_valid")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_technologies")),
        sa.UniqueConstraint("slug", name=op.f("uq_technologies_slug")),
    )
    op.create_table(
        "contents",
        sa.Column("id", mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False),
        sa.Column("source_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("url_hash", mysql.CHAR(length=64), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("summary_status", sa.String(length=20), nullable=False),
        sa.Column("author", sa.String(length=200), nullable=True),
        sa.Column("source_tags", sa.JSON(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("comment_count", sa.Integer(), nullable=True),
        sa.Column("view_count", sa.Integer(), nullable=True),
        sa.Column("published_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.Column("collected_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("updated_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column(
            "sort_at",
            mysql.DATETIME(fsp=6),
            sa.Computed("COALESCE(published_at, collected_at)", persisted=True),
            nullable=True,
        ),
        sa.CheckConstraint(
            "summary_status IN ('pending', 'done', 'failed', 'skipped')",
            name=op.f("ck_contents_summary_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["content_sources.id"],
            name=op.f("fk_contents_source_id_content_sources"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_contents")),
        sa.UniqueConstraint("source_id", "url_hash", name=op.f("uq_contents_source_id_url_hash")),
    )
    op.create_index("ix_contents_sort", "contents", ["sort_at", "id"], unique=False)
    op.create_index(
        "ix_contents_source_sort", "contents", ["source_id", "sort_at", "id"], unique=False
    )
    op.create_table(
        "job_runs",
        sa.Column("id", mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False),
        sa.Column("job_name", sa.String(length=64), nullable=False),
        sa.Column("source_id", mysql.BIGINT(unsigned=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("started_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("finished_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.Column("fetched_count", sa.Integer(), nullable=False),
        sa.Column("inserted_count", sa.Integer(), nullable=False),
        sa.Column("updated_count", sa.Integer(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("error_summary", sa.String(length=1000), nullable=True),
        sa.CheckConstraint(
            "status IN ('running', 'succeeded', 'failed', 'skipped')",
            name=op.f("ck_job_runs_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["content_sources.id"],
            name=op.f("fk_job_runs_source_id_content_sources"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_job_runs")),
    )
    op.create_index(
        "ix_job_runs_source_started", "job_runs", ["source_id", "started_at"], unique=False
    )
    op.create_table(
        "technology_aliases",
        sa.Column("id", mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False),
        sa.Column("technology_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("alias", sa.String(length=100), nullable=False),
        sa.Column("tag_only", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["technology_id"],
            ["technologies.id"],
            name=op.f("fk_technology_aliases_technology_id_technologies"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_technology_aliases")),
        sa.UniqueConstraint("alias", name=op.f("uq_technology_aliases_alias")),
    )
    op.create_table(
        "content_technologies",
        sa.Column("content_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("technology_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("method", sa.String(length=20), nullable=False),
        sa.CheckConstraint(
            "method IN ('rule', 'llm', 'manual')", name=op.f("ck_content_technologies_method_valid")
        ),
        sa.ForeignKeyConstraint(
            ["content_id"],
            ["contents.id"],
            name=op.f("fk_content_technologies_content_id_contents"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["technology_id"],
            ["technologies.id"],
            name=op.f("fk_content_technologies_technology_id_technologies"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "content_id", "technology_id", name=op.f("pk_content_technologies")
        ),
    )
    op.create_index(
        op.f("ix_content_technologies_technology_id"),
        "content_technologies",
        ["technology_id"],
        unique=False,
    )


def downgrade() -> None:
    # Drop tables only: MariaDB refuses to drop an index a foreign key still needs
    # (error 1553), and dropping the table removes its indexes anyway.
    for table in (
        "content_technologies",
        "technology_aliases",
        "job_runs",
        "contents",
        "technologies",
        "content_sources",
    ):
        op.drop_table(table)
