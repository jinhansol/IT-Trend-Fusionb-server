"""P3-6: learning goals. Own data only, manual achievement, at most 5 active."""

import threading
import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.session import create_session_factory
from app.main import create_app
from app.models.user import User
from app.schemas.goals import GoalCreate
from app.services import learning_goals
from tests.career_helpers import seed_careers

pytestmark = pytest.mark.integration

PASSWORD = "correct horse 1"


@pytest.fixture()
def client(clean_db, integration_settings, tmp_path):
    seed_careers(clean_db, tmp_path)
    with TestClient(create_app(integration_settings)) as test_client:
        yield test_client


def login(client, email):
    response = client.post(
        "/api/auth/register", json={"email": email, "password": PASSWORD, "display_name": "U"}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create(client, headers, **body):
    return client.post("/api/me/goals", json={"title": "목표", **body}, headers=headers)


def units(goal):
    return [(u["track"]["slug"], u["slug"], u["state"]) for u in goal["units"]]


def test_login_is_required(client):
    assert client.get("/api/me/goals").status_code == 401
    assert client.post("/api/me/goals", json={"title": "x"}).status_code == 401
    assert client.patch("/api/me/goals/1", json={"title": "x"}).status_code == 401
    assert client.delete("/api/me/goals/1").status_code == 401


def test_goals_with_each_kind_of_target_link_to_published_units(client):
    me = login(client, "a@example.com")
    free = create(client, me, title="  매일 30분  ", target_date="2026-12-31")
    assert free.status_code == 201
    body = free.json()
    assert body["title"] == "매일 30분"
    assert body["status"] == "active" and body["achieved_at"] is None
    assert body["target"] is None and body["units"] == []
    assert body["target_date"] == "2026-12-31" and body["created_at"].endswith("Z")

    role = create(client, me, role="backend-dev").json()
    assert role["target"] == {
        "kind": "role",
        "slug": "backend-dev",
        "name": "Role backend-dev",
        "available": True,
    }
    # Core technologies (python, backend) -> published units, each once, in catalog order.
    assert units(role) == [
        ("py-test", "py-basics", "not_started"),
        ("py-test", "py-web", "not_started"),
    ]
    tech = create(client, me, technology="javascript").json()
    assert tech["target"]["kind"] == "technology" and units(tech) == [
        ("js-test", "js-basics", "not_started")
    ]
    track = create(client, me, track="py-test").json()
    assert track["target"] == {
        "kind": "track",
        "slug": "py-test",
        "name": "Track py-test",
        "available": True,
    }
    assert [u[1] for u in units(track)] == ["py-basics", "py-web"]  # draft unit hidden


def test_goal_units_show_the_users_own_progress(client, clean_db):
    me = login(client, "a@example.com")
    goal = create(client, me, track="py-test").json()
    with clean_db.begin() as connection:
        user_id = connection.execute(
            text("SELECT id FROM users WHERE email = 'a@example.com'")
        ).scalar_one()
        for slug, completed in (("py-basics", True), ("py-web", False)):
            connection.execute(
                text(
                    "INSERT INTO user_unit_progress (user_id, unit_id, started_at, "
                    "completed_at, last_activity_at) SELECT :u, id, UTC_TIMESTAMP(6), "
                    "IF(:c, UTC_TIMESTAMP(6), NULL), UTC_TIMESTAMP(6) "
                    "FROM learning_units WHERE slug = :s"
                ),
                {"u": user_id, "s": slug, "c": completed},
            )
    listed = client.get("/api/me/goals", headers=me).json()["items"]
    assert [g["id"] for g in listed] == [goal["id"]]
    assert units(listed[0]) == [
        ("py-test", "py-basics", "completed"),
        ("py-test", "py-web", "in_progress"),
    ]
    other = login(client, "b@example.com")
    goal_b = create(client, other, track="py-test").json()
    assert [u["state"] for u in goal_b["units"]] == ["not_started", "not_started"]


@pytest.mark.parametrize(
    ("body", "status", "code"),
    [
        ({"role": "backend-dev", "technology": "python"}, 422, None),
        ({"title": "   "}, 422, None),
        ({"title": "x" * 101}, 422, None),
        ({"role": "Bad_Slug"}, 422, None),
        ({"role": "nope"}, 404, "CAREER_ROLE_NOT_FOUND"),
        ({"technology": "nope"}, 404, "TECHNOLOGY_NOT_FOUND"),
        ({"track": "nope"}, 404, "TRACK_NOT_FOUND"),
        ({"unknown": 1}, 201, None),  # extra keys are ignored like other request bodies
    ],
)
def test_validation(client, body, status, code):
    me = login(client, "a@example.com")
    response = client.post("/api/me/goals", json={"title": "목표", **body}, headers=me)
    assert response.status_code == status
    if code:
        assert response.json()["error"]["code"] == code


def test_achieving_is_manual_and_achieved_at_follows_the_status(client, clean_db):
    me = login(client, "a@example.com")
    goal_id = create(client, me).json()["id"]

    def patch(**body):
        response = client.patch(f"/api/me/goals/{goal_id}", json=body, headers=me)
        assert response.status_code == 200, response.text
        return response.json()

    first = patch(status="achieved")
    assert first["status"] == "achieved" and first["achieved_at"] is not None
    assert patch(title="새 제목")["achieved_at"] == first["achieved_at"]  # unchanged
    assert patch(status="active")["achieved_at"] is None
    time.sleep(0.01)
    again = patch(status="achieved")
    assert again["achieved_at"] > first["achieved_at"]  # a new time, not the old one
    assert patch(status="archived")["achieved_at"] is None

    assert patch(target_date="2027-01-31")["target_date"] == "2027-01-31"
    assert patch(target_date=None)["target_date"] is None
    assert (
        client.patch(f"/api/me/goals/{goal_id}", json={"status": None}, headers=me).status_code
        == 422
    )
    assert (
        client.patch(f"/api/me/goals/{goal_id}", json={"title": None}, headers=me).status_code
        == 422
    )
    assert (
        client.patch(f"/api/me/goals/{goal_id}", json={"status": "done"}, headers=me).status_code
        == 422
    )

    with clean_db.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM xp_ledger")).scalar_one() == 0


def test_status_filter_and_order(client):
    me = login(client, "a@example.com")
    ids = [create(client, me, title=f"g{i}").json()["id"] for i in range(3)]
    client.patch(f"/api/me/goals/{ids[0]}", json={"status": "archived"}, headers=me)
    client.patch(f"/api/me/goals/{ids[1]}", json={"status": "achieved"}, headers=me)
    items = client.get("/api/me/goals", headers=me).json()["items"]
    assert [g["title"] for g in items] == ["g2", "g1", "g0"]  # active, achieved, archived
    active = client.get("/api/me/goals?status=active", headers=me).json()
    assert [g["title"] for g in active["items"]] == ["g2"] and active["active_limit"] == 5
    assert client.get("/api/me/goals?status=done", headers=me).status_code == 422


def test_at_most_five_active_goals(client):
    me = login(client, "a@example.com")
    ids = [create(client, me, title=f"g{i}").json()["id"] for i in range(5)]
    over = create(client, me, title="g5")
    assert over.status_code == 409 and over.json()["error"]["code"] == "GOAL_LIMIT"

    # Archived or achieved goals do not count; bringing one back does.
    client.patch(f"/api/me/goals/{ids[0]}", json={"status": "archived"}, headers=me)
    assert create(client, me, title="g5").status_code == 201
    back = client.patch(f"/api/me/goals/{ids[0]}", json={"status": "active"}, headers=me)
    assert back.status_code == 409
    # Editing an active goal is not a new active goal.
    assert (
        client.patch(f"/api/me/goals/{ids[1]}", json={"title": "edit"}, headers=me).status_code
        == 200
    )


def test_limit_holds_under_concurrent_creates(client, clean_db):
    login(client, "race@example.com")
    session_factory = create_session_factory(clean_db)
    with session_factory() as db:
        user = db.query(User).filter_by(email="race@example.com").one()
        db.expunge(user)
    attempts = 8
    barrier = threading.Barrier(attempts)
    outcomes = []

    def make(i):
        with session_factory() as db:
            barrier.wait()
            try:
                learning_goals.create_goal(db, user, GoalCreate(title=f"g{i}"))
                outcomes.append("created")
            except learning_goals.ActiveGoalLimitReached:
                outcomes.append("limit")

    threads = [threading.Thread(target=make, args=(i,)) for i in range(attempts)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(outcomes) == ["created"] * 5 + ["limit"] * 3
    with clean_db.connect() as connection:
        count = connection.execute(
            text("SELECT COUNT(*) FROM learning_goals WHERE user_id = :u AND status = 'active'"),
            {"u": user.id},
        ).scalar_one()
    assert count == 5


def test_users_cannot_see_or_change_each_others_goals(client):
    alice = login(client, "alice@example.com")
    bob = login(client, "bob@example.com")
    goal_id = create(client, alice, title="alice").json()["id"]

    assert client.get("/api/me/goals", headers=bob).json()["items"] == []
    for response in (
        client.patch(f"/api/me/goals/{goal_id}", json={"title": "bob"}, headers=bob),
        client.delete(f"/api/me/goals/{goal_id}", headers=bob),
    ):
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "GOAL_NOT_FOUND"
    assert (
        client.patch("/api/me/goals/999999", json={"title": "x"}, headers=alice).status_code == 404
    )
    assert client.patch("/api/me/goals/0", json={"title": "x"}, headers=alice).status_code == 422
    assert [g["title"] for g in client.get("/api/me/goals", headers=alice).json()["items"]] == [
        "alice"
    ]


def test_delete_is_separate_from_archive(client):
    me = login(client, "a@example.com")
    kept = create(client, me, title="kept").json()["id"]
    gone = create(client, me, title="gone").json()["id"]
    client.patch(f"/api/me/goals/{kept}", json={"status": "archived"}, headers=me)
    assert client.delete(f"/api/me/goals/{gone}", headers=me).status_code == 204
    assert client.delete(f"/api/me/goals/{gone}", headers=me).status_code == 404
    items = client.get("/api/me/goals", headers=me).json()["items"]
    assert [(g["title"], g["status"]) for g in items] == [("kept", "archived")]


def test_goals_keep_retired_targets_without_learning_links(client, clean_db):
    me = login(client, "a@example.com")
    create(client, me, role="backend-dev")
    create(client, me, technology="javascript")
    with clean_db.begin() as connection:
        connection.execute(
            text("UPDATE career_roles SET status = 'retired' WHERE slug = 'backend-dev'")
        )
        connection.execute(
            text("UPDATE technologies SET status = 'retired' WHERE slug = 'javascript'")
        )
    items = client.get("/api/me/goals", headers=me).json()["items"]
    assert [(g["target"]["slug"], g["target"]["available"], g["units"]) for g in items] == [
        ("backend-dev", False, []),
        ("javascript", False, []),
    ]
    assert create(client, me, role="backend-dev").status_code == 404  # not for new goals


def test_personalization_off_users_can_save_goals(client, clean_db):
    me = login(client, "off@example.com")
    with clean_db.connect() as connection:
        assert (
            connection.execute(
                text("SELECT personalization_enabled FROM user_settings")
            ).scalar_one()
            == 0
        )
    assert create(client, me, role="backend-dev").status_code == 201
    assert len(client.get("/api/me/goals", headers=me).json()["items"]) == 1
