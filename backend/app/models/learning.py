"""Learning catalog: tracks, units and activities.

Shared content, never copied per user. Rows are identified by human-managed slugs
and are retired instead of deleted, so future learning records keep their target.
A retired row has no position, which frees the position for its replacement.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import BigId, UtcDateTime, utc_now

CATALOG_STATUSES = ("draft", "published", "retired")
ACTIVITY_KINDS = ("reading", "video", "exercise", "external")
# How a learner confirms an activity. Only the self-check button exists today;
# the column lets stronger evidence (e.g. exercise submission) be added later.
CONFIRMATION_TYPES = ("self_check",)


def _in_list(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


_POSITIONED_UNLESS_RETIRED = "status = 'retired' OR position IS NOT NULL"


class LearningTrack(Base):
    __tablename__ = "learning_tracks"
    __table_args__ = (CheckConstraint(_in_list("status", CATALOG_STATUSES), name="status_valid"),)

    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    # Display order on the track list.
    position: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utc_now, onupdate=utc_now)

    units: Mapped[list["LearningUnit"]] = relationship(back_populates="track")


class LearningUnit(Base):
    __tablename__ = "learning_units"
    __table_args__ = (
        UniqueConstraint("track_id", "slug"),
        UniqueConstraint("track_id", "position"),
        CheckConstraint(_in_list("status", CATALOG_STATUSES), name="status_valid"),
        CheckConstraint(_POSITIONED_UNLESS_RETIRED, name="position_required"),
        CheckConstraint(
            "estimated_minutes IS NULL OR estimated_minutes > 0", name="minutes_positive"
        ),
    )

    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    track_id: Mapped[int] = mapped_column(
        BigId, ForeignKey("learning_tracks.id", ondelete="RESTRICT")
    )
    slug: Mapped[str] = mapped_column(String(64))
    position: Mapped[int | None] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str | None] = mapped_column(Text)
    estimated_minutes: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utc_now, onupdate=utc_now)

    track: Mapped[LearningTrack] = relationship(back_populates="units")
    activities: Mapped[list["LearningActivity"]] = relationship(back_populates="unit")


class LearningActivity(Base):
    __tablename__ = "learning_activities"
    __table_args__ = (
        UniqueConstraint("unit_id", "slug"),
        UniqueConstraint("unit_id", "position"),
        CheckConstraint(_in_list("status", CATALOG_STATUSES), name="status_valid"),
        CheckConstraint(_in_list("kind", ACTIVITY_KINDS), name="kind_valid"),
        CheckConstraint(_POSITIONED_UNLESS_RETIRED, name="position_required"),
        CheckConstraint("url IS NOT NULL OR body_md IS NOT NULL", name="has_content"),
        CheckConstraint(
            _in_list("confirmation_type", CONFIRMATION_TYPES), name="confirmation_valid"
        ),
    )

    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    unit_id: Mapped[int] = mapped_column(
        BigId, ForeignKey("learning_units.id", ondelete="RESTRICT")
    )
    slug: Mapped[str] = mapped_column(String(64))
    position: Mapped[int | None] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(200))
    url: Mapped[str | None] = mapped_column(String(2048))
    body_md: Mapped[str | None] = mapped_column(Text)
    is_required: Mapped[bool] = mapped_column(Boolean)
    confirmation_type: Mapped[str] = mapped_column(
        String(20), default="self_check", server_default=text("'self_check'")
    )
    status: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utc_now, onupdate=utc_now)

    unit: Mapped[LearningUnit] = relationship(back_populates="activities")


class LearningUnitTechnology(Base):
    """Which technologies a unit teaches, as stated in its content file.

    Hand-written in the unit file, so it is a reviewed link (unlike the rule-based
    tags on collected news). Used for technology-level navigation between Home, Dev
    and Career only (A-plan v0.2, P2).
    """

    __tablename__ = "learning_unit_technologies"

    unit_id: Mapped[int] = mapped_column(
        BigId, ForeignKey("learning_units.id", ondelete="RESTRICT"), primary_key=True
    )
    technology_id: Mapped[int] = mapped_column(
        BigId, ForeignKey("technologies.id", ondelete="RESTRICT"), primary_key=True, index=True
    )
