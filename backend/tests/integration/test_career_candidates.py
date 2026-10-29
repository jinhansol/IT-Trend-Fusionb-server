"""P3-5: saved career candidates. Own data only, idempotent, limited to 10."""

import threading

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.session import create_session_factory
from app.main import create_app
from app.models.user import User
from app.services import career_candidates
from tests.career_helpers import TEST_ROLES, role, seed_careers

pytestmark = pytest.mark.integration

PASSWORD = "correct horse 1"
MANY_ROLES = [*TEST_ROLES, *(role(f"extra-{i}", 10 + i) for i in range(12))]


@pytest.fixture()
def client(clean_db, integration_settings, tmp_path):
    seed_careers(clean_db, tmp_path, roles=MANY_ROLES)
    with TestClient(create_app(integration_settings)) as test_client:
        yield test_client


def login(client, email):
    response = client.post(
        "/api/auth/register", json={"email": email, "password": PASSWORD, "display_name": "U"}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def saved(client, headers):
    return [
        (i["role"]["slug"], i["note"])
        for i in client.get("/api/me/career-candidates", headers=headers).json()["items"]
    ]


def test_login_is_required(client):
    assert client.get("/api/me/career-candidates").status_code == 401
    assert client.put("/api/me/career-candidates/backend-dev", json={}).status_code == 401
    assert client.delete("/api/me/career-candidates/backend-dev").status_code == 401


def test_save_is_idempotent_and_updates_the_note(client):
    me = login(client, "a@example.com")
    first = client.put("/api/me/career-candidates/backend-dev", json={"note": " 관심 "}, headers=me)
    assert first.status_code == 200
    body = first.json()
    assert body["role"] == {"slug": "backend-dev", "name": "Role backend-dev", "available": True}
    assert body["note"] == "관심" and body["saved_at"].endswith("Z")

    client.put("/api/me/career-candidates/backend-dev", json={"note": "  "}, headers=me)
    client.put("/api/me/career-candidates/frontend-dev", json={}, headers=me)
    assert saved(client, me) == [("backend-dev", None), ("frontend-dev", None)]
    listing = client.get("/api/me/career-candidates", headers=me).json()
    assert listing["limit"] == 10

    assert client.delete("/api/me/career-candidates/backend-dev", headers=me).status_code == 204
    assert client.delete("/api/me/career-candidates/backend-dev", headers=me).status_code == 204
    assert saved(client, me) == [("frontend-dev", None)]


def test_validation_and_unknown_roles(client):
    me = login(client, "a@example.com")
    assert client.put("/api/me/career-candidates/nope", json={}, headers=me).status_code == 404
    assert client.delete("/api/me/career-candidates/nope", headers=me).status_code == 404
    assert client.put("/api/me/career-candidates/Bad_Slug", json={}, headers=me).status_code == 422
    long_note = client.put(
        "/api/me/career-candidates/backend-dev", json={"note": "x" * 201}, headers=me
    )
    assert long_note.status_code == 422


def test_retired_roles_are_kept_but_cannot_be_newly_saved(client, clean_db):
    me = login(client, "a@example.com")
    client.put("/api/me/career-candidates/backend-dev", json={}, headers=me)
    with clean_db.begin() as connection:
        connection.execute(
            text(
                "UPDATE career_roles SET status = 'retired' "
                "WHERE slug IN ('backend-dev', 'no-units')"
            )
        )
    items = client.get("/api/me/career-candidates", headers=me).json()["items"]
    assert items[0]["role"] == {
        "slug": "backend-dev",
        "name": "Role backend-dev",
        "available": False,
    }
    assert client.put("/api/me/career-candidates/no-units", json={}, headers=me).status_code == 404
    # Updating the note of an existing save of a retired role is also refused...
    assert (
        client.put("/api/me/career-candidates/backend-dev", json={}, headers=me).status_code == 404
    )
    # ...but it can still be removed.
    assert client.delete("/api/me/career-candidates/backend-dev", headers=me).status_code == 204
    assert saved(client, me) == []


def test_limit_of_ten(client):
    me = login(client, "a@example.com")
    slugs = [r["slug"] for r in MANY_ROLES]
    for slug in slugs[:10]:
        assert (
            client.put(f"/api/me/career-candidates/{slug}", json={}, headers=me).status_code == 200
        )
    over = client.put(f"/api/me/career-candidates/{slugs[10]}", json={}, headers=me)
    assert over.status_code == 409 and over.json()["error"]["code"] == "CANDIDATE_LIMIT"
    # Re-saving an existing one (note change) is not a new candidate.
    assert (
        client.put(
            f"/api/me/career-candidates/{slugs[0]}", json={"note": "n"}, headers=me
        ).status_code
        == 200
    )
    assert len(saved(client, me)) == 10


def test_limit_holds_under_concurrent_saves(client, clean_db):
    login(client, "race@example.com")
    session_factory = create_session_factory(clean_db)
    with session_factory() as db:
        user = db.query(User).filter_by(email="race@example.com").one()
        db.expunge(user)
    slugs = [r["slug"] for r in MANY_ROLES][:14]
    barrier = threading.Barrier(len(slugs))
    outcomes = []

    def save(slug):
        with session_factory() as db:
            barrier.wait()
            try:
                career_candidates.save_candidate(db, user, slug, None)
                outcomes.append("saved")
            except career_candidates.CandidateLimitReached:
                outcomes.append("limit")

    threads = [threading.Thread(target=save, args=(slug,)) for slug in slugs]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(outcomes) == ["limit"] * 4 + ["saved"] * 10
    with clean_db.connect() as connection:
        count = connection.execute(
            text("SELECT COUNT(*) FROM user_career_candidates WHERE user_id = :u"), {"u": user.id}
        ).scalar_one()
    assert count == 10


def test_users_only_see_and_change_their_own_candidates(client):
    alice = login(client, "alice@example.com")
    bob = login(client, "bob@example.com")
    client.put("/api/me/career-candidates/backend-dev", json={"note": "alice"}, headers=alice)
    client.put("/api/me/career-candidates/backend-dev", json={"note": "bob"}, headers=bob)

    assert saved(client, alice) == [("backend-dev", "alice")]
    client.delete("/api/me/career-candidates/backend-dev", headers=alice)
    assert saved(client, alice) == []
    assert saved(client, bob) == [("backend-dev", "bob")]
