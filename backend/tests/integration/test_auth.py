"""Authentication flows against the real MariaDB test database."""

import threading
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.security import create_access_token
from app.main import create_app
from app.services import auth as auth_service
from app.services.auth import EmailAlreadyRegistered

pytestmark = pytest.mark.integration

COOKIE = "devhub_refresh"
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


@pytest.fixture()
def client(make_client):
    return make_client()


def register(client, email="alice@example.com", password=PASSWORD, name="Alice"):
    return client.post(
        "/api/auth/register", json={"email": email, "password": password, "display_name": name}
    )


def login(client, email="alice@example.com", password=PASSWORD):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def refresh_with(client, cookie_value, **headers):
    client.cookies.clear()
    return client.post(
        "/api/auth/refresh", headers={"Cookie": f"{COOKIE}={cookie_value}", **headers}
    )


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def scalar(engine, sql, **params):
    with engine.connect() as connection:
        return connection.execute(text(sql), params).scalar()


# --- registration -----------------------------------------------------------------------


def test_register_creates_user_with_settings_and_logs_in(client, clean_db):
    response = register(client, email="Alice@Example.COM")
    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer" and body["expires_in"] == 900
    assert body["user"]["email"] == "alice@example.com"
    assert body["user"]["display_name"] == "Alice"
    assert set(body["user"]) == {"id", "email", "display_name", "role", "created_at"}
    assert "password" not in response.text and "argon2" not in response.text

    cookie_header = response.headers["set-cookie"]
    assert f"{COOKIE}=" in cookie_header
    for attribute in ("HttpOnly", "Path=/api/auth", "SameSite=strict"):
        assert attribute.lower() in cookie_header.lower()
    assert "secure" not in cookie_header.lower()  # plain http outside production

    user_id = body["user"]["id"]
    assert scalar(clean_db, "SELECT email FROM users WHERE id=:i", i=user_id) == "alice@example.com"
    assert (
        scalar(
            clean_db,
            "SELECT personalization_enabled FROM user_settings WHERE user_id=:i",
            i=user_id,
        )
        == 0
    )
    raw_cookie = response.cookies[COOKIE]
    stored_hash = scalar(
        clean_db, "SELECT token_hash FROM refresh_tokens WHERE user_id=:i", i=user_id
    )
    assert stored_hash and stored_hash != raw_cookie


def test_duplicate_email_is_rejected_case_insensitively(client, clean_db):
    assert register(client).status_code == 201
    duplicate = register(client, email="ALICE@example.com", name="Other")
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"
    assert scalar(clean_db, "SELECT COUNT(*) FROM users") == 1


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "not-an-email", "password": PASSWORD, "display_name": "A"},
        {"email": "a@example.com", "password": "short", "display_name": "A"},
        {"email": "a@example.com", "password": "x" * 129, "display_name": "A"},
        {"email": "a@example.com", "password": PASSWORD, "display_name": "   "},
        {"email": "a@example.com", "password": PASSWORD, "display_name": "x" * 51},
        {"email": "a@example.com", "password": PASSWORD, "display_name": "bad\nname"},
    ],
)
def test_register_validation(client, clean_db, payload):
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert scalar(clean_db, "SELECT COUNT(*) FROM users") == 0


def test_concurrent_registration_with_same_email_creates_one_user(client, clean_db):
    app = client.app
    barrier = threading.Barrier(2)
    outcomes = []

    def attempt():
        db = app.state.session_factory()
        try:
            barrier.wait()
            auth_service.register_user(
                db,
                app.state.settings,
                email="race@example.com",
                password=PASSWORD,
                display_name="Racer",
                user_agent=None,
            )
            outcomes.append("created")
        except EmailAlreadyRegistered:
            outcomes.append("duplicate")
        finally:
            db.close()

    threads = [threading.Thread(target=attempt) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert sorted(outcomes) == ["created", "duplicate"]
    assert scalar(clean_db, "SELECT COUNT(*) FROM users") == 1
    assert scalar(clean_db, "SELECT COUNT(*) FROM user_settings") == 1


def test_registration_rolls_back_completely_on_failure(client, clean_db, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("token store unavailable")

    monkeypatch.setattr(auth_service, "_issue_refresh_token", boom)
    response = register(client)
    assert response.status_code == 500
    assert scalar(clean_db, "SELECT COUNT(*) FROM users") == 0
    assert scalar(clean_db, "SELECT COUNT(*) FROM user_settings") == 0


# --- login --------------------------------------------------------------------------------


def test_login_succeeds_and_failures_look_identical(make_client, clean_db):
    assert register(make_client()).status_code == 201

    client = make_client()
    ok = login(client, email="ALICE@example.com")
    assert ok.status_code == 200
    assert ok.json()["user"]["email"] == "alice@example.com"
    assert COOKIE in ok.cookies

    wrong_password = login(client, password="wrong password!")
    unknown_email = login(client, email="nobody@example.com")
    for response in (wrong_password, unknown_email):
        assert response.status_code == 401
        assert COOKIE not in response.cookies
    first, second = wrong_password.json()["error"], unknown_email.json()["error"]
    assert (first["code"], first["message"]) == (second["code"], second["message"])
    assert first["code"] == "INVALID_CREDENTIALS"


def test_login_is_rate_limited_after_repeated_failures(make_client, clean_db):
    client = make_client(login_rate_limit_attempts=3, login_rate_limit_window_seconds=60)
    assert register(client).status_code == 201
    for _ in range(3):
        assert login(client, password="wrong password!").status_code == 401

    blocked = login(client)  # even the right password is refused for now
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "TOO_MANY_ATTEMPTS"
    assert 0 < int(blocked.headers["Retry-After"]) <= 60


def test_disabled_user_cannot_login_refresh_or_call_api(client, clean_db):
    registered = register(client)
    token = registered.json()["access_token"]
    cookie = registered.cookies[COOKIE]
    with clean_db.begin() as connection:
        connection.execute(text("UPDATE users SET status='disabled'"))

    assert client.get("/api/me", headers=bearer(token)).status_code == 401
    assert login(client).status_code == 401
    assert refresh_with(client, cookie).status_code == 401


# --- /api/me and access tokens ------------------------------------------------------------


def test_me_requires_a_valid_access_token(client, clean_db):
    user = register(client).json()["user"]
    settings = client.app.state.settings
    expired, _ = create_access_token(
        user["id"], settings, now=datetime.now(UTC) - timedelta(hours=1)
    )
    unknown_user, _ = create_access_token(user["id"] + 1000, settings)

    no_header = client.get("/api/me")
    assert no_header.status_code == 401
    assert no_header.headers["WWW-Authenticate"] == "Bearer"
    for token in ("garbage", expired, unknown_user):
        response = client.get("/api/me", headers=bearer(token))
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_each_user_only_sees_their_own_profile(make_client, clean_db):
    alice = register(make_client(), email="alice@example.com", name="Alice").json()
    bob = register(make_client(), email="bob@example.com", name="Bob").json()

    client = make_client()
    me_alice = client.get("/api/me", headers=bearer(alice["access_token"])).json()
    me_bob = client.get("/api/me", headers=bearer(bob["access_token"])).json()

    assert (me_alice["id"], me_alice["email"]) == (alice["user"]["id"], "alice@example.com")
    assert (me_bob["id"], me_bob["email"]) == (bob["user"]["id"], "bob@example.com")
    # P1 added learner_type; NULL until the user picks one.
    assert me_alice["settings"] == {"personalization_enabled": False, "learner_type": None}
    assert set(me_alice) == {"id", "email", "display_name", "role", "created_at", "settings"}


# --- refresh tokens -----------------------------------------------------------------------


def test_refresh_rotates_the_token(client, clean_db):
    first_cookie = register(client).cookies[COOKIE]
    response = refresh_with(client, first_cookie)
    assert response.status_code == 200
    second_cookie = response.cookies[COOKIE]
    assert second_cookie != first_cookie
    assert client.get("/api/me", headers=bearer(response.json()["access_token"])).status_code == 200

    old_revoked, old_successor = (
        scalar(clean_db, "SELECT revoked_at IS NOT NULL FROM refresh_tokens ORDER BY id LIMIT 1"),
        scalar(clean_db, "SELECT replaced_by_id FROM refresh_tokens ORDER BY id LIMIT 1"),
    )
    newest = scalar(clean_db, "SELECT MAX(id) FROM refresh_tokens")
    assert old_revoked == 1 and old_successor == newest


def test_reusing_a_rotated_token_revokes_the_whole_login(make_client, clean_db):
    client = make_client(refresh_reuse_grace_seconds=0)
    first_cookie = register(client).cookies[COOKIE]
    second_cookie = refresh_with(client, first_cookie).cookies[COOKIE]

    reuse = refresh_with(client, first_cookie)
    assert reuse.status_code == 401
    assert reuse.json()["error"]["code"] == "REFRESH_TOKEN_INVALID"
    assert f"{COOKIE}=" in reuse.headers.get("set-cookie", "")  # cookie cleared

    assert refresh_with(client, second_cookie).status_code == 401
    assert scalar(clean_db, "SELECT COUNT(*) FROM refresh_tokens WHERE revoked_at IS NULL") == 0


def test_concurrent_refresh_within_grace_is_not_treated_as_theft(make_client, clean_db):
    client = make_client(refresh_reuse_grace_seconds=10)
    first_cookie = register(client).cookies[COOKIE]
    second_cookie = refresh_with(client, first_cookie).cookies[COOKIE]

    late = refresh_with(client, first_cookie)
    assert late.status_code == 401
    assert late.json()["error"]["code"] == "REFRESH_TOKEN_ROTATED"
    assert "set-cookie" not in late.headers  # keep the newer cookie in the browser

    assert refresh_with(client, second_cookie).status_code == 200


def test_expired_or_missing_refresh_token_is_rejected(client, clean_db):
    cookie = register(client).cookies[COOKIE]
    with clean_db.begin() as connection:
        connection.execute(text("UPDATE refresh_tokens SET expires_at = '2000-01-01'"))
    assert refresh_with(client, cookie).status_code == 401

    client.cookies.clear()
    missing = client.post("/api/auth/refresh")
    assert missing.status_code == 401
    assert missing.json()["error"]["code"] == "REFRESH_TOKEN_INVALID"


def test_logout_revokes_the_refresh_token(client, clean_db):
    cookie = register(client).cookies[COOKIE]
    client.cookies.clear()
    response = client.post("/api/auth/logout", headers={"Cookie": f"{COOKIE}={cookie}"})
    assert response.status_code == 204
    assert (
        f'{COOKIE}=""' in response.headers["set-cookie"]
        or "Max-Age=0" in response.headers["set-cookie"]
    )
    assert refresh_with(client, cookie).status_code == 401

    client.cookies.clear()
    assert client.post("/api/auth/logout").status_code == 204  # idempotent


def test_cookie_endpoints_reject_cross_site_origins(client, clean_db):
    cookie = register(client).cookies[COOKIE]
    evil = refresh_with(client, cookie, Origin="https://evil.example")
    assert evil.status_code == 403
    assert evil.json()["error"]["code"] == "ORIGIN_NOT_ALLOWED"

    same_site = refresh_with(client, cookie, Origin="http://testserver")
    assert same_site.status_code == 200
