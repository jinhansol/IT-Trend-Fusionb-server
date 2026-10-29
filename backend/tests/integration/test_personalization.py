"""P4: personalization switch, interests, self-rated skills and reset.

OFF keeps the data but the recommendation profile is empty; ON without data is an
empty profile; reset deletes interests and skills only and keeps the switch.
Invalid requests change nothing.
"""

import threading

import pytest
import yaml
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.session import create_session_factory
from app.main import create_app
from app.models.user import User
from app.schemas.personalization import InterestsUpdate
from app.services import personalization
from tests.collect_helpers import seed_catalog
from tests.e2e_seed import TECHNOLOGIES_FILE

pytestmark = pytest.mark.integration

PASSWORD = "correct horse 1"
REAL_TECHNOLOGIES = yaml.safe_load(TECHNOLOGIES_FILE.read_text(encoding="utf-8"))
ALL_SLUGS = [t["slug"] for t in REAL_TECHNOLOGIES["technologies"]]


@pytest.fixture()
def client(clean_db, integration_settings):
    seed_catalog(clean_db, technologies=REAL_TECHNOLOGIES)
    with TestClient(create_app(integration_settings)) as test_client:
        yield test_client


def login(client, email):
    response = client.post(
        "/api/auth/register", json={"email": email, "password": PASSWORD, "display_name": "U"}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def state(client, headers):
    return client.get("/api/me/personalization", headers=headers).json()


def interests(client, headers):
    return [i["slug"] for i in state(client, headers)["interests"]]


def skills(client, headers):
    return {s["slug"]: s["level"] for s in state(client, headers)["skills"]}


def switch(client, headers, enabled):
    response = client.patch(
        "/api/me/settings", json={"personalization_enabled": enabled}, headers=headers
    )
    assert response.status_code == 200, response.text
    return response.json()


def put_interests(client, headers, slugs):
    return client.put(
        "/api/me/personalization/interests", json={"technologies": slugs}, headers=headers
    )


def put_skills(client, headers, pairs):
    body = {"skills": [{"technology": t, "level": level} for t, level in pairs]}
    return client.put("/api/me/personalization/skills", json=body, headers=headers)


# --- access and switch ---------------------------------------------------------------------


def test_login_is_required(client):
    assert client.get("/api/me/personalization").status_code == 401
    assert (
        client.put("/api/me/personalization/interests", json={"technologies": []}).status_code
        == 401
    )
    assert client.put("/api/me/personalization/skills", json={"skills": []}).status_code == 401
    assert client.post("/api/me/personalization/reset").status_code == 401


def test_personalization_is_off_by_default_and_turned_on_only_explicitly(client):
    me = login(client, "a@example.com")
    assert client.get("/api/me", headers=me).json()["settings"]["personalization_enabled"] is False
    assert state(client, me)["enabled"] is False and state(client, me)["profile_status"] == "off"

    assert switch(client, me, True) == {"personalization_enabled": True, "learner_type": None}
    assert state(client, me)["profile_status"] == "empty"  # ON without data
    # Changing only the learner type leaves the switch alone, and vice versa.
    client.patch("/api/me/settings", json={"learner_type": "developer"}, headers=me)
    assert switch(client, me, False) == {
        "personalization_enabled": False,
        "learner_type": "developer",
    }
    for bad in (None, "yes", 1, "true"):
        response = client.patch(
            "/api/me/settings", json={"personalization_enabled": bad}, headers=me
        )
        assert response.status_code == 422, bad
    assert client.get("/api/me", headers=me).json()["settings"]["personalization_enabled"] is False


# --- interests -----------------------------------------------------------------------------


def test_interests_are_replaced_as_a_whole_and_idempotently(client):
    me = login(client, "a@example.com")
    first = put_interests(client, me, ["react", "python"])
    assert first.status_code == 200
    body = first.json()
    assert [i["slug"] for i in body["interests"]] == ["python", "react"]  # by name
    assert body["interests"][0] == {
        "slug": "python",
        "name": "Python",
        "kind": "language",
        "available": True,
    }
    assert body["limits"] == {"interests": 20, "skills": 30}
    assert put_interests(client, me, ["react", "python"]).json() == body
    assert put_interests(client, me, ["go"]).status_code == 200
    assert interests(client, me) == ["go"]
    assert put_interests(client, me, []).status_code == 200
    assert interests(client, me) == []


@pytest.mark.parametrize(
    ("slugs", "status", "code"),
    [
        (["python", "python"], 422, None),
        (ALL_SLUGS[:21], 422, None),
        (["python", "no-such-tech"], 422, "UNKNOWN_TECHNOLOGY"),
        (["Bad_Slug"], 422, None),
    ],
)
def test_invalid_interest_requests_change_nothing(client, slugs, status, code):
    me = login(client, "a@example.com")
    put_interests(client, me, ["java", "kotlin"])
    response = put_interests(client, me, slugs)
    assert response.status_code == status
    if code:
        assert response.json()["error"]["code"] == code
        assert response.json()["error"]["details"] == {"technologies": ["no-such-tech"]}
    assert interests(client, me) == ["java", "kotlin"]


def test_twenty_interests_are_allowed(client):
    me = login(client, "a@example.com")
    assert put_interests(client, me, ALL_SLUGS[:20]).status_code == 200
    assert len(interests(client, me)) == 20


# --- skills --------------------------------------------------------------------------------


def test_skills_are_self_ratings_replaced_as_a_whole(client):
    me = login(client, "a@example.com")
    response = put_skills(client, me, [("python", "used"), ("docker", "learning")])
    assert response.status_code == 200
    skill = response.json()["skills"][1]
    assert skill == {
        "slug": "python",
        "name": "Python",
        "kind": "language",
        "available": True,
        "level": "used",
    }
    assert put_skills(client, me, [("python", "confident")]).status_code == 200
    assert skills(client, me) == {"python": "confident"}
    # Skills and interests are independent.
    assert interests(client, me) == []


@pytest.mark.parametrize(
    "pairs",
    [
        [("python", "expert")],
        [("python", "used"), ("python", "learning")],
        [("no-such-tech", "used")],
        [(slug, "used") for slug in ALL_SLUGS[:31]],
    ],
)
def test_invalid_skill_requests_change_nothing(client, pairs):
    me = login(client, "a@example.com")
    put_skills(client, me, [("java", "used")])
    assert put_skills(client, me, pairs).status_code == 422
    assert skills(client, me) == {"java": "used"}


def test_thirty_skills_are_allowed(client):
    me = login(client, "a@example.com")
    assert put_skills(client, me, [(s, "learning") for s in ALL_SLUGS[:30]]).status_code == 200
    assert len(skills(client, me)) == 30


# --- retired technologies ------------------------------------------------------------------


def test_retired_technologies_are_kept_but_cannot_be_newly_selected(client, clean_db):
    me = login(client, "a@example.com")
    switch(client, me, True)
    put_interests(client, me, ["python", "rust"])
    put_skills(client, me, [("python", "used")])
    with clean_db.begin() as connection:
        connection.execute(
            text("UPDATE technologies SET status = 'retired' WHERE slug IN ('python', 'java')")
        )

    data = state(client, me)
    assert {i["slug"]: i["available"] for i in data["interests"]} == {"python": False, "rust": True}
    assert data["skills"][0]["available"] is False
    with create_session_factory(clean_db)() as db:
        user = db.query(User).filter_by(email="a@example.com").one()
        profile = personalization.profile_for_recommendation(db, user)
    assert profile.interests == ["rust"] and profile.skills == {}  # retired never used

    # Keeping a retired one is fine; selecting a retired one anew is not.
    assert put_interests(client, me, ["python", "rust", "go"]).status_code == 200
    refused = put_interests(client, me, ["python", "java"])
    assert refused.status_code == 422
    assert refused.json()["error"]["code"] == "RETIRED_TECHNOLOGY"
    assert refused.json()["error"]["details"] == {"technologies": ["java"]}
    assert interests(client, me) == ["go", "python", "rust"]
    assert put_skills(client, me, [("java", "used")]).status_code == 422
    # Leaving it out removes it.
    put_interests(client, me, ["rust"])
    assert interests(client, me) == ["rust"]


# --- OFF, ON and the recommendation profile ------------------------------------------------


def test_off_keeps_the_data_and_on_brings_back_the_same_profile(client, clean_db):
    me = login(client, "a@example.com")
    put_interests(client, me, ["python"])  # editable while OFF
    put_skills(client, me, [("docker", "learning")])
    off = state(client, me)
    assert off["profile_status"] == "off" and [i["slug"] for i in off["interests"]] == ["python"]

    def profile():
        with create_session_factory(clean_db)() as db:
            user = db.query(User).filter_by(email="a@example.com").one()
            return personalization.profile_for_recommendation(db, user)

    assert profile() == personalization.RecommendationProfile(enabled=False)
    switch(client, me, True)
    assert state(client, me)["profile_status"] == "ready"
    on = profile()
    assert on.interests == ["python"] and on.skills == {"docker": "learning"}

    switch(client, me, False)
    assert state(client, me)["interests"] == off["interests"]
    assert state(client, me)["skills"] == off["skills"]
    assert profile().is_empty
    switch(client, me, True)
    assert profile() == on


# --- reset ---------------------------------------------------------------------------------


def test_reset_deletes_interests_and_skills_only_and_keeps_the_switch(client, clean_db):
    me = login(client, "a@example.com")
    other = login(client, "b@example.com")
    for headers in (me, other):
        put_interests(client, headers, ["python"])
        put_skills(client, headers, [("python", "used")])
    switch(client, me, True)

    assert client.post("/api/me/personalization/reset", headers=me).status_code == 204
    after = state(client, me)
    assert after["enabled"] is True and after["profile_status"] == "empty"
    assert after["interests"] == [] and after["skills"] == []
    assert client.post("/api/me/personalization/reset", headers=me).status_code == 204  # idempotent
    assert interests(client, other) == ["python"] and skills(client, other) == {"python": "used"}

    # OFF stays OFF too.
    assert client.post("/api/me/personalization/reset", headers=other).status_code == 204
    assert state(client, other)["enabled"] is False


# --- isolation and concurrency -------------------------------------------------------------


def test_users_only_see_and_change_their_own_data(client):
    alice = login(client, "alice@example.com")
    bob = login(client, "bob@example.com")
    put_interests(client, alice, ["python"])
    put_interests(client, bob, ["java"])
    put_skills(client, bob, [("java", "confident")])
    switch(client, bob, True)
    assert interests(client, alice) == ["python"]
    assert skills(client, alice) == {}
    assert state(client, alice)["enabled"] is False
    put_interests(client, alice, [])
    assert interests(client, bob) == ["java"]


def test_concurrent_replacements_never_mix(client, clean_db):
    login(client, "race@example.com")
    session_factory = create_session_factory(clean_db)
    with session_factory() as db:
        user_id = db.query(User).filter_by(email="race@example.com").one().id
    sets = [ALL_SLUGS[i * 5 : i * 5 + 5] for i in range(6)]
    barrier = threading.Barrier(len(sets))
    errors = []

    def replace(slugs):
        with session_factory() as db:
            user = db.get(User, user_id)
            db.commit()  # end the read, as get_current_user does before a write use case
            barrier.wait()
            try:
                personalization.replace_interests(db, user, InterestsUpdate(technologies=slugs))
            except Exception as exc:  # pragma: no cover - reported below
                errors.append(exc)

    threads = [threading.Thread(target=replace, args=(s,)) for s in sets]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    with clean_db.connect() as connection:
        final = set(
            connection.execute(
                text(
                    "SELECT t.slug FROM user_interests i JOIN technologies t "
                    "ON t.id = i.technology_id WHERE i.user_id = :u"
                ),
                {"u": user_id},
            ).scalars()
        )
    assert final in [set(s) for s in sets]  # exactly one request's set, never a mix
