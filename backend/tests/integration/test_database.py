"""Checks against the real MariaDB test database (docker compose)."""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from app.db.safety import UnsafeDatabaseError, assert_test_database
from app.main import create_app

pytestmark = pytest.mark.integration

DEV_DATABASE_NAME = os.environ.get("DEV_DATABASE_NAME", "devhub_dev")
ER_DBACCESS_DENIED = 1044


def test_connected_database_is_the_configured_test_database(test_engine, integration_settings):
    with test_engine.connect() as connection:
        name = connection.execute(text("SELECT DATABASE()")).scalar_one()
    assert name == integration_settings.database_name
    assert name.endswith("_test")
    assert name != DEV_DATABASE_NAME


def test_guard_rejects_a_mismatched_expected_name(test_engine):
    with pytest.raises(UnsafeDatabaseError):
        assert_test_database(test_engine, DEV_DATABASE_NAME)


def test_test_account_cannot_open_dev_database(integration_settings):
    dev_url = integration_settings.parsed_database_url().set(database=DEV_DATABASE_NAME)
    engine = create_engine(dev_url)
    try:
        with pytest.raises(OperationalError) as excinfo:
            with engine.connect():
                pass
        assert excinfo.value.orig.args[0] == ER_DBACCESS_DENIED
    finally:
        engine.dispose()


def test_test_account_sees_only_its_own_database(test_engine, integration_settings):
    with test_engine.connect() as connection:
        visible = {row[0] for row in connection.execute(text("SHOW DATABASES"))}
    assert visible - {"information_schema"} == {integration_settings.database_name}


def test_session_defaults_are_utc_and_utf8mb4(test_engine):
    with test_engine.connect() as connection:
        time_zone = connection.execute(text("SELECT @@session.time_zone")).scalar_one()
        charset = connection.execute(text("SELECT @@character_set_connection")).scalar_one()
        collation = connection.execute(
            text(
                "SELECT DEFAULT_COLLATION_NAME FROM information_schema.SCHEMATA "
                "WHERE SCHEMA_NAME = DATABASE()"
            )
        ).scalar_one()
    assert time_zone == "+00:00"
    assert charset == "utf8mb4"
    assert collation == "utf8mb4_uca1400_ai_ci"


def test_readiness_endpoint_reaches_database(test_engine, integration_settings):
    with TestClient(create_app(integration_settings)) as client:
        response = client.get("/api/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
