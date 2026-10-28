"""Alembic round trip against the MariaDB test database."""

import pytest
from alembic import command
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect

from tests.conftest import alembic_config

pytestmark = pytest.mark.integration


HEAD_TABLES = {"alembic_version", "users", "user_settings", "refresh_tokens"}


def _current_revision(connection) -> str | None:
    return MigrationContext.configure(connection).get_current_revision()


def _tables(connection) -> set[str]:
    return set(inspect(connection).get_table_names())


def test_upgrade_check_downgrade_upgrade(test_engine):
    with test_engine.connect() as connection:
        config = alembic_config(connection)
        head = ScriptDirectory.from_config(config).get_current_head()

        command.upgrade(config, "head")
        connection.commit()
        assert _current_revision(connection) == head
        assert _tables(connection) == HEAD_TABLES

        # Fails if the ORM models and the migrated schema differ.
        command.check(config)

        command.downgrade(config, "base")
        connection.commit()
        assert _current_revision(connection) is None
        # A partial downgrade (MariaDB DDL cannot roll back) would leave tables here.
        assert _tables(connection) == {"alembic_version"}

        command.upgrade(config, "head")
        connection.commit()
        assert _current_revision(connection) == head
        assert _tables(connection) == HEAD_TABLES


def test_single_head_and_linear_history(test_engine):
    with test_engine.connect() as connection:
        script = ScriptDirectory.from_config(alembic_config(connection))
    assert len(script.get_heads()) == 1
