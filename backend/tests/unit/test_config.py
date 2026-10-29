import pytest
from pydantic import ValidationError

from tests.conftest import UNIT_DB_PASSWORD, make_settings

PROD_URL = "mysql+pymysql://devhub_app:S7rong-Unique-Pass@db.internal:3306/devhub"


def test_local_settings_are_valid():
    settings = make_settings()
    assert settings.app_env == "local"
    assert settings.database_name == "devhub_unit"
    assert not settings.use_json_logs


def test_password_is_not_exposed_by_repr_or_dump():
    settings = make_settings()
    assert UNIT_DB_PASSWORD not in repr(settings)
    assert UNIT_DB_PASSWORD not in str(settings.model_dump())


@pytest.mark.parametrize(
    "url",
    [
        "sqlite:///devhub.db",
        "postgresql://u:p@localhost/devhub",
        "mysql+pymysql://u:p@localhost",  # no database name
        "not a url",
    ],
)
def test_rejects_non_mariadb_or_incomplete_urls(url):
    with pytest.raises(ValidationError):
        make_settings(database_url=url)


def test_test_env_requires_test_database():
    with pytest.raises(ValidationError, match="_test"):
        make_settings(app_env="test", database_url="mysql+pymysql://u:p@localhost/devhub_dev")


def test_non_test_env_rejects_test_database():
    with pytest.raises(ValidationError, match="_test"):
        make_settings(app_env="local", database_url="mysql+pymysql://u:p@localhost/devhub_test")


def test_production_accepts_strong_settings():
    settings = make_settings(app_env="production", database_url=PROD_URL)
    assert settings.is_production
    assert settings.use_json_logs


@pytest.mark.parametrize(
    "url",
    [
        "mysql+pymysql://root:S7rong-Unique-Pass@db.internal/devhub",
        "mysql+pymysql://devhub_app@db.internal/devhub",
        "mysql+pymysql://devhub_app:change-me@db.internal/devhub",
        "mysql+pymysql://devhub_dev:devhub_local_dev@db.internal/devhub",
    ],
)
def test_production_fails_fast_on_unsafe_database_credentials(url):
    with pytest.raises(ValidationError, match="production"):
        make_settings(app_env="production", database_url=url)


def test_unknown_app_env_is_rejected():
    with pytest.raises(ValidationError):
        make_settings(app_env="staging-ish")


def test_database_url_is_required(monkeypatch):
    from app.core.config import Settings

    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValidationError, match="database_url"):
        Settings(_env_file=None)


def test_signup_limit_defaults_to_five_when_not_set(monkeypatch):
    """A missing setting never relaxes the sign-up limit (E2E raises it for its own
    test server only, see e2e/playwright.config.js)."""
    monkeypatch.delenv("REGISTER_RATE_LIMIT_ATTEMPTS", raising=False)
    assert make_settings().register_rate_limit_attempts == 5


@pytest.mark.parametrize("value", ["", "0", "-1", "abc", "3.5"])
def test_invalid_signup_limit_stops_startup_instead_of_relaxing(monkeypatch, value):
    monkeypatch.setenv("REGISTER_RATE_LIMIT_ATTEMPTS", value)
    with pytest.raises(ValidationError):
        make_settings()
