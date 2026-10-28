"""learning progress: quizzes, attempts, activity records, unit progress, XP ledger

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "xp_ledger",
        sa.Column("id", mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False),
        sa.Column("user_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=30), nullable=False),
        sa.Column("source_type", sa.String(length=20), nullable=False),
        sa.Column("source_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("idempotency_key", sa.String(length=100), nullable=False),
        sa.Column("policy_version", sa.String(length=20), nullable=False),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.CheckConstraint("reason IN ('unit_completed')", name=op.f("ck_xp_ledger_reason_valid")),
        sa.CheckConstraint("amount > 0", name=op.f("ck_xp_ledger_amount_positive")),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_xp_ledger_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_xp_ledger")),
        sa.UniqueConstraint(
            "user_id", "idempotency_key", name=op.f("uq_xp_ledger_user_id_idempotency_key")
        ),
    )
    op.create_index(op.f("ix_xp_ledger_user_id"), "xp_ledger", ["user_id"], unique=False)
    op.create_table(
        "quizzes",
        sa.Column("id", mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False),
        sa.Column("unit_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("pass_score_percent", sa.SmallInteger(), nullable=False),
        sa.Column("content_hash", sa.CHAR(length=64), nullable=False),
        sa.Column(
            "published_unit_id",
            mysql.BIGINT(unsigned=True),
            sa.Computed("IF(status = 'published', unit_id, NULL)", persisted=True),
            nullable=True,
        ),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("updated_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.CheckConstraint(
            "status IN ('published', 'retired')", name=op.f("ck_quizzes_status_valid")
        ),
        sa.CheckConstraint(
            "pass_score_percent BETWEEN 1 AND 100", name=op.f("ck_quizzes_pass_score_range")
        ),
        sa.ForeignKeyConstraint(
            ["unit_id"],
            ["learning_units.id"],
            name=op.f("fk_quizzes_unit_id_learning_units"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quizzes")),
        sa.UniqueConstraint("published_unit_id", name=op.f("uq_quizzes_published_unit_id")),
        sa.UniqueConstraint("unit_id", "version", name=op.f("uq_quizzes_unit_id_version")),
    )
    op.create_table(
        "quiz_attempts",
        sa.Column("id", mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False),
        sa.Column("user_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("quiz_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("client_submission_id", sa.CHAR(length=36), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("max_score", sa.Integer(), nullable=False),
        sa.Column("score_percent", sa.SmallInteger(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("submitted_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.CheckConstraint(
            "score BETWEEN 0 AND max_score", name=op.f("ck_quiz_attempts_score_range")
        ),
        sa.CheckConstraint(
            "score_percent BETWEEN 0 AND 100", name=op.f("ck_quiz_attempts_score_percent_range")
        ),
        sa.ForeignKeyConstraint(
            ["quiz_id"],
            ["quizzes.id"],
            name=op.f("fk_quiz_attempts_quiz_id_quizzes"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_quiz_attempts_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quiz_attempts")),
        sa.UniqueConstraint(
            "user_id",
            "client_submission_id",
            name=op.f("uq_quiz_attempts_user_id_client_submission_id"),
        ),
    )
    op.create_index(op.f("ix_quiz_attempts_user_id"), "quiz_attempts", ["user_id"], unique=False)
    op.create_table(
        "quiz_questions",
        sa.Column("id", mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False),
        sa.Column("quiz_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "type IN ('single', 'multiple')", name=op.f("ck_quiz_questions_type_valid")
        ),
        sa.ForeignKeyConstraint(
            ["quiz_id"],
            ["quizzes.id"],
            name=op.f("fk_quiz_questions_quiz_id_quizzes"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quiz_questions")),
        sa.UniqueConstraint("quiz_id", "key", name=op.f("uq_quiz_questions_quiz_id_key")),
        sa.UniqueConstraint("quiz_id", "position", name=op.f("uq_quiz_questions_quiz_id_position")),
    )
    op.create_table(
        "user_activity_records",
        sa.Column("user_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("activity_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("confirmation_type", sa.String(length=20), nullable=False),
        sa.Column("confirmed_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.ForeignKeyConstraint(
            ["activity_id"],
            ["learning_activities.id"],
            name=op.f("fk_user_activity_records_activity_id_learning_activities"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_activity_records_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "activity_id", name=op.f("pk_user_activity_records")),
    )
    op.create_table(
        "quiz_choices",
        sa.Column("id", mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False),
        sa.Column("question_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("key", sa.String(length=32), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["quiz_questions.id"],
            name=op.f("fk_quiz_choices_question_id_quiz_questions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quiz_choices")),
        sa.UniqueConstraint("question_id", "key", name=op.f("uq_quiz_choices_question_id_key")),
        sa.UniqueConstraint(
            "question_id", "position", name=op.f("uq_quiz_choices_question_id_position")
        ),
    )
    op.create_table(
        "user_unit_progress",
        sa.Column("user_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("unit_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("started_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("activities_completed_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.Column("quiz_passed_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.Column("passed_attempt_id", mysql.BIGINT(unsigned=True), nullable=True),
        sa.Column("completed_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.Column("last_activity_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.ForeignKeyConstraint(
            ["passed_attempt_id"],
            ["quiz_attempts.id"],
            name=op.f("fk_user_unit_progress_passed_attempt_id_quiz_attempts"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["unit_id"],
            ["learning_units.id"],
            name=op.f("fk_user_unit_progress_unit_id_learning_units"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_unit_progress_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "unit_id", name=op.f("pk_user_unit_progress")),
    )
    op.create_index(
        "ix_user_unit_progress_recent",
        "user_unit_progress",
        ["user_id", "last_activity_at"],
        unique=False,
    )
    op.create_table(
        "quiz_attempt_answers",
        sa.Column("attempt_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("question_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("choice_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["attempt_id"],
            ["quiz_attempts.id"],
            name=op.f("fk_quiz_attempt_answers_attempt_id_quiz_attempts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["choice_id"],
            ["quiz_choices.id"],
            name=op.f("fk_quiz_attempt_answers_choice_id_quiz_choices"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["quiz_questions.id"],
            name=op.f("fk_quiz_attempt_answers_question_id_quiz_questions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "attempt_id", "question_id", "choice_id", name=op.f("pk_quiz_attempt_answers")
        ),
    )
    op.add_column(
        "learning_activities",
        sa.Column(
            "confirmation_type",
            sa.String(length=20),
            server_default=sa.text("'self_check'"),
            nullable=False,
        ),
    )
    # Autogenerate does not emit CHECK constraints for columns added to existing tables.
    op.create_check_constraint(
        op.f("ck_learning_activities_confirmation_valid"),
        "learning_activities",
        "confirmation_type IN ('self_check')",
    )


def downgrade() -> None:
    # Drop tables only (children first): MariaDB refuses to drop an index a foreign
    # key still needs, and indexes go away with their table.
    for table in (
        "quiz_attempt_answers",
        "user_unit_progress",
        "user_activity_records",
        "xp_ledger",
        "quiz_attempts",
        "quiz_choices",
        "quiz_questions",
        "quizzes",
    ):
        op.drop_table(table)
    op.drop_constraint(
        op.f("ck_learning_activities_confirmation_valid"), "learning_activities", type_="check"
    )
    op.drop_column("learning_activities", "confirmation_type")
