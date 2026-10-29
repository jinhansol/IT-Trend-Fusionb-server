"""P3-3: public career role API. Read-only and the same for every visitor."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, text

from app.main import create_app
from tests.career_helpers import seed_careers

pytestmark = pytest.mark.integration

PASSWORD = "correct horse 1"


@pytest.fixture()
def client(clean_db, integration_settings, tmp_path):
    seed_careers(clean_db, tmp_path)
    application = create_app(integration_settings)
    with TestClient(application) as test_client:
        test_client.app_ref = application
        yield test_client


def test_roles_are_listed_in_file_order_with_core_technologies(client):
    items = client.get("/api/careers/roles").json()["items"]
    assert [i["slug"] for i in items] == ["backend-dev", "frontend-dev", "no-units"]
    assert items[0] == {
        "slug": "backend-dev",
        "name": "Role backend-dev",
        "summary": "Summary of backend-dev",
        "core_technologies": [
            {"slug": "python", "name": "Python"},
            {"slug": "backend", "name": "백엔드"},
        ],
        "technology_count": 3,
    }


def test_role_detail_links_technologies_to_published_units(client):
    detail = client.get("/api/careers/roles/backend-dev").json()
    assert detail["tasks"] == ["Task one", "Task two"]
    assert detail["references"] == [{"title": "Source", "url": "https://example.com/source"}]
    assert detail["description_md"] == "What a **backend-dev** does."
    technologies = [
        (t["slug"], t["importance"], [u["slug"] for u in t["units"]])
        for t in detail["technologies"]
    ]
    assert technologies == [
        ("python", "core", ["py-basics", "py-web"]),  # the draft unit is hidden
        ("backend", "core", ["py-web"]),
        ("kubernetes", "related", []),
    ]
    assert detail["technologies"][0]["units"][0]["track"] == {
        "slug": "py-test",
        "title": "Track py-test",
    }
    assert client.get("/api/careers/roles/no-units").json()["technologies"][0]["units"] == []


def test_retired_roles_and_technologies_are_hidden(client, clean_db):
    with clean_db.begin() as connection:
        connection.execute(
            text("UPDATE career_roles SET status = 'retired' WHERE slug = 'no-units'")
        )
        connection.execute(
            text("UPDATE technologies SET status = 'retired' WHERE slug = 'backend'")
        )
    items = client.get("/api/careers/roles").json()["items"]
    assert [i["slug"] for i in items] == ["backend-dev", "frontend-dev"]
    assert items[0]["technology_count"] == 2
    missing = client.get("/api/careers/roles/no-units")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "CAREER_ROLE_NOT_FOUND"
    detail = client.get("/api/careers/roles/backend-dev").json()
    assert [t["slug"] for t in detail["technologies"]] == ["python", "kubernetes"]


def test_unknown_and_malformed_slugs(client):
    assert client.get("/api/careers/roles/nope").status_code == 404
    assert client.get("/api/careers/roles/Bad_Slug").status_code == 422


def test_role_endpoints_never_write(client):
    writes = []

    def record(conn, cursor, statement, *args):
        if statement.lstrip().split(" ", 1)[0].upper() in {"INSERT", "UPDATE", "DELETE", "REPLACE"}:
            writes.append(statement)

    engine = client.app_ref.state.engine
    event.listen(engine, "before_cursor_execute", record)
    try:
        for url in ("/api/careers/roles", "/api/careers/roles/backend-dev"):
            assert client.get(url).status_code == 200
    finally:
        event.remove(engine, "before_cursor_execute", record)
    assert writes == []


def test_guests_members_learner_types_and_personalization_see_the_same(client, clean_db):
    urls = ["/api/careers/roles", "/api/careers/roles/backend-dev", "/api/careers/roles/no-units"]
    guest = [client.get(u).content for u in urls]

    response = client.post(
        "/api/auth/register",
        json={"email": "same@example.com", "password": PASSWORD, "display_name": "Same"},
    )
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
    for learner_type in (None, "beginner", "developer", "exploring"):
        client.patch("/api/me/settings", json={"learner_type": learner_type}, headers=headers)
        for personalization in (0, 1):
            with clean_db.begin() as connection:
                connection.execute(
                    text("UPDATE user_settings SET personalization_enabled = :p"),
                    {"p": personalization},
                )
            member = [client.get(u, headers=headers).content for u in urls]
            assert member == guest, (learner_type, personalization)
