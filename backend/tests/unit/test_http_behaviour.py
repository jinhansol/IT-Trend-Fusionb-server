import logging

import pytest
from fastapi.testclient import TestClient

from app.core.errors import AppError
from app.main import create_app
from tests.conftest import UNIT_DB_PASSWORD, make_settings


@pytest.fixture()
def app():
    application = create_app(make_settings())

    @application.get("/_test/app-error")
    def raise_app_error():
        raise AppError(
            "Thing is missing", code="THING_NOT_FOUND", status_code=404, details={"id": 7}
        )

    @application.get("/_test/crash")
    def crash():
        raise RuntimeError(f"secret detail {UNIT_DB_PASSWORD}")

    @application.get("/_test/validate")
    def validate(limit: int):
        return {"limit": limit}

    return application


@pytest.fixture()
def client(app):
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def _assert_error(response, status, code):
    assert response.status_code == status
    error = response.json()["error"]
    assert error["code"] == code
    assert isinstance(error["message"], str)
    assert error["request_id"] == response.headers["X-Request-ID"]
    return error


def test_liveness_does_not_need_database(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_reports_unreachable_database_as_503(client):
    error = _assert_error(client.get("/api/health/ready"), 503, "DATABASE_UNAVAILABLE")
    assert UNIT_DB_PASSWORD not in error["message"]


def test_unknown_route_uses_error_format(client):
    _assert_error(client.get("/api/does-not-exist"), 404, "NOT_FOUND")


def test_wrong_method_uses_error_format(client):
    _assert_error(client.post("/api/health"), 405, "METHOD_NOT_ALLOWED")


def test_app_error_carries_code_and_details(client):
    error = _assert_error(client.get("/_test/app-error"), 404, "THING_NOT_FOUND")
    assert error["details"] == {"id": 7}


def test_validation_error_format(client):
    error = _assert_error(client.get("/_test/validate?limit=abc"), 422, "VALIDATION_ERROR")
    assert error["details"][0]["loc"] == ["query", "limit"]


def test_unexpected_error_hides_internals(client):
    response = client.get("/_test/crash")
    error = _assert_error(response, 500, "INTERNAL_ERROR")
    assert error["message"] == "Internal server error"
    assert UNIT_DB_PASSWORD not in response.text


def test_request_id_is_echoed_or_generated(client):
    assert (
        client.get("/api/health", headers={"X-Request-ID": "abc-123"}).headers["X-Request-ID"]
        == "abc-123"
    )
    generated = client.get("/api/health", headers={"X-Request-ID": "bad id!\n"}).headers[
        "X-Request-ID"
    ]
    assert generated != "bad id!\n" and len(generated) == 32


def test_logs_never_contain_database_password(caplog):
    caplog.set_level(logging.DEBUG)
    application = create_app(make_settings())
    with TestClient(application, raise_server_exceptions=False) as test_client:
        test_client.get("/api/health/ready")
    assert caplog.records, "expected some log output"
    assert UNIT_DB_PASSWORD not in caplog.text
    assert "mysql+pymysql://" not in caplog.text


def test_docs_are_disabled_in_production():
    settings = make_settings(
        app_env="production",
        database_url="mysql+pymysql://devhub_app:S7rong-Unique-Pass@127.0.0.1:9/devhub",
    )
    with TestClient(create_app(settings)) as test_client:
        assert test_client.get("/api/docs").status_code == 404
        assert test_client.get("/api/openapi.json").status_code == 404


def test_docs_are_available_locally(client):
    assert client.get("/api/openapi.json").status_code == 200
