"""Alembic round trip against the MariaDB test database."""

import pytest
from alembic import command
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text

from tests.conftest import alembic_config

pytestmark = pytest.mark.integration


HEAD_TABLES = {
    "alembic_version",
    "user_interests",
    "user_skills",
    "career_roles",
    "career_role_technologies",
    "user_career_candidates",
    "learning_goals",
    "users",
    "user_settings",
    "refresh_tokens",
    "learning_tracks",
    "learning_units",
    "learning_activities",
    "quizzes",
    "quiz_questions",
    "quiz_choices",
    "quiz_attempts",
    "quiz_attempt_answers",
    "user_activity_records",
    "user_unit_progress",
    "xp_ledger",
    "technologies",
    "technology_aliases",
    "content_sources",
    "contents",
    "content_technologies",
    "content_translations",
    "content_summaries",
    "job_runs",
    "learning_unit_technologies",
}


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


def test_learner_type_migration_keeps_existing_users(test_engine, clean_db):
    """0006 adds user_settings.learner_type; users created before it keep their rows
    and get NULL ("not chosen")."""
    with test_engine.connect() as connection:
        config = alembic_config(connection)
        command.upgrade(config, "head")
        command.downgrade(config, "0005")
        connection.commit()
        assert "learner_type" not in {
            c["name"] for c in inspect(connection).get_columns("user_settings")
        }
        connection.execute(
            text(
                "INSERT INTO users (email, password_hash, display_name, role, status, "
                "created_at, updated_at) VALUES ('old@example.com', 'x', 'Old', 'user', "
                "'active', UTC_TIMESTAMP(6), UTC_TIMESTAMP(6))"
            )
        )
        user_id = connection.execute(text("SELECT LAST_INSERT_ID()")).scalar_one()
        connection.execute(
            text(
                "INSERT INTO user_settings (user_id, personalization_enabled, updated_at) "
                "VALUES (:u, 1, UTC_TIMESTAMP(6))"
            ),
            {"u": user_id},
        )
        connection.commit()

        command.upgrade(config, "head")
        connection.commit()
        row = connection.execute(
            text(
                "SELECT u.email, u.role, s.personalization_enabled, s.learner_type "
                "FROM users u JOIN user_settings s ON s.user_id = u.id WHERE u.id = :u"
            ),
            {"u": user_id},
        ).one()
    assert tuple(row) == ("old@example.com", "user", 1, None)


def test_career_migration_keeps_existing_records(test_engine, clean_db):
    """0008 only adds tables: users, settings, learning progress and XP written before
    it are unchanged by the upgrade and by a downgrade back to 0007."""
    snapshot_sql = (
        "SELECT u.email, s.personalization_enabled, s.learner_type, x.amount, x.reason "
        "FROM users u JOIN user_settings s ON s.user_id = u.id "
        "JOIN xp_ledger x ON x.user_id = u.id WHERE u.id = :u"
    )
    with test_engine.connect() as connection:
        config = alembic_config(connection)
        command.upgrade(config, "head")
        command.downgrade(config, "0007")
        connection.commit()
        connection.execute(
            text(
                "INSERT INTO users (email, password_hash, display_name, role, status, "
                "created_at, updated_at) VALUES ('kept@example.com', 'x', 'Kept', 'user', "
                "'active', UTC_TIMESTAMP(6), UTC_TIMESTAMP(6))"
            )
        )
        user_id = connection.execute(text("SELECT LAST_INSERT_ID()")).scalar_one()
        connection.execute(
            text(
                "INSERT INTO user_settings (user_id, personalization_enabled, learner_type, "
                "updated_at) VALUES (:u, 0, 'beginner', UTC_TIMESTAMP(6))"
            ),
            {"u": user_id},
        )
        connection.execute(
            text(
                "INSERT INTO xp_ledger (user_id, amount, reason, source_type, source_id, "
                "idempotency_key, policy_version, created_at) VALUES (:u, 100, "
                "'unit_completed', 'unit', 1, 'unit:1', 'v1', UTC_TIMESTAMP(6))"
            ),
            {"u": user_id},
        )
        connection.commit()
        before = tuple(connection.execute(text(snapshot_sql), {"u": user_id}).one())

        command.upgrade(config, "head")
        connection.commit()
        assert tuple(connection.execute(text(snapshot_sql), {"u": user_id}).one()) == before

        command.downgrade(config, "0007")
        connection.commit()
        assert tuple(connection.execute(text(snapshot_sql), {"u": user_id}).one()) == before
        command.upgrade(config, "head")
        connection.commit()
    assert before == ("kept@example.com", 0, "beginner", 100, "unit_completed")


def test_personalization_migration_keeps_goals_candidates_and_settings(test_engine, clean_db):
    """0009 only adds tables: P3 goals and candidates and the settings written before
    it survive the upgrade and a downgrade back to 0008."""
    snapshot_sql = (
        "SELECT u.email, s.personalization_enabled, s.learner_type, g.title, g.status, r.slug "
        "FROM users u JOIN user_settings s ON s.user_id = u.id "
        "JOIN learning_goals g ON g.user_id = u.id "
        "JOIN user_career_candidates c ON c.user_id = u.id "
        "JOIN career_roles r ON r.id = c.role_id WHERE u.id = :u"
    )
    with test_engine.connect() as connection:
        config = alembic_config(connection)
        command.upgrade(config, "head")
        command.downgrade(config, "0008")
        connection.commit()
        connection.execute(
            text(
                "INSERT INTO users (email, password_hash, display_name, role, status, "
                "created_at, updated_at) VALUES ('p3@example.com', 'x', 'P3', 'user', "
                "'active', UTC_TIMESTAMP(6), UTC_TIMESTAMP(6))"
            )
        )
        user_id = connection.execute(text("SELECT LAST_INSERT_ID()")).scalar_one()
        connection.execute(
            text(
                "INSERT INTO user_settings (user_id, personalization_enabled, learner_type, "
                "updated_at) VALUES (:u, 1, 'developer', UTC_TIMESTAMP(6))"
            ),
            {"u": user_id},
        )
        connection.execute(
            text(
                "INSERT INTO career_roles (slug, name, summary, description_md, tasks, "
                "reference_links, position, status, created_at, updated_at) VALUES ('r', 'R', "
                "'s', 'd', '[]', '[]', 1, 'published', UTC_TIMESTAMP(6), UTC_TIMESTAMP(6))"
            )
        )
        role_id = connection.execute(text("SELECT LAST_INSERT_ID()")).scalar_one()
        connection.execute(
            text(
                "INSERT INTO user_career_candidates (user_id, role_id, created_at, updated_at) "
                "VALUES (:u, :r, UTC_TIMESTAMP(6), UTC_TIMESTAMP(6))"
            ),
            {"u": user_id, "r": role_id},
        )
        connection.execute(
            text(
                "INSERT INTO learning_goals (user_id, title, role_id, status, created_at, "
                "updated_at) VALUES (:u, 'goal', :r, 'active', UTC_TIMESTAMP(6), "
                "UTC_TIMESTAMP(6))"
            ),
            {"u": user_id, "r": role_id},
        )
        connection.commit()
        before = tuple(connection.execute(text(snapshot_sql), {"u": user_id}).one())

        command.upgrade(config, "head")
        connection.commit()
        assert tuple(connection.execute(text(snapshot_sql), {"u": user_id}).one()) == before
        command.downgrade(config, "0008")
        connection.commit()
        assert tuple(connection.execute(text(snapshot_sql), {"u": user_id}).one()) == before
        command.upgrade(config, "head")
        connection.commit()
    assert before == ("p3@example.com", 1, "developer", "goal", "active", "r")
