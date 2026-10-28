"""Password hashing and token primitives.

- Passwords: argon2id (argon2-cffi defaults).
- Access tokens: short-lived JWT (HS256) whose subject is the user id.
- Refresh tokens: opaque random strings; only their SHA-256 hash is stored.
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from functools import lru_cache

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import Settings

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_BYTES = 32

_password_hasher = PasswordHasher()


class InvalidAccessTokenError(Exception):
    pass


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    return _password_hasher.check_needs_rehash(password_hash)


@lru_cache(maxsize=1)
def _dummy_password_hash() -> str:
    return _password_hasher.hash(secrets.token_urlsafe(16))


def burn_password_check(password: str) -> None:
    """Spend the same time as a real check when the account does not exist."""
    verify_password(password, _dummy_password_hash())


def _jwt_key(settings: Settings) -> str:
    if settings.jwt_secret is None:
        raise RuntimeError("JWT_SECRET is not configured")
    return settings.jwt_secret.get_secret_value()


def create_access_token(
    user_id: int, settings: Settings, *, now: datetime | None = None
) -> tuple[str, int]:
    issued_at = now or datetime.now(UTC)
    ttl = settings.access_token_ttl_seconds
    payload = {
        "sub": str(user_id),
        "type": ACCESS_TOKEN_TYPE,
        "iat": issued_at,
        "exp": issued_at + timedelta(seconds=ttl),
    }
    return jwt.encode(payload, _jwt_key(settings), algorithm=JWT_ALGORITHM), ttl


def decode_access_token(token: str, settings: Settings) -> int:
    """Return the user id, or raise InvalidAccessTokenError."""
    try:
        payload = jwt.decode(
            token,
            _jwt_key(settings),
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "type", "iat", "exp"]},
        )
    except jwt.PyJWTError as exc:
        raise InvalidAccessTokenError(type(exc).__name__) from exc

    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise InvalidAccessTokenError("wrong token type")
    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject.isdigit():
        raise InvalidAccessTokenError("invalid subject")
    return int(subject)


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(REFRESH_TOKEN_BYTES)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_token_family_id() -> str:
    return secrets.token_hex(16)
