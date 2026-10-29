"""Career roles (jobs), the technologies they use, and the roles a user saved.

Roles are public content managed in a YAML file like the technology taxonomy:
retired instead of deleted, so saved candidates and goals keep their target.
Candidates are the user's own records, written only by the career candidate
service; it never writes learning goals, settings or learning progress.
"""

from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import BigId, UtcDateTime, utc_now
from app.models.learning import _in_list

ROLE_STATUSES = ("published", "retired")
ROLE_TECHNOLOGY_IMPORTANCE = ("core", "related")


class CareerRole(Base):
    __tablename__ = "career_roles"
    __table_args__ = (CheckConstraint(_in_list("status", ROLE_STATUSES), name="status_valid"),)

    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    summary: Mapped[str] = mapped_column(String(300))
    description_md: Mapped[str] = mapped_column(Text)
    # Typical tasks (list of strings) and supporting sources ([{title, url}]).
    tasks: Mapped[list] = mapped_column(JSON)
    # "references" is a reserved word in MariaDB.
    reference_links: Mapped[list] = mapped_column(JSON)
    # Fixed list order: the same for every visitor, never per user or learner type.
    position: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utc_now, onupdate=utc_now)


class CareerRoleTechnology(Base):
    """Many-to-many: a technology can belong to several roles."""

    __tablename__ = "career_role_technologies"
    __table_args__ = (
        CheckConstraint(
            _in_list("importance", ROLE_TECHNOLOGY_IMPORTANCE), name="importance_valid"
        ),
    )

    role_id: Mapped[int] = mapped_column(
        BigId, ForeignKey("career_roles.id", ondelete="RESTRICT"), primary_key=True
    )
    technology_id: Mapped[int] = mapped_column(
        BigId, ForeignKey("technologies.id", ondelete="RESTRICT"), primary_key=True, index=True
    )
    importance: Mapped[str] = mapped_column(String(20))
    position: Mapped[int] = mapped_column(Integer)


class UserCareerCandidate(Base):
    """A role the user saved while exploring. Not saving it is how "undecided" looks."""

    __tablename__ = "user_career_candidates"

    user_id: Mapped[int] = mapped_column(
        BigId, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[int] = mapped_column(
        BigId, ForeignKey("career_roles.id", ondelete="RESTRICT"), primary_key=True, index=True
    )
    note: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utc_now, onupdate=utc_now)
