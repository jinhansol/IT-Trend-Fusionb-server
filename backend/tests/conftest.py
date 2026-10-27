"""Shared fixtures.

Unit tests never open a database connection (they use an unreachable URL).
Integration tests use TEST_DATABASE_URL and refuse to run unless the live
connection really points at a '*_test' database.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic.config import Config
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import Connection, Engine

from app.core.config import Settings
from app.db.safety import assert_test_database
from app.db.session import create_db_engine

BACKEND_DIR = Path(__file__).resolve().parents[1]

# Port 9 (discard) on loopback: connection attempts fail fast, nothing is reached.
UNIT_DB_PASSWORD = "unit-secret-pw"
UNIT_DATABASE_URL = f"mysql+pymysql://devhub_unit:{UNIT_DB_PASSWORD}@127.0.0.1:9/devhub_unit"


def make_settings(**overrides) -> Settings:
    values = {"app_env": "local", "database_url": UNIT_DATABASE_URL, "log_level": "INFO"}
    values.update(overrides)
    return Settings(_env_file=None, **values)


class _TestEnvironment(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    test_database_url: str | None = None


@pytest.fixture(scope="session")
def integration_settings() -> Settings:
    url = _TestEnvironment().test_database_url
    if not url:
        pytest.fail(
            "TEST_DATABASE_URL is not set. Start MariaDB with "
            "'docker compose up -d --wait mariadb' and set TEST_DATABASE_URL "
            "(see backend/.env.example), or deselect with -m 'not integration'.",
            pytrace=False,
        )
    return Settings(_env_file=None, app_env="test", database_url=url)


@pytest.fixture(scope="session")
def test_engine(integration_settings: Settings) -> Iterator[Engine]:
    engine = create_db_engine(integration_settings)
    try:
        # Verify the live connection before any test can touch the database.
        assert_test_database(engine, integration_settings.database_name)
        yield engine
    finally:
        engine.dispose()


def alembic_config(connection: Connection) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.attributes["connection"] = connection
    config.attributes["configure_logger"] = False
    return config
