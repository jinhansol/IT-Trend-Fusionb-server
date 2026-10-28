"""Registration, login, refresh-token rotation and logout.

Each public function is one use case and owns its transaction (``with db.begin()``).
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import (
    burn_password_check,
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    new_token_family_id,
    password_needs_rehash,
    verify_password,
)
from app.db.types import utc_now
from app.models.user import RefreshToken, User, UserSettings
from app.services.rate_limit import FailedAttemptLimiter

logger = logging.getLogger("devhub.auth")

ER_DUP_ENTRY = 1062
USER_AGENT_MAX_LENGTH = 255


class EmailAlreadyRegistered(AppError):
    status_code = 409
    code = "EMAIL_ALREADY_REGISTERED"

    def __init__(self) -> None:
        super().__init__("An account with this email already exists")


class InvalidCredentials(AppError):
    status_code = 401
    code = "INVALID_CREDENTIALS"

    def __init__(self) -> None:
        super().__init__("Invalid email or password")


class TooManyAttempts(AppError):
    status_code = 429
    code = "TOO_MANY_ATTEMPTS"

    def __init__(self, retry_after: int) -> None:
        super().__init__(
            "Too many failed login attempts. Try again later.",
            details={"retry_after": retry_after},
            headers={"Retry-After": str(retry_after)},
        )


class RefreshTokenInvalid(AppError):
    status_code = 401
    code = "REFRESH_TOKEN_INVALID"

    def __init__(self) -> None:
        super().__init__("Session expired. Please log in again.")


class RefreshTokenRotated(RefreshTokenInvalid):
    """The token was just rotated by a concurrent request (e.g. another tab).
    The client should retry once with the cookie it now holds."""

    code = "REFRESH_TOKEN_ROTATED"


@dataclass(frozen=True)
class IssuedTokens:
    user: User
    access_token: str
    expires_in: int
    refresh_token: str


def normalize_email(email: str) -> str:
    return email.strip().lower()


def register_user(
    db: Session,
    settings: Settings,
    *,
    email: str,
    password: str,
    display_name: str,
    user_agent: str | None,
) -> IssuedTokens:
    password_hash = hash_password(password)  # slow; keep it outside the transaction
    try:
        with db.begin():
            user = User(
                email=normalize_email(email),
                password_hash=password_hash,
                display_name=display_name,
                last_login_at=utc_now(),
            )
            user.user_settings = UserSettings()
            db.add(user)
            db.flush()
            refresh_token, _ = _issue_refresh_token(
                db, settings, user.id, family_id=new_token_family_id(), user_agent=user_agent
            )
    except IntegrityError as exc:
        if _is_duplicate_email(exc):
            raise EmailAlreadyRegistered() from exc
        raise
    return _issued(user, settings, refresh_token)


def login(
    db: Session,
    settings: Settings,
    limiter: FailedAttemptLimiter,
    *,
    email: str,
    password: str,
    client_ip: str,
    user_agent: str | None,
) -> IssuedTokens:
    email = normalize_email(email)
    limiter_key = f"{email}|{client_ip}"
    retry_after = limiter.retry_after(limiter_key)
    if retry_after is not None:
        raise TooManyAttempts(retry_after)

    with db.begin():
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            burn_password_check(password)
            authenticated = False
        else:
            # Disabled accounts get the same answer as a wrong password.
            authenticated = verify_password(password, user.password_hash) and user.is_active

        if not authenticated:
            limiter.record_failure(limiter_key)
            raise InvalidCredentials()

        limiter.reset(limiter_key)
        if password_needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)
        user.last_login_at = utc_now()
        refresh_token, _ = _issue_refresh_token(
            db, settings, user.id, family_id=new_token_family_id(), user_agent=user_agent
        )
    return _issued(user, settings, refresh_token)


def rotate_refresh_token(
    db: Session, settings: Settings, raw_token: str | None, *, user_agent: str | None
) -> IssuedTokens:
    if not raw_token:
        raise RefreshTokenInvalid()

    now = utc_now()
    rejected_after_commit = False
    with db.begin():
        current = db.scalar(
            select(RefreshToken)
            .where(RefreshToken.token_hash == hash_refresh_token(raw_token))
            .with_for_update()
        )
        if current is None:
            raise RefreshTokenInvalid()

        if current.revoked_at is not None:
            grace = timedelta(seconds=settings.refresh_reuse_grace_seconds)
            if current.replaced_by_id is not None and now - current.revoked_at <= grace:
                raise RefreshTokenRotated()
            # A revoked token came back: assume it was stolen and end the whole login.
            _revoke_family(db, current.family_id, now)
            logger.warning("Refresh token reuse detected; token family revoked")
            rejected_after_commit = True
        elif current.expires_at <= now:
            raise RefreshTokenInvalid()
        else:
            user = db.get(User, current.user_id)
            if user is None or not user.is_active:
                current.revoked_at = now
                rejected_after_commit = True
            else:
                refresh_token, successor = _issue_refresh_token(
                    db, settings, user.id, family_id=current.family_id, user_agent=user_agent
                )
                current.revoked_at = now
                current.replaced_by_id = successor.id

    if rejected_after_commit:
        raise RefreshTokenInvalid()
    return _issued(user, settings, refresh_token)


def logout(db: Session, raw_token: str | None) -> None:
    if not raw_token:
        return
    with db.begin():
        db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.token_hash == hash_refresh_token(raw_token),
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=utc_now())
        )


def _issue_refresh_token(
    db: Session, settings: Settings, user_id: int, *, family_id: str, user_agent: str | None
) -> tuple[str, RefreshToken]:
    raw_token = generate_refresh_token()
    row = RefreshToken(
        user_id=user_id,
        token_hash=hash_refresh_token(raw_token),
        family_id=family_id,
        expires_at=utc_now() + timedelta(days=settings.refresh_token_ttl_days),
        user_agent=(user_agent or "")[:USER_AGENT_MAX_LENGTH] or None,
    )
    db.add(row)
    db.flush()
    return raw_token, row


def _revoke_family(db: Session, family_id: str, now: datetime) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )


def _issued(user: User, settings: Settings, refresh_token: str) -> IssuedTokens:
    access_token, expires_in = create_access_token(user.id, settings)
    return IssuedTokens(user, access_token, expires_in, refresh_token)


def _is_duplicate_email(exc: IntegrityError) -> bool:
    args = getattr(exc.orig, "args", ())
    return len(args) >= 2 and args[0] == ER_DUP_ENTRY and "uq_users_email" in str(args[1])
