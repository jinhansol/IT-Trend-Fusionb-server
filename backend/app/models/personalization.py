"""Personalization data: technologies a user is interested in and how they rate
their own skill with a technology (A-plan v0.2, P4).

Only services/personalization.py reads or writes these tables. They are kept when
personalization is turned OFF (and then never used for recommendations) and are the
only rows a personalization reset deletes. Skill levels are the user's own rating,
not a verified proficiency.
"""

from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import BigId, UtcDateTime, utc_now
from app.models.learning import _in_list

SKILL_LEVELS = ("learning", "used", "confident")


class UserInterest(Base):
    __tablename__ = "user_interests"

    user_id: Mapped[int] = mapped_column(
        BigId, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    technology_id: Mapped[int] = mapped_column(
        BigId, ForeignKey("technologies.id", ondelete="RESTRICT"), primary_key=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utc_now)


class UserSkill(Base):
    __tablename__ = "user_skills"
    __table_args__ = (CheckConstraint(_in_list("level", SKILL_LEVELS), name="level_valid"),)

    user_id: Mapped[int] = mapped_column(
        BigId, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    technology_id: Mapped[int] = mapped_column(
        BigId, ForeignKey("technologies.id", ondelete="RESTRICT"), primary_key=True, index=True
    )
    level: Mapped[str] = mapped_column(String(20))
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utc_now, onupdate=utc_now)
