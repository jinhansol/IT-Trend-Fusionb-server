"""user_settings.learner_type: optional learner self-description (A-plan v0.2, P1)

Separate from users.role (authorization). Existing rows stay NULL ("not chosen").

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("user_settings", sa.Column("learner_type", sa.String(length=20), nullable=True))
    op.create_check_constraint(
        op.f("ck_user_settings_learner_type_valid"),
        "user_settings",
        "learner_type IS NULL OR learner_type IN ('beginner', 'developer', 'exploring')",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_user_settings_learner_type_valid"), "user_settings", type_="check")
    op.drop_column("user_settings", "learner_type")
