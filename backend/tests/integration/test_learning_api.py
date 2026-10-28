"""Public learning catalog API against the real MariaDB test database."""

import pytest
from fastapi.testclient import TestClient

from app.content_loader.loader import apply_track
from app.content_loader.schema import read_track_directory
from app.db.session import create_session_factory
from app.main import create_app
from tests.content_helpers import activity, unit, write_track

pytestmark = pytest.mark.integration


@pytest.fixture()
def client(clean_db, integration_settings, tmp_path):
    def load(directory):
        session = create_session_factory(clean_db)()
        try:
            apply_track(session, read_track_directory(directory))
            session.commit()
        finally:
            session.close()

    # "beta" is listed before "alpha" by position; it also has hidden rows.
    load(write_track(tmp_path, slug="alpha", position=2, units=[unit("intro", 1)]))
    load(
        write_track(
            tmp_path,
            slug="beta",
            position=1,
            units=[
                unit("first", 1, activities=[activity("read"), activity("hidden", status="draft")]),
                unit("gone", 2),
                unit("second", 3),
                unit("draft-unit", 4, status="draft"),
            ],
        )
    )
    # Retire "gone" by removing it from the files.
    load(
        write_track(
            tmp_path,
            slug="beta",
            position=1,
            units=[
                unit("first", 1, activities=[activity("read"), activity("hidden", status="draft")]),
                unit("second", 3),
                unit("draft-unit", 4, status="draft"),
            ],
        )
    )
    load(write_track(tmp_path, slug="secret", position=3, status="draft", units=[unit("x", 1)]))

    with TestClient(create_app(integration_settings)) as test_client:
        yield test_client


def test_track_list_shows_published_tracks_in_order(client):
    response = client.get("/api/tracks")
    assert response.status_code == 200
    items = response.json()["items"]
    assert [(t["slug"], t["unit_count"]) for t in items] == [("beta", 2), ("alpha", 1)]


def test_track_detail_lists_published_units_only(client):
    body = client.get("/api/tracks/beta").json()
    assert [(u["slug"], u["position"], u["activity_count"]) for u in body["units"]] == [
        ("first", 1, 1),
        ("second", 3, 1),
    ]


def test_unit_detail_has_ordered_activities_and_neighbours(client):
    body = client.get("/api/tracks/beta/units/first").json()
    assert body["track"] == {"slug": "beta", "title": "Track beta"}
    assert [a["slug"] for a in body["activities"]] == ["read"]
    activity_out = body["activities"][0]
    assert set(activity_out) == {
        "id",
        "slug",
        "position",
        "kind",
        "title",
        "url",
        "body_md",
        "is_required",
    }
    assert body["prev"] is None
    assert body["next"] == {"slug": "second", "title": "Unit second"}

    last = client.get("/api/tracks/beta/units/second").json()
    assert last["prev"] == {"slug": "first", "title": "Unit first"}
    assert last["next"] is None


def test_tracks_do_not_mix(client):
    alpha = client.get("/api/tracks/alpha").json()
    assert [u["slug"] for u in alpha["units"]] == ["intro"]
    assert client.get("/api/tracks/alpha/units/first").status_code == 404


@pytest.mark.parametrize(
    ("path", "code"),
    [
        ("/api/tracks/secret", "TRACK_NOT_FOUND"),  # draft track
        ("/api/tracks/missing", "TRACK_NOT_FOUND"),
        ("/api/tracks/secret/units/x", "TRACK_NOT_FOUND"),
        ("/api/tracks/beta/units/gone", "UNIT_NOT_FOUND"),  # retired
        ("/api/tracks/beta/units/draft-unit", "UNIT_NOT_FOUND"),
        ("/api/tracks/beta/units/missing", "UNIT_NOT_FOUND"),
    ],
)
def test_hidden_or_unknown_content_is_404(client, path, code):
    response = client.get(path)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == code


def test_catalog_is_public(client):
    # No Authorization header anywhere above; make it explicit for the list.
    assert client.get("/api/tracks", headers={}).status_code == 200
