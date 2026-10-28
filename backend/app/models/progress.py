"""Per-user learning records: confirmed activities, unit progress, XP ledger.

Personal rows are deleted with the account (CASCADE); the catalog rows they
point at can never be deleted while referenced (RESTRICT).
"""

from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import BigId, UtcDateTime, utc_now

XP_REASONS = ("unit_completed",)


class UserActivityRecord(Base):
    """A learner confirmed an activity. One row per user and activity."""

    __tablename__ = "user_activity_records"

    user_id: Mapped[int] = mapped_column(
        BigId, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    activity_id: Mapped[int] = mapped_column(
        BigId, ForeignKey("learning_activities.id", ondelete="RESTRICT"), primary_key=True
    )
    confirmation_type: Mapped[str] = mapped_column(String(20))
    confirmed_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utc_now)


class UserUnitProgress(Base):
    """Where a learner stands in a unit. completed_at is set once and never cleared.

    State is derived: no row = not started, completed_at set = completed,
    otherwise in progress.
    """

    __tablename__ = "user_unit_progress"
    __table_args__ = (Index("ix_user_unit_progress_recent", "user_id", "last_activity_at"),)

    user_id: Mapped[int] = mapped_column(
        BigId, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    unit_id: Mapped[int] = mapped_column(
        BigId, ForeignKey("learning_units.id", ondelete="RESTRICT"), primary_key=True
    )
    started_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utc_now)
    activities_completed_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    quiz_passed_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    passed_attempt_id: Mapped[int | None] = mapped_column(
        BigId, ForeignKey("quiz_attempts.id", ondelete="SET NULL")
    )
    completed_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    last_activity_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utc_now)


class XpLedgerEntry(Base):
    """Append-only reward ledger. Total XP is the sum; level is derived from it.
    (user_id, idempotency_key) makes it impossible to grant the same reward twice."""

    __tablename__ = "xp_ledger"
    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key"),
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint(
            f"reason IN ({', '.join(repr(r) for r in XP_REASONS)})", name="reason_valid"
        ),
    )

    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigId, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    amount: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(30))
    source_type: Mapped[str] = mapped_column(String(20))
    source_id: Mapped[int] = mapped_column(BigId)
    idempotency_key: Mapped[str] = mapped_column(String(100))
    policy_version: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utc_now)
