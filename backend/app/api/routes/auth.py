from fastapi import APIRouter, Cookie, Depends, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_settings, require_same_origin
from app.core.config import Settings
from app.core.errors import error_response
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest
from app.schemas.user import UserPublic
from app.services import auth as auth_service
from app.services.auth import IssuedTokens, RefreshTokenInvalid, RefreshTokenRotated

router = APIRouter(prefix="/api/auth", tags=["auth"])

REFRESH_COOKIE_NAME = "devhub_refresh"
# The browser only sends the refresh cookie to /api/auth/* (refresh, logout).
REFRESH_COOKIE_PATH = "/api/auth"


def _set_refresh_cookie(response: Response, settings: Settings, token: str) -> None:
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        token,
        max_age=settings.refresh_token_ttl_days * 24 * 60 * 60,
        path=REFRESH_COOKIE_PATH,
        secure=settings.use_secure_cookies,
        httponly=True,
        samesite="strict",
    )


def _clear_refresh_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        secure=settings.use_secure_cookies,
        httponly=True,
        samesite="strict",
    )


def _auth_response(issued: IssuedTokens) -> AuthResponse:
    return AuthResponse(
        access_token=issued.access_token,
        expires_in=issued.expires_in,
        user=UserPublic.model_validate(issued.user),
    )


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("/register", status_code=201, response_model=AuthResponse)
def register(
    body: RegisterRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthResponse:
    issued = auth_service.register_user(
        db,
        settings,
        email=body.email,
        password=body.password,
        display_name=body.display_name,
        user_agent=request.headers.get("user-agent"),
    )
    _set_refresh_cookie(response, settings, issued.refresh_token)
    return _auth_response(issued)


@router.post("/login", response_model=AuthResponse)
def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthResponse:
    issued = auth_service.login(
        db,
        settings,
        request.app.state.login_limiter,
        email=body.email,
        password=body.password,
        client_ip=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    _set_refresh_cookie(response, settings, issued.refresh_token)
    return _auth_response(issued)


@router.post("/refresh", response_model=AuthResponse, dependencies=[Depends(require_same_origin)])
def refresh(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
):
    try:
        issued = auth_service.rotate_refresh_token(
            db, settings, refresh_token, user_agent=request.headers.get("user-agent")
        )
    except RefreshTokenInvalid as exc:
        failure: JSONResponse = error_response(exc.status_code, exc.code, exc.message)
        # After a concurrent rotation the browser already holds the newer cookie.
        if not isinstance(exc, RefreshTokenRotated):
            _clear_refresh_cookie(failure, settings)
        return failure
    _set_refresh_cookie(response, settings, issued.refresh_token)
    return _auth_response(issued)


@router.post("/logout", status_code=204, dependencies=[Depends(require_same_origin)])
def logout(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
) -> Response:
    auth_service.logout(db, refresh_token)
    response = Response(status_code=204)
    _clear_refresh_cookie(response, settings)
    return response
