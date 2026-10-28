"""Application settings.

Settings are read from environment variables (and ``backend/.env`` for local
development). Nothing here connects to the database; validation only inspects
the configured values.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError

AppEnv = Literal["local", "test", "production"]

TEST_DATABASE_SUFFIX = "_test"
# Values copied from .env.example must never reach production.
PLACEHOLDER_PASSWORD_MARKERS = ("change-me", "changeme", "devhub_local")
MIN_PRODUCTION_JWT_SECRET_BYTES = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: AppEnv = "local"
    database_url: SecretStr
    log_level: str = "INFO"
    # None means "JSON in production, plain text elsewhere".
    log_json: bool | None = None
    # JSON list, e.g. CORS_ORIGINS='["https://devhub.example"]'. Empty disables CORS.
    cors_origins: list[str] = []
    db_pool_recycle_seconds: int = 1800

    # Authentication. JWT_SECRET is required to run the API (not for Alembic).
    jwt_secret: SecretStr | None = None
    access_token_ttl_seconds: int = Field(default=900, gt=0)
    refresh_token_ttl_days: int = Field(default=14, gt=0)
    # A rotated refresh token reused within this window is treated as a
    # concurrent refresh (another tab), not as theft.
    refresh_reuse_grace_seconds: int = Field(default=10, ge=0)
    # None means "Secure in production only" (local dev runs over plain http).
    refresh_cookie_secure: bool | None = None
    login_rate_limit_attempts: int = Field(default=10, gt=0)
    login_rate_limit_window_seconds: int = Field(default=600, gt=0)

    @model_validator(mode="after")
    def _validate_environment(self) -> "Settings":
        url = self.parsed_database_url()
        if url.get_backend_name() not in ("mysql", "mariadb"):
            raise ValueError("DATABASE_URL must use a MariaDB/MySQL driver (mysql+pymysql://...)")
        if not url.database:
            raise ValueError("DATABASE_URL must include a database name")

        is_test_db = url.database.endswith(TEST_DATABASE_SUFFIX)
        if self.app_env == "test" and not is_test_db:
            raise ValueError(
                f"APP_ENV=test requires a database name ending with '{TEST_DATABASE_SUFFIX}'"
            )
        if self.app_env != "test" and is_test_db:
            raise ValueError(
                f"APP_ENV={self.app_env} must not use a '{TEST_DATABASE_SUFFIX}' database"
            )

        if self.app_env == "production":
            if url.username == "root":
                raise ValueError("production must not connect as the MariaDB root user")
            password = (url.password or "").lower()
            if not password or any(marker in password for marker in PLACEHOLDER_PASSWORD_MARKERS):
                raise ValueError("production DATABASE_URL has an empty or placeholder password")
            self._validate_production_auth()
        return self

    def _validate_production_auth(self) -> None:
        secret = self.jwt_secret.get_secret_value() if self.jwt_secret else ""
        if len(secret.encode()) < MIN_PRODUCTION_JWT_SECRET_BYTES:
            raise ValueError(
                "production requires JWT_SECRET of at least "
                f"{MIN_PRODUCTION_JWT_SECRET_BYTES} bytes"
            )
        if any(marker in secret.lower() for marker in PLACEHOLDER_PASSWORD_MARKERS):
            raise ValueError("production JWT_SECRET is a placeholder value")
        if self.refresh_cookie_secure is False:
            raise ValueError("production must not disable REFRESH_COOKIE_SECURE")

    def parsed_database_url(self) -> URL:
        try:
            return make_url(self.database_url.get_secret_value())
        except ArgumentError as exc:
            raise ValueError("DATABASE_URL is not a valid SQLAlchemy URL") from exc

    @property
    def database_name(self) -> str:
        return self.parsed_database_url().database or ""

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def use_json_logs(self) -> bool:
        return self.is_production if self.log_json is None else self.log_json

    @property
    def use_secure_cookies(self) -> bool:
        if self.refresh_cookie_secure is None:
            return self.is_production
        return self.refresh_cookie_secure


@lru_cache
def get_settings() -> Settings:
    return Settings()
