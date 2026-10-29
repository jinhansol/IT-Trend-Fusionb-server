"""P1 (A-plan v0.2): optional learner_type, own-settings API, sign-up rate limit.

learner_type is for static guidance only: changing it must not change any public
content response, ranking or learning record.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import create_app
from tests.collect_helpers import collect_all, seed_catalog
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

PASSWORD = "correct horse 1"


@pytest.fixture()
def make_client(clean_db, integration_settings):
    clients = []

    def factory(**overrides):
        settings = integration_settings.model_copy(update=overrides)
        client = TestClient(create_app(settings), raise_server_exceptions=False)
        clients.append(client)
        return client

    yield factory
    for client in clients:
        client.close()


def register(client, email, **extra):
    body = {"email": email, "password": PASSWORD, "display_name": "Tester", **extra}
    return client.post("/api/auth/register", json=body)


def bearer(response):
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def stored_type(engine, email):
    with engine.connect() as connection:
        return connection.execute(
            text(
                "SELECT s.learner_type FROM user_settings s JOIN users u ON u.id = s.user_id "
                "WHERE u.email = :e"
            ),
            {"e": email},
        ).scalar_one()


# --- 1-3. registration, choice, change, invalid values -----------------------------------


def test_old_registration_body_still_works_and_leaves_type_unset(make_client, clean_db):
    client = make_client()
    response = register(client, "legacy@example.com")  # no learner_type, as before P1

    assert response.status_code == 201
    assert response.json()["user"]["role"] == "user"  # authorization role untouched
    me = client.get("/api/me", headers=bearer(response)).json()
    assert me["settings"] == {"personalization_enabled": False, "learner_type": None}
    assert stored_type(clean_db, "legacy@example.com") is None


@pytest.mark.parametrize("learner_type", ["beginner", "developer", "exploring"])
def test_registration_stores_the_chosen_type(make_client, clean_db, learner_type):
    client = make_client()
    response = register(client, f"{learner_type}@example.com", learner_type=learner_type)

    assert response.status_code == 201
    me = client.get("/api/me", headers=bearer(response)).json()
    assert me["settings"]["learner_type"] == learner_type
    assert me["role"] == "user"


@pytest.mark.parametrize("value", ["admin", "user", "Beginner", "", 3, ["beginner"]])
def test_invalid_type_is_rejected_on_registration(make_client, clean_db, value):
    response = register(make_client(), "bad@example.com", learner_type=value)
    assert response.status_code == 422
    with clean_db.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM users")).scalar_one() == 0


def test_type_can_be_changed_and_cleared(make_client, clean_db):
    client = make_client()
    headers = bearer(register(client, "chg@example.com", learner_type="beginner"))

    changed = client.patch("/api/me/settings", json={"learner_type": "developer"}, headers=headers)
    assert changed.status_code == 200
    assert changed.json() == {"personalization_enabled": False, "learner_type": "developer"}

    untouched = client.patch("/api/me/settings", json={}, headers=headers)
    assert untouched.json()["learner_type"] == "developer"  # absent field = unchanged

    cleared = client.patch("/api/me/settings", json={"learner_type": None}, headers=headers)
    assert cleared.json()["learner_type"] is None
    assert client.get("/api/me", headers=headers).json()["settings"]["learner_type"] is None


@pytest.mark.parametrize(
    "body",
    [
        {"learner_type": "admin"},
        {"learner_type": "expert"},
        # The switch is settable since P4, but only with a real boolean.
        {"personalization_enabled": None},
        {"personalization_enabled": "yes"},
        {"role": "admin"},
    ],
)
def test_invalid_settings_changes_are_rejected(make_client, clean_db, body):
    client = make_client()
    headers = bearer(register(client, "inv@example.com", learner_type="beginner"))

    response = client.patch("/api/me/settings", json=body, headers=headers)

    assert response.status_code == 422
    me = client.get("/api/me", headers=headers).json()
    assert me["role"] == "user"
    assert me["settings"] == {"personalization_enabled": False, "learner_type": "beginner"}


# --- 4. access control and isolation -----------------------------------------------------


def test_settings_require_login(make_client, clean_db):
    client = make_client()
    assert client.patch("/api/me/settings", json={"learner_type": "beginner"}).status_code == 401
    bad = {"Authorization": "Bearer not-a-token"}
    assert client.patch("/api/me/settings", json={}, headers=bad).status_code == 401


def test_users_only_change_their_own_settings(make_client, clean_db):
    client = make_client()
    alice = bearer(register(client, "alice@example.com", learner_type="beginner"))
    bob = bearer(register(client, "bob@example.com", learner_type="exploring"))

    client.patch("/api/me/settings", json={"learner_type": "developer"}, headers=alice)

    assert stored_type(clean_db, "alice@example.com") == "developer"
    assert stored_type(clean_db, "bob@example.com") == "exploring"
    assert client.get("/api/me", headers=bob).json()["settings"]["learner_type"] == "exploring"


# --- 5. public responses do not depend on the learner type -------------------------------


def test_public_content_is_identical_for_every_learner_type(make_client, clean_db, tmp_path):
    load(clean_db, write_track(tmp_path, slug="py", units=[UNIT_ONE, UNIT_TWO]))
    seed_catalog(clean_db)
    collect_all(clean_db)
    client = make_client()
    headers = bearer(register(client, "same@example.com"))
    urls = [
        "/api/news",
        "/api/news?tech=python",
        "/api/dev/channels",
        "/api/dev/channels/devto/posts?sort=popular",
        "/api/trends?scope=dev",
        "/api/tracks",
        "/api/tracks/py",
        "/api/tracks/py/units/one",
        "/api/tracks/py/units/one/quiz",
        "/api/technologies/python/units",
    ]

    def snapshot(with_token):
        return [client.get(u, headers=headers if with_token else {}).content for u in urls]

    guest = snapshot(with_token=False)
    for learner_type in (None, "beginner", "developer", "exploring"):
        client.patch("/api/me/settings", json={"learner_type": learner_type}, headers=headers)
        assert snapshot(with_token=True) == guest, learner_type


# --- 6. learning records are untouched ---------------------------------------------------


def test_changing_type_keeps_progress_quiz_results_and_xp(make_client, clean_db, tmp_path):
    load(clean_db, write_track(tmp_path, slug="py", units=[UNIT_ONE, UNIT_TWO]))
    client = make_client()
    learner = Learner(client, "keep@example.com")
    activities, quiz_id, questions = unit_info(client)
    for slug in ("read-a", "read-b"):
        assert learner.confirm(activities[slug]).status_code == 200
    assert learner.submit(quiz_id, answers(questions, q1=("a",))).json()["passed"] is False
    assert learner.submit(quiz_id, answers(questions)).json()["passed"] is True

    def records():
        with clean_db.connect() as connection:
            tables = (
                "user_activity_records",
                "user_unit_progress",
                "quiz_attempts",
                "quiz_attempt_answers",
                "xp_ledger",
            )
            return {
                t: connection.execute(text(f"SELECT * FROM {t} ORDER BY 1, 2")).all()
                for t in tables
            }

    before = (records(), learner.summary(), learner.unit_progress())
    for learner_type in ("beginner", "developer", None, "exploring"):
        response = learner.client.patch(
            "/api/me/settings", json={"learner_type": learner_type}, headers=learner.headers
        )
        assert response.status_code == 200
    after = (records(), learner.summary(), learner.unit_progress())

    assert after == before
    assert before[1]["xp"]["total"] == 100 and before[1]["completed_units"] == 1


# --- 7. sign-up rate limit ---------------------------------------------------------------


def test_signups_are_limited_per_client_ip(make_client, clean_db):
    client = make_client(register_rate_limit_attempts=3)
    statuses = [register(client, f"u{i}@example.com").status_code for i in range(3)]
    # Duplicates and invalid-but-parsed attempts count too.
    blocked = register(client, "u9@example.com")

    assert statuses == [201, 201, 201]
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "TOO_MANY_REGISTRATIONS"
    assert int(blocked.headers["Retry-After"]) > 0
    with clean_db.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM users")).scalar_one() == 3

    # Existing accounts can still log in from the same network.
    login = client.post("/api/auth/login", json={"email": "u0@example.com", "password": PASSWORD})
    assert login.status_code == 200


def test_duplicate_signups_count_toward_the_limit(make_client, clean_db):
    client = make_client(register_rate_limit_attempts=2)
    assert register(client, "dup@example.com").status_code == 201
    assert register(client, "dup@example.com").status_code == 409
    assert register(client, "new@example.com").status_code == 429


def test_default_signup_limit_is_five_per_hour(integration_settings):
    assert integration_settings.register_rate_limit_attempts == 5
    assert integration_settings.register_rate_limit_window_seconds == 3600
