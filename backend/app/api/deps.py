from collections.abc import Iterator
from urllib.parse import urlsplit

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import InvalidAccessTokenError, decode_access_token
from app.models.user import User

_bearer = HTTPBearer(auto_error=False)


def get_db(request: Request) -> Iterator[Session]:
    """One session per request. Read endpoints never commit; write use cases
    open their own transaction with ``with db.begin():``."""
    session: Session = request.app.state.session_factory()
    try:
        yield session
    finally:
        session.close()


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def _unauthorized() -> AppError:
    return AppError(
        "Authentication required",
        code="UNAUTHORIZED",
        status_code=401,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    """The user identified by the access token. Personal endpoints must use this
    instead of accepting a user id from the path or body."""
    if credentials is None:
        raise _unauthorized()
    try:
        user_id = decode_access_token(credentials.credentials, settings)
    except InvalidAccessTokenError as exc:
        raise _unauthorized() from exc

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _unauthorized()
    # End the read transaction so write use cases can open their own with db.begin().
    db.commit()
    return user


def require_same_origin(request: Request, settings: Settings = Depends(get_settings)) -> None:
    """Reject cross-site requests to cookie-authenticated endpoints.
    SameSite=Strict already blocks the cookie; this is a second layer."""
    origin = request.headers.get("origin")
    if origin is None:
        return
    if urlsplit(origin).netloc == request.headers.get("host") or origin in settings.cors_origins:
        return
    raise AppError("Origin not allowed", code="ORIGIN_NOT_ALLOWED", status_code=403)
