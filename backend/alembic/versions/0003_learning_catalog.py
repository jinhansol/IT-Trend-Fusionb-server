"""learning catalog: learning_tracks, learning_units, learning_activities

Shared learning content (Phase 3). Rows are retired instead of deleted; a retired
row has no position. User progress tables come in a later revision.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "learning_tracks",
        sa.Column("id", mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("updated_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.CheckConstraint(
            "status IN ('draft', 'published', 'retired')",
            name=op.f("ck_learning_tracks_status_valid"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_learning_tracks")),
        sa.UniqueConstraint("slug", name=op.f("uq_learning_tracks_slug")),
    )
    op.create_table(
        "learning_units",
        sa.Column("id", mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False),
        sa.Column("track_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("position", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("estimated_minutes", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("updated_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.CheckConstraint(
            "status = 'retired' OR position IS NOT NULL",
            name=op.f("ck_learning_units_position_required"),
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'published', 'retired')",
            name=op.f("ck_learning_units_status_valid"),
        ),
        sa.CheckConstraint(
            "estimated_minutes IS NULL OR estimated_minutes > 0",
            name=op.f("ck_learning_units_minutes_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["track_id"],
            ["learning_tracks.id"],
            name=op.f("fk_learning_units_track_id_learning_tracks"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_learning_units")),
        sa.UniqueConstraint(
            "track_id", "position", name=op.f("uq_learning_units_track_id_position")
        ),
        sa.UniqueConstraint("track_id", "slug", name=op.f("uq_learning_units_track_id_slug")),
    )
    op.create_table(
        "learning_activities",
        sa.Column("id", mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False),
        sa.Column("unit_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("position", sa.Integer(), nullable=True),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=True),
        sa.Column("body_md", sa.Text(), nullable=True),
        sa.Column("is_required", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("updated_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.CheckConstraint(
            "kind IN ('reading', 'video', 'exercise', 'external')",
            name=op.f("ck_learning_activities_kind_valid"),
        ),
        sa.CheckConstraint(
            "status = 'retired' OR position IS NOT NULL",
            name=op.f("ck_learning_activities_position_required"),
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'published', 'retired')",
            name=op.f("ck_learning_activities_status_valid"),
        ),
        sa.CheckConstraint(
            "url IS NOT NULL OR body_md IS NOT NULL",
            name=op.f("ck_learning_activities_has_content"),
        ),
        sa.ForeignKeyConstraint(
            ["unit_id"],
            ["learning_units.id"],
            name=op.f("fk_learning_activities_unit_id_learning_units"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_learning_activities")),
        sa.UniqueConstraint(
            "unit_id", "position", name=op.f("uq_learning_activities_unit_id_position")
        ),
        sa.UniqueConstraint("unit_id", "slug", name=op.f("uq_learning_activities_unit_id_slug")),
    )


def downgrade() -> None:
    op.drop_table("learning_activities")
    op.drop_table("learning_units")
    op.drop_table("learning_tracks")
