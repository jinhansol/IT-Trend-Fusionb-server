"""learning_unit_technologies: technologies a unit teaches (A-plan v0.2, P2)

New table only; existing learning tables are unchanged.

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "learning_unit_technologies",
        sa.Column("unit_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("technology_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["technology_id"],
            ["technologies.id"],
            name=op.f("fk_learning_unit_technologies_technology_id_technologies"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["unit_id"],
            ["learning_units.id"],
            name=op.f("fk_learning_unit_technologies_unit_id_learning_units"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "unit_id", "technology_id", name=op.f("pk_learning_unit_technologies")
        ),
    )
    op.create_index(
        op.f("ix_learning_unit_technologies_technology_id"),
        "learning_unit_technologies",
        ["technology_id"],
        unique=False,
    )


def downgrade() -> None:
    # Drop the table only: MariaDB refuses to drop an index a foreign key still needs
    # (error 1553), and dropping the table removes its indexes anyway.
    op.drop_table("learning_unit_technologies")
