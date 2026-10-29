"""user_interests, user_skills: personalization data (A-plan v0.2, P4)

New tables only; user_settings and every other table are unchanged.

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_interests",
        sa.Column("user_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("technology_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.ForeignKeyConstraint(
            ["technology_id"],
            ["technologies.id"],
            name=op.f("fk_user_interests_technology_id_technologies"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_interests_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "technology_id", name=op.f("pk_user_interests")),
    )
    op.create_index(
        op.f("ix_user_interests_technology_id"), "user_interests", ["technology_id"], unique=False
    )
    op.create_table(
        "user_skills",
        sa.Column("user_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("technology_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("level", sa.String(length=20), nullable=False),
        sa.Column("updated_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.CheckConstraint(
            "level IN ('learning', 'used', 'confident')", name=op.f("ck_user_skills_level_valid")
        ),
        sa.ForeignKeyConstraint(
            ["technology_id"],
            ["technologies.id"],
            name=op.f("fk_user_skills_technology_id_technologies"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_user_skills_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("user_id", "technology_id", name=op.f("pk_user_skills")),
    )
    op.create_index(
        op.f("ix_user_skills_technology_id"), "user_skills", ["technology_id"], unique=False
    )


def downgrade() -> None:
    # Drop the tables only: MariaDB refuses to drop an index a foreign key still needs
    # (error 1553), and dropping a table removes its indexes anyway.
    op.drop_table("user_skills")
    op.drop_table("user_interests")
