from datetime import UTC, datetime, timedelta

import jwt
import pytest
from pydantic import ValidationError

from app.core.security import (
    InvalidAccessTokenError,
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.services.rate_limit import FailedAttemptLimiter
from tests.conftest import TEST_JWT_SECRET, make_settings

PROD_URL = "mysql+pymysql://devhub_app:S7rong-Unique-Pass@db.internal:3306/devhub"


@pytest.fixture()
def settings():
    return make_settings()


def test_password_hash_round_trip():
    hashed = hash_password("correct horse battery")
    assert hashed.startswith("$argon2id$")
    assert "correct horse battery" not in hashed
    assert verify_password("correct horse battery", hashed)
    assert not verify_password("wrong password", hashed)


def test_verify_password_rejects_malformed_hash():
    assert not verify_password("anything", "not-a-hash")


def test_access_token_round_trip(settings):
    token, expires_in = create_access_token(42, settings)
    assert expires_in == settings.access_token_ttl_seconds
    assert decode_access_token(token, settings) == 42


def test_expired_access_token_is_rejected(settings):
    past = datetime.now(UTC) - timedelta(seconds=settings.access_token_ttl_seconds + 5)
    token, _ = create_access_token(42, settings, now=past)
    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(token, settings)


def _encode(payload, key=TEST_JWT_SECRET, algorithm="HS256"):
    return jwt.encode(payload, key, algorithm=algorithm)


def _valid_payload(**overrides):
    now = datetime.now(UTC)
    payload = {"sub": "42", "type": "access", "iat": now, "exp": now + timedelta(minutes=5)}
    payload.update(overrides)
    return payload


@pytest.mark.parametrize(
    "token",
    [
        pytest.param(_encode(_valid_payload(), key="another-secret-0123456789abcdef!"), id="key"),
        pytest.param(_encode(_valid_payload(type="refresh")), id="type"),
        pytest.param(_encode(_valid_payload(sub="not-a-number")), id="sub-text"),
        pytest.param(
            _encode({k: v for k, v in _valid_payload().items() if k != "sub"}), id="no-sub"
        ),
        pytest.param(
            _encode({k: v for k, v in _valid_payload().items() if k != "exp"}), id="no-exp"
        ),
        pytest.param(_encode(_valid_payload(), algorithm="none", key=None), id="alg-none"),
        pytest.param(
            _encode(_valid_payload(), key=TEST_JWT_SECRET * 2, algorithm="HS512"), id="alg-hs512"
        ),
        pytest.param("not.a.jwt", id="garbage"),
    ],
)
def test_invalid_access_tokens_are_rejected(settings, token):
    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(token, settings)


def test_refresh_tokens_are_random_and_hashed():
    first, second = generate_refresh_token(), generate_refresh_token()
    assert first != second and len(first) >= 40
    digest = hash_refresh_token(first)
    assert len(digest) == 64 and digest != first
    assert hash_refresh_token(first) == digest


@pytest.mark.parametrize(
    "overrides",
    [
        {"jwt_secret": None},
        {"jwt_secret": "too-short"},
        {"jwt_secret": "change-me-change-me-change-me-change-me"},
        {"refresh_cookie_secure": False},
    ],
)
def test_production_fails_fast_on_weak_auth_settings(overrides):
    with pytest.raises(ValidationError, match="production"):
        make_settings(app_env="production", database_url=PROD_URL, **overrides)


def test_secure_cookie_defaults_by_environment():
    assert make_settings().use_secure_cookies is False
    assert make_settings(app_env="production", database_url=PROD_URL).use_secure_cookies is True


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def test_limiter_blocks_after_max_failures_and_recovers():
    clock = FakeClock()
    limiter = FailedAttemptLimiter(max_attempts=3, window_seconds=60, clock=clock)
    for _ in range(3):
        assert limiter.retry_after("a") is None
        limiter.record_failure("a")
    assert limiter.retry_after("a") == 60
    assert limiter.retry_after("b") is None  # other keys unaffected

    clock.now += 30
    assert limiter.retry_after("a") == 30
    clock.now += 31
    assert limiter.retry_after("a") is None


def test_limiter_reset_clears_failures():
    limiter = FailedAttemptLimiter(max_attempts=1, window_seconds=60, clock=FakeClock())
    limiter.record_failure("a")
    assert limiter.retry_after("a") is not None
    limiter.reset("a")
    assert limiter.retry_after("a") is None
