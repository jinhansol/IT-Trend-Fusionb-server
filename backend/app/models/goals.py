"""Learning goals: Career growth data the user writes themself (A-plan v0.2, C-1).

Saved with personalization ON or OFF and never cleared by a personalization reset.
Only the learning goal service writes this table, and only on the user's request:
career exploration never creates or changes a goal. Goals do not touch learning
progress or XP.
"""

from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import BigId, UtcDateTime, utc_now
from app.models.learning import _in_list

GOAL_STATUSES = ("active", "achieved", "archived")


class LearningGoal(Base):
    __tablename__ = "learning_goals"
    __table_args__ = (
        CheckConstraint(_in_list("status", GOAL_STATUSES), name="status_valid"),
        # At most one target: a role, a technology or a track (none = free-form goal).
        CheckConstraint(
            "(role_id IS NOT NULL) + (technology_id IS NOT NULL) + (track_id IS NOT NULL) <= 1",
            name="one_target",
        ),
        # achieved_at is set exactly while the goal is achieved.
        CheckConstraint(
            "(status = 'achieved') = (achieved_at IS NOT NULL)", name="achieved_at_matches"
        ),
        Index("ix_learning_goals_user_status", "user_id", "status"),
    )

    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigId, ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(100))
    role_id: Mapped[int | None] = mapped_column(
        BigId, ForeignKey("career_roles.id", ondelete="RESTRICT"), index=True
    )
    technology_id: Mapped[int | None] = mapped_column(
        BigId, ForeignKey("technologies.id", ondelete="RESTRICT"), index=True
    )
    track_id: Mapped[int | None] = mapped_column(
        BigId, ForeignKey("learning_tracks.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[str] = mapped_column(String(20))
    target_date: Mapped[date | None] = mapped_column(Date)
    achieved_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utc_now, onupdate=utc_now)
