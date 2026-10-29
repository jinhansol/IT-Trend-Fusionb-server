"""career roles, role technologies, saved candidates and learning goals (A-plan v0.2, P3)

New tables only; existing tables are unchanged.

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "career_roles",
        sa.Column("id", mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("summary", sa.String(length=300), nullable=False),
        sa.Column("description_md", sa.Text(), nullable=False),
        sa.Column("tasks", sa.JSON(), nullable=False),
        sa.Column("reference_links", sa.JSON(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("updated_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.CheckConstraint(
            "status IN ('published', 'retired')", name=op.f("ck_career_roles_status_valid")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_career_roles")),
        sa.UniqueConstraint("slug", name=op.f("uq_career_roles_slug")),
    )
    op.create_table(
        "career_role_technologies",
        sa.Column("role_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("technology_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("importance", sa.String(length=20), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "importance IN ('core', 'related')",
            name=op.f("ck_career_role_technologies_importance_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["career_roles.id"],
            name=op.f("fk_career_role_technologies_role_id_career_roles"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["technology_id"],
            ["technologies.id"],
            name=op.f("fk_career_role_technologies_technology_id_technologies"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "role_id", "technology_id", name=op.f("pk_career_role_technologies")
        ),
    )
    op.create_index(
        op.f("ix_career_role_technologies_technology_id"),
        "career_role_technologies",
        ["technology_id"],
        unique=False,
    )
    op.create_table(
        "learning_goals",
        sa.Column("id", mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False),
        sa.Column("user_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("role_id", mysql.BIGINT(unsigned=True), nullable=True),
        sa.Column("technology_id", mysql.BIGINT(unsigned=True), nullable=True),
        sa.Column("track_id", mysql.BIGINT(unsigned=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("achieved_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("updated_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.CheckConstraint(
            "(status = 'achieved') = (achieved_at IS NOT NULL)",
            name=op.f("ck_learning_goals_achieved_at_matches"),
        ),
        sa.CheckConstraint(
            "status IN ('active', 'achieved', 'archived')",
            name=op.f("ck_learning_goals_status_valid"),
        ),
        sa.CheckConstraint(
            "(role_id IS NOT NULL) + (technology_id IS NOT NULL) + (track_id IS NOT NULL) <= 1",
            name=op.f("ck_learning_goals_one_target"),
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["career_roles.id"],
            name=op.f("fk_learning_goals_role_id_career_roles"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["technology_id"],
            ["technologies.id"],
            name=op.f("fk_learning_goals_technology_id_technologies"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["track_id"],
            ["learning_tracks.id"],
            name=op.f("fk_learning_goals_track_id_learning_tracks"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_learning_goals_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_learning_goals")),
    )
    op.create_index(op.f("ix_learning_goals_role_id"), "learning_goals", ["role_id"], unique=False)
    op.create_index(
        op.f("ix_learning_goals_technology_id"), "learning_goals", ["technology_id"], unique=False
    )
    op.create_index(
        op.f("ix_learning_goals_track_id"), "learning_goals", ["track_id"], unique=False
    )
    op.create_index(
        "ix_learning_goals_user_status", "learning_goals", ["user_id", "status"], unique=False
    )
    op.create_table(
        "user_career_candidates",
        sa.Column("user_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("role_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("note", sa.String(length=200), nullable=True),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("updated_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["career_roles.id"],
            name=op.f("fk_user_career_candidates_role_id_career_roles"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_career_candidates_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "role_id", name=op.f("pk_user_career_candidates")),
    )
    op.create_index(
        op.f("ix_user_career_candidates_role_id"),
        "user_career_candidates",
        ["role_id"],
        unique=False,
    )


def downgrade() -> None:
    # Drop the tables only: MariaDB refuses to drop an index a foreign key still needs
    # (error 1553), and dropping a table removes its indexes anyway.
    op.drop_table("user_career_candidates")
    op.drop_table("learning_goals")
    op.drop_table("career_role_technologies")
    op.drop_table("career_roles")
