"""P4 policies across features.

- Switching personalization, editing interests/skills and resetting never change
  goals, career candidates, learning progress, quiz results, XP or the learner type.
- Public content is byte-for-byte the same for guests, members with personalization
  OFF and members with it ON and saved interests/skills, for every learner type:
  P4 adds no recommendation or ranking.
"""

import pytest
import yaml
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.content_loader.careers import apply_careers, read_careers
from app.db.session import create_session_factory
from app.main import create_app
from tests.career_helpers import role, write_careers
from tests.collect_helpers import collect_all, seed_catalog
from tests.content_helpers import write_track
from tests.e2e_seed import TECHNOLOGIES_FILE
from tests.integration.test_learning_progress import (
    UNIT_ONE,
    UNIT_TWO,
    Learner,
    answers,
    load,
    unit_info,
)

pytestmark = pytest.mark.integration

REAL_TECHNOLOGIES = yaml.safe_load(TECHNOLOGIES_FILE.read_text(encoding="utf-8"))
KEPT_TABLES = (
    "user_activity_records",
    "user_unit_progress",
    "quiz_attempts",
    "quiz_attempt_answers",
    "xp_ledger",
    "learning_goals",
    "user_career_candidates",
)


@pytest.fixture()
def catalog(clean_db, tmp_path):
    seed_catalog(clean_db, technologies=REAL_TECHNOLOGIES)
    load(clean_db, write_track(tmp_path, slug="py", units=[UNIT_ONE, UNIT_TWO]))
    with create_session_factory(clean_db).begin() as db:
        apply_careers(db, read_careers(write_careers(tmp_path / "careers.yaml", [role("dev", 1)])))
    return clean_db


@pytest.fixture()
def client(catalog, integration_settings):
    with TestClient(create_app(integration_settings)) as test_client:
        yield test_client


def records(engine, learner_id):
    with engine.connect() as connection:
        rows = {
            t: connection.execute(text(f"SELECT * FROM {t} ORDER BY 1, 2")).all()
            for t in KEPT_TABLES
        }
        rows["learner_type"] = connection.execute(
            text("SELECT learner_type FROM user_settings WHERE user_id = :u"), {"u": learner_id}
        ).scalar_one()
    return rows


def test_personalization_never_touches_learning_goals_candidates_xp_or_type(client, catalog):
    learner = Learner(client, "keep@example.com")
    activities, quiz_id, questions = unit_info(client)
    for slug in ("read-a", "read-b"):
        assert learner.confirm(activities[slug]).status_code == 200
    assert learner.submit(quiz_id, answers(questions)).json()["passed"] is True
    h = learner.headers
    client.patch("/api/me/settings", json={"learner_type": "beginner"}, headers=h)
    assert (
        client.post("/api/me/goals", json={"title": "g", "role": "dev"}, headers=h).status_code
        == 201
    )
    assert client.put("/api/me/career-candidates/dev", json={}, headers=h).status_code == 200
    before = (records(catalog, learner.id), learner.summary(), learner.unit_progress())
    assert before[1]["xp"]["total"] == 100

    steps = [
        ("PATCH", "/api/me/settings", {"personalization_enabled": True}),
        ("PUT", "/api/me/personalization/interests", {"technologies": ["python", "docker"]}),
        (
            "PUT",
            "/api/me/personalization/skills",
            {"skills": [{"technology": "python", "level": "used"}]},
        ),
        ("PATCH", "/api/me/settings", {"personalization_enabled": False}),
        ("POST", "/api/me/personalization/reset", None),
        ("PATCH", "/api/me/settings", {"personalization_enabled": True}),
        ("POST", "/api/me/personalization/reset", None),
    ]
    for method, path, body in steps:
        response = client.request(method, path, json=body, headers=h)
        assert response.status_code < 300, (method, path, response.text)

    assert (records(catalog, learner.id), learner.summary(), learner.unit_progress()) == before


def test_public_content_is_the_same_for_guest_off_and_on(client, catalog):
    collect_all(catalog)
    urls = [
        "/api/news",
        "/api/news?tech=python",
        "/api/dev/channels",
        "/api/dev/channels/devto/posts?sort=popular",
        "/api/trends?scope=news",
        "/api/trends?scope=dev",
        "/api/tracks",
        "/api/tracks/py",
        "/api/tracks/py/units/one",
        "/api/tracks/py/units/one/quiz",
        "/api/technologies",
        "/api/technologies/python/units",
        "/api/careers/roles",
        "/api/careers/roles/dev",
    ]
    guest = [client.get(u).content for u in urls]
    member = Learner(client, "same@example.com").headers

    def as_member():
        return [client.get(u, headers=member).content for u in urls]

    assert as_member() == guest  # OFF, no data
    client.put(
        "/api/me/personalization/interests",
        json={"technologies": ["python", "react", "security"]},
        headers=member,
    )
    client.put(
        "/api/me/personalization/skills",
        json={"skills": [{"technology": "java", "level": "confident"}]},
        headers=member,
    )
    for enabled in (False, True):
        client.patch("/api/me/settings", json={"personalization_enabled": enabled}, headers=member)
        for learner_type in (None, "beginner", "developer", "exploring"):
            client.patch("/api/me/settings", json={"learner_type": learner_type}, headers=member)
            assert as_member() == guest, (enabled, learner_type)


def test_technology_list_is_public_and_grouped_by_kind(client):
    items = client.get("/api/technologies").json()["items"]
    assert len(items) == len(REAL_TECHNOLOGIES["technologies"]) == 57
    kinds = [i["kind"] for i in items]
    assert kinds == sorted(kinds)
    assert {"slug": "python", "name": "Python", "kind": "language"} in items
