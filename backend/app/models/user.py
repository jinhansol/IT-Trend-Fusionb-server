from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import CHAR

from app.db.base import Base
from app.db.types import BigId, UtcDateTime, utc_now

USER_ROLES = ("user", "admin")
USER_STATUSES = ("active", "disabled")
# How a learner describes themself. Used only for static start guidance and menu
# links, never for ranking, recommendations or access (A-plan v0.2, C-2). Separate
# from users.role, which is the authorization role.
LEARNER_TYPES = ("beginner", "developer", "exploring")


def _in_list(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class User(Base):
    """Authentication identity. Profile-style data lives in separate tables."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(_in_list("role", USER_ROLES), name="role_valid"),
        CheckConstraint(_in_list("status", USER_STATUSES), name="status_valid"),
    )

    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    # Stored lower-cased by the auth service and compared byte-for-byte: the default
    # collation is accent-insensitive and would treat different addresses as equal.
    email: Mapped[str] = mapped_column(String(255, collation="utf8mb4_bin"), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(50))
    role: Mapped[str] = mapped_column(String(20), default="user", server_default=text("'user'"))
    status: Mapped[str] = mapped_column(
        String(20), default="active", server_default=text("'active'")
    )
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utc_now, onupdate=utc_now)
    last_login_at: Mapped[datetime | None] = mapped_column(UtcDateTime)

    user_settings: Mapped["UserSettings"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan", passive_deletes=True
    )

    @property
    def is_active(self) -> bool:
        return self.status == "active"


class UserSettings(Base):
    """Per-user switches. Personalization is OFF until the user turns it on."""

    __tablename__ = "user_settings"
    __table_args__ = (
        CheckConstraint(
            f"learner_type IS NULL OR {_in_list('learner_type', LEARNER_TYPES)}",
            name="learner_type_valid",
        ),
    )

    user_id: Mapped[int] = mapped_column(
        BigId, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    personalization_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("0")
    )
    # Optional; NULL means "not chosen". Changeable at any time.
    learner_type: Mapped[str | None] = mapped_column(String(20))
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utc_now, onupdate=utc_now)

    user: Mapped[User] = relationship(back_populates="user_settings")


class RefreshToken(Base):
    """One row per issued refresh token. Rotation links a token to its successor;
    all tokens from one login share a family so reuse can revoke them together."""

    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigId, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(CHAR(64), unique=True)
    family_id: Mapped[str] = mapped_column(CHAR(32), index=True)
    expires_at: Mapped[datetime] = mapped_column(UtcDateTime)
    revoked_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    replaced_by_id: Mapped[int | None] = mapped_column(
        BigId, ForeignKey("refresh_tokens.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utc_now)
    user_agent: Mapped[str | None] = mapped_column(String(255))
