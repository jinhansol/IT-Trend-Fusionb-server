"""Content loader against the real MariaDB test database."""

import pytest
from sqlalchemy import text

from app.content_loader import __main__ as cli
from app.content_loader.loader import apply_track
from app.content_loader.schema import read_track_directory
from app.db.session import create_session_factory
from tests.content_helpers import activity, question, quiz, unit, write_track

pytestmark = pytest.mark.integration


@pytest.fixture()
def load(clean_db):
    session_factory = create_session_factory(clean_db)

    def run(directory):
        session = session_factory()
        try:
            report = apply_track(session, read_track_directory(directory))
            session.commit()
            return report
        finally:
            session.close()

    return run


def rows(engine, sql, **params):
    with engine.connect() as connection:
        return [tuple(r) for r in connection.execute(text(sql), params)]


UNITS_SQL = (
    "SELECT u.slug, u.position, u.status FROM learning_units u "
    "JOIN learning_tracks t ON t.id = u.track_id WHERE t.slug = :t ORDER BY u.slug"
)


def test_first_load_creates_everything(tmp_path, load, clean_db):
    directory = write_track(
        tmp_path,
        units=[unit("one", 1, activities=[activity("a"), activity("b")]), unit("two", 2)],
    )
    report = load(directory)

    assert "track sample" in report.created
    assert {"unit one", "unit two", "activity one/a", "activity one/b"} <= set(report.created)
    assert rows(clean_db, UNITS_SQL, t="sample") == [
        ("one", 1, "published"),
        ("two", 2, "published"),
    ]
    assert rows(
        clean_db,
        "SELECT a.slug, a.position FROM learning_activities a JOIN learning_units u "
        "ON u.id = a.unit_id WHERE u.slug = 'one' ORDER BY a.position",
    ) == [("a", 1), ("b", 2)]


def test_loading_the_same_files_twice_changes_nothing(tmp_path, load, clean_db):
    directory = write_track(tmp_path, units=[unit("one", 1), unit("two", 2)])
    load(directory)
    before = rows(clean_db, "SELECT id, slug, position, title, updated_at FROM learning_units")

    report = load(directory)

    assert not report.changed, report.summary()
    assert (
        rows(clean_db, "SELECT id, slug, position, title, updated_at FROM learning_units") == before
    )


def test_only_changed_rows_are_reported(tmp_path, load, clean_db):
    load(write_track(tmp_path, units=[unit("one", 1), unit("two", 2)]))
    report = load(write_track(tmp_path, units=[unit("one", 1, title="Renamed"), unit("two", 2)]))
    assert report.updated == ["unit one"]
    assert report.created == [] and report.retired == []


def test_units_can_swap_positions(tmp_path, load, clean_db):
    load(write_track(tmp_path, units=[unit("one", 1), unit("two", 2)]))
    load(write_track(tmp_path, units=[unit("one", 2), unit("two", 1)]))
    assert rows(clean_db, UNITS_SQL, t="sample") == [
        ("one", 2, "published"),
        ("two", 1, "published"),
    ]


def test_removed_units_and_activities_are_retired_not_deleted(tmp_path, load, clean_db):
    load(
        write_track(
            tmp_path,
            units=[unit("one", 1, activities=[activity("a"), activity("b")]), unit("two", 2)],
        )
    )
    report = load(write_track(tmp_path, units=[unit("one", 1, activities=[activity("a")])]))

    assert set(report.retired) == {"unit two", "activity one/b"}
    assert rows(clean_db, UNITS_SQL, t="sample") == [
        ("one", 1, "published"),
        ("two", None, "retired"),
    ]
    assert rows(clean_db, "SELECT position, status FROM learning_activities WHERE slug = 'b'") == [
        (None, "retired")
    ]

    # The freed position can be reused, and a retired unit can come back.
    load(write_track(tmp_path, units=[unit("one", 1), unit("three", 2), unit("two", 3)]))
    assert rows(clean_db, UNITS_SQL, t="sample") == [
        ("one", 1, "published"),
        ("three", 2, "published"),
        ("two", 3, "published"),
    ]


def test_tracks_are_independent(tmp_path, load, clean_db):
    load(write_track(tmp_path, slug="alpha", units=[unit("intro", 1)], position=1))
    load(write_track(tmp_path, slug="beta", units=[unit("intro", 1), unit("more", 2)], position=2))
    load(write_track(tmp_path, slug="alpha", units=[], position=1))  # alpha's units retired

    assert rows(clean_db, UNITS_SQL, t="alpha") == [("intro", None, "retired")]
    assert rows(clean_db, UNITS_SQL, t="beta") == [
        ("intro", 1, "published"),
        ("more", 2, "published"),
    ]


def test_cli_dry_run_saves_nothing_and_errors_write_nothing(
    tmp_path, clean_db, integration_settings, monkeypatch, capsys
):
    monkeypatch.setattr(cli, "get_settings", lambda: integration_settings)
    directory = write_track(tmp_path, units=[unit("one", 1)])

    assert cli.main(["load", str(directory), "--dry-run"]) == 0
    assert "dry run" in capsys.readouterr().out
    assert rows(clean_db, "SELECT COUNT(*) FROM learning_tracks") == [(0,)]

    broken = write_track(tmp_path, slug="broken", units=[unit("x", 1), unit("y", 1)])
    assert cli.main(["load", str(directory), str(broken)]) == 1
    assert "duplicate unit position" in capsys.readouterr().err
    assert rows(clean_db, "SELECT COUNT(*) FROM learning_tracks") == [(0,)]

    assert cli.main(["load", str(directory)]) == 0
    assert rows(clean_db, "SELECT slug FROM learning_tracks") == [("sample",)]


QUIZ_SQL = (
    "SELECT q.version, q.status, COUNT(qq.id) FROM quizzes q "
    "LEFT JOIN quiz_questions qq ON qq.quiz_id = q.id GROUP BY q.id ORDER BY q.version"
)


def _attempt_current_quiz(engine):
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO users (email, password_hash, display_name, created_at, updated_at) "
                "VALUES ('q@example.com', 'x', 'Q', NOW(6), NOW(6))"
            )
        )
        connection.execute(
            text(
                "INSERT INTO quiz_attempts (user_id, quiz_id, client_submission_id, score, "
                "max_score, score_percent, passed, submitted_at) SELECT u.id, q.id, "
                "'00000000-0000-0000-0000-000000000001', 0, 2, 0, 0, NOW(6) "
                "FROM users u, quizzes q WHERE q.status = 'published'"
            )
        )


def test_quiz_lifecycle_versions_only_after_attempts(tmp_path, load, clean_db):
    original = quiz([question("q1"), question("q2")])
    report = load(write_track(tmp_path, units=[unit("one", 1, quiz=original)]))
    assert "quiz one v1" in report.created
    assert rows(clean_db, QUIZ_SQL) == [(1, "published", 2)]

    assert not load(write_track(tmp_path, units=[unit("one", 1, quiz=original)])).changed

    # Not attempted yet: edited in place, still version 1.
    edited = quiz([question("q1"), question("q2"), question("q3")])
    report = load(write_track(tmp_path, units=[unit("one", 1, quiz=edited)]))
    assert report.updated == ["quiz one v1"]
    assert rows(clean_db, QUIZ_SQL) == [(1, "published", 3)]

    # Attempted: the old version is kept for history and a new one is published.
    _attempt_current_quiz(clean_db)
    report = load(write_track(tmp_path, units=[unit("one", 1, quiz=quiz([question("q1")]))]))
    assert report.retired == ["quiz one v1"] and report.created == ["quiz one v2"]
    assert rows(clean_db, QUIZ_SQL) == [(1, "retired", 3), (2, "published", 1)]

    # Removing the quiz from the file retires it.
    report = load(write_track(tmp_path, units=[unit("one", 1)]))
    assert report.retired == ["quiz one v2"]
    assert rows(clean_db, "SELECT COUNT(*) FROM quizzes WHERE status = 'published'") == [(0,)]


def test_quiz_answers_are_stored_per_choice(tmp_path, load, clean_db):
    load(
        write_track(
            tmp_path,
            units=[
                unit("one", 1, quiz=quiz([question("q1", type="multiple", correct=("a", "c"))]))
            ],
        )
    )
    assert rows(
        clean_db, "SELECT `key`, position, is_correct FROM quiz_choices ORDER BY position"
    ) == [("a", 1, 1), ("b", 2, 0), ("c", 3, 1)]
