"""DevHub 2.0 application factory.

Run locally (from backend/):
    uv run uvicorn app.main:create_app --factory --reload

Importing this module has no side effects: no database connection, no
background threads, no external calls. The legacy entry point (backend/main.py)
is separate and is not imported here.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, content, health, learning, me, me_learning
from app.core.config import Settings, get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import REQUEST_ID_HEADER, RequestIdMiddleware, configure_logging
from app.db.session import create_db_engine, create_session_factory
from app.services.rate_limit import FailedAttemptLimiter

logger = logging.getLogger("devhub.app")

API_VERSION = "2.0.0.dev0"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    if settings.jwt_secret is None:
        raise RuntimeError("JWT_SECRET is required to run the API")
    configure_logging(settings)

    engine = create_db_engine(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        engine.dispose()

    app = FastAPI(
        title="DevHub API",
        version=API_VERSION,
        lifespan=lifespan,
        docs_url=None if settings.is_production else "/api/docs",
        redoc_url=None,
        openapi_url=None if settings.is_production else "/api/openapi.json",
    )
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    app.state.login_limiter = FailedAttemptLimiter(
        settings.login_rate_limit_attempts, settings.login_rate_limit_window_seconds
    )
    app.state.register_limiter = FailedAttemptLimiter(
        settings.register_rate_limit_attempts, settings.register_rate_limit_window_seconds
    )

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
            allow_headers=["Authorization", "Content-Type", REQUEST_ID_HEADER],
            expose_headers=[REQUEST_ID_HEADER],
        )
    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(me.router)
    app.include_router(learning.router)
    app.include_router(me_learning.router)
    app.include_router(content.router)

    logger.info(
        "DevHub API created (env=%s, database=%s)", settings.app_env, settings.database_name
    )
    return app
