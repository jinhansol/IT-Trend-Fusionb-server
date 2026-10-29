"""P3 policies across features, with a learner who has real progress and XP.

- Saving or removing career candidates never changes goals, settings, progress or XP.
- Goal changes (create, edit, achieve, un-achieve, archive, delete) never change
  candidates, settings, progress or XP; achieving grants nothing.
- Reloading the career roles file never changes users' candidates or goals.
- Nothing in P3 turns personalization on.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.content_loader.careers import apply_careers, read_careers
from app.db.session import create_session_factory
from app.main import create_app
from tests.career_helpers import role, write_careers
from tests.collect_helpers import seed_catalog
from tests.content_helpers import write_track
from tests.integration.test_learning_progress import (
    UNIT_ONE,
    UNIT_TWO,
    Learner,
    answers,
    load,
    unit_info,
)

pytestmark = pytest.mark.integration

LEARNING_TABLES = (
    "user_activity_records",
    "user_unit_progress",
    "quiz_attempts",
    "quiz_attempt_answers",
    "xp_ledger",
)


def table(engine, name):
    with engine.connect() as connection:
        return connection.execute(text(f"SELECT * FROM {name} ORDER BY 1, 2")).all()


def snapshot(engine, learner, *names):
    return (
        {name: table(engine, name) for name in names},
        learner.summary(),
        learner.unit_progress(),
    )


@pytest.fixture()
def learner(clean_db, integration_settings, tmp_path):
    seed_catalog(clean_db)
    load(clean_db, write_track(tmp_path, slug="py", units=[UNIT_ONE, UNIT_TWO]))
    careers = write_careers(tmp_path / "careers.yaml", [role("backend-dev", 1), role("other", 2)])
    with create_session_factory(clean_db).begin() as db:
        apply_careers(db, read_careers(careers))
    with TestClient(create_app(integration_settings)) as client:
        user = Learner(client, "learner@example.com")
        activities, quiz_id, questions = unit_info(client)
        for slug in ("read-a", "read-b"):
            assert user.confirm(activities[slug]).status_code == 200
        assert user.submit(quiz_id, answers(questions)).json()["passed"] is True
        assert user.summary()["xp"]["total"] == 100  # a completed unit
        user.careers_file = careers
        yield user


def call(learner, method, path, json=None):
    response = learner.client.request(method, path, json=json, headers=learner.headers)
    assert response.status_code < 300, (method, path, response.text)
    return response


def test_candidates_never_change_goals_settings_progress_or_xp(learner, clean_db):
    call(learner, "POST", "/api/me/goals", {"title": "kept", "role": "backend-dev"})
    watched = (*LEARNING_TABLES, "user_settings", "learning_goals")
    before = snapshot(clean_db, learner, *watched)

    call(learner, "PUT", "/api/me/career-candidates/backend-dev", {"note": "a"})
    call(learner, "PUT", "/api/me/career-candidates/backend-dev", {"note": "b"})
    call(learner, "PUT", "/api/me/career-candidates/other", {})
    call(learner, "DELETE", "/api/me/career-candidates/other")

    assert snapshot(clean_db, learner, *watched) == before
    assert len(table(clean_db, "user_career_candidates")) == 1


def test_goal_changes_never_change_candidates_settings_progress_or_xp(learner, clean_db):
    call(learner, "PUT", "/api/me/career-candidates/backend-dev", {"note": "kept"})
    watched = (*LEARNING_TABLES, "user_settings", "user_career_candidates")
    before = snapshot(clean_db, learner, *watched)

    role_goal = call(learner, "POST", "/api/me/goals", {"title": "r", "role": "backend-dev"})
    track_goal = call(learner, "POST", "/api/me/goals", {"title": "t", "track": "py"}).json()
    free_goal = call(learner, "POST", "/api/me/goals", {"title": "f"}).json()
    # The linked unit shows the learner's real completion (read-only).
    assert [u["state"] for u in track_goal["units"]] == ["completed", "not_started"]
    goal_id = role_goal.json()["id"]
    for status in ("achieved", "active", "achieved", "archived"):
        call(learner, "PATCH", f"/api/me/goals/{goal_id}", {"status": status})
    call(learner, "PATCH", f"/api/me/goals/{free_goal['id']}", {"title": "f2", "target_date": None})
    call(learner, "DELETE", f"/api/me/goals/{free_goal['id']}")

    assert snapshot(clean_db, learner, *watched) == before


def test_reloading_roles_keeps_users_candidates_and_goals(learner, clean_db):
    call(learner, "PUT", "/api/me/career-candidates/other", {"note": "n"})
    call(learner, "POST", "/api/me/goals", {"title": "g", "role": "other"})
    watched = ("user_career_candidates", "learning_goals", *LEARNING_TABLES, "user_settings")
    before = snapshot(clean_db, learner, *watched)

    # "other" disappears from the file: it is retired, never deleted.
    with create_session_factory(clean_db).begin() as db:
        apply_careers(
            db, read_careers(write_careers(learner.careers_file, [role("backend-dev", 1)]))
        )
    assert snapshot(clean_db, learner, *watched) == before
    goal = learner.get("/api/me/goals").json()["items"][0]
    assert goal["target"]["available"] is False


def test_nothing_in_p3_turns_personalization_on(learner, clean_db):
    call(learner, "GET", "/api/careers/roles")
    call(learner, "GET", "/api/careers/roles/backend-dev")
    call(learner, "PUT", "/api/me/career-candidates/backend-dev", {})
    goal_id = call(learner, "POST", "/api/me/goals", {"title": "g", "role": "backend-dev"}).json()[
        "id"
    ]
    call(learner, "PATCH", f"/api/me/goals/{goal_id}", {"status": "achieved"})
    me = learner.get("/api/me").json()
    assert me["settings"] == {"personalization_enabled": False, "learner_type": None}
