"""P2: technologies a learning unit teaches (unit files) and the public lookup API."""

import copy

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, text

from app.content_loader.loader import apply_track
from app.content_loader.schema import ContentError, read_track_directory
from app.content_loader.taxonomy import TechnologiesFile, apply_technologies
from app.db.session import create_session_factory
from app.main import create_app
from tests.collect_helpers import TECHNOLOGIES, seed_catalog
from tests.content_helpers import activity, unit, write_track

pytestmark = pytest.mark.integration


def load(engine, directory):
    with create_session_factory(engine).begin() as db:
        return apply_track(db, read_track_directory(directory))


def links(engine):
    with engine.connect() as connection:
        return sorted(
            tuple(r)
            for r in connection.execute(
                text(
                    "SELECT u.slug, t.slug FROM learning_unit_technologies l "
                    "JOIN learning_units u ON u.id = l.unit_id "
                    "JOIN technologies t ON t.id = l.technology_id"
                )
            )
        )


@pytest.fixture()
def catalog(clean_db):
    seed_catalog(clean_db)  # technologies first, as CI/E2E/local loading now does
    return clean_db


# --- loader ------------------------------------------------------------------------------


def test_units_link_to_their_technologies_and_reloading_changes_nothing(catalog, tmp_path):
    directory = write_track(
        tmp_path,
        slug="py",
        units=[
            unit("one", 1, technologies=["python"]),
            unit("two", 2, technologies=["python", "backend"]),
            unit("three", 3),  # technologies are optional
        ],
    )
    first = load(catalog, directory)
    assert {"unit one technologies", "unit two technologies"} <= set(first.updated)
    assert links(catalog) == [("one", "python"), ("two", "backend"), ("two", "python")]

    again = load(catalog, directory)
    assert not again.changed
    assert links(catalog) == [("one", "python"), ("two", "backend"), ("two", "python")]


def test_changed_and_removed_technologies_follow_the_file(catalog, tmp_path):
    load(
        catalog,
        write_track(tmp_path, slug="py", units=[unit("one", 1, technologies=["python", "java"])]),
    )
    report = load(
        catalog, write_track(tmp_path, slug="py", units=[unit("one", 1, technologies=["kotlin"])])
    )
    assert report.updated == ["unit one technologies"]
    assert links(catalog) == [("one", "kotlin")]

    load(catalog, write_track(tmp_path, slug="py", units=[unit("one", 1)]))
    assert links(catalog) == []


@pytest.mark.parametrize("slug", ["no-such-tech", "rust-lang"])
def test_unknown_technology_stops_the_whole_load(catalog, tmp_path, slug):
    directory = write_track(
        tmp_path,
        slug="py",
        units=[unit("one", 1, technologies=["python"]), unit("two", 2, technologies=[slug])],
    )
    with pytest.raises(ContentError, match=f"unit 'two': {slug}"):
        load(catalog, directory)
    with catalog.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM learning_tracks")).scalar_one() == 0
    assert links(catalog) == []


def test_retired_technology_is_rejected(catalog, tmp_path):
    technologies = copy.deepcopy(TECHNOLOGIES)
    technologies["technologies"] = [t for t in technologies["technologies"] if t["slug"] != "rust"]
    with create_session_factory(catalog).begin() as db:
        apply_technologies(db, TechnologiesFile.model_validate(technologies))  # retires rust
    with pytest.raises(ContentError, match="retired"):
        load(
            catalog, write_track(tmp_path, slug="py", units=[unit("one", 1, technologies=["rust"])])
        )


def test_tracks_cannot_load_before_technologies(clean_db, tmp_path):
    """The CI/E2E ordering problem: an empty catalog rejects technology references."""
    with pytest.raises(ContentError, match="Load content/technologies.yaml first"):
        load(
            clean_db,
            write_track(tmp_path, slug="py", units=[unit("one", 1, technologies=["python"])]),
        )


def test_duplicate_technology_in_one_unit_is_a_file_error(tmp_path):
    directory = write_track(
        tmp_path, slug="py", units=[unit("one", 1, technologies=["python", "python"])]
    )
    with pytest.raises(ContentError, match="duplicate technology"):
        read_track_directory(directory)


# --- API ---------------------------------------------------------------------------------


@pytest.fixture()
def client(catalog, integration_settings, tmp_path):
    load(
        catalog,
        write_track(
            tmp_path,
            slug="py",
            position=1,
            units=[
                unit("basics", 1, technologies=["python"]),
                unit("web", 2, technologies=["python", "backend"]),
                unit("later", 3, technologies=["python"], status="draft"),
            ],
        ),
    )
    load(
        catalog,
        write_track(
            tmp_path,
            slug="jvm",
            position=2,
            units=[unit("intro", 1, technologies=["java", "python"])],
        ),
    )
    load(
        catalog,
        write_track(
            tmp_path,
            slug="old",
            position=3,
            status="retired",
            units=[unit("x", 1, technologies=["python"])],
        ),
    )
    application = create_app(integration_settings)
    with TestClient(application) as test_client:
        test_client.app_ref = application
        yield test_client


def test_unit_detail_lists_its_technologies(client):
    detail = client.get("/api/tracks/py/units/web").json()
    assert sorted(detail["technologies"], key=lambda t: t["slug"]) == [
        {"slug": "backend", "name": "백엔드"},
        {"slug": "python", "name": "Python"},
    ]
    intro = client.get("/api/tracks/jvm/units/intro").json()["technologies"]
    assert {t["slug"] for t in intro} == {"java", "python"}


def test_units_by_technology_in_catalog_order_published_only(client):
    body = client.get("/api/technologies/python/units").json()
    assert body["technology"] == {"slug": "python", "name": "Python"}
    assert [(u["track"]["slug"], u["slug"]) for u in body["units"]] == [
        ("py", "basics"),
        ("py", "web"),
        ("jvm", "intro"),
    ]  # draft unit and retired track are hidden

    assert [u["slug"] for u in client.get("/api/technologies/backend/units").json()["units"]] == [
        "web"
    ]
    assert client.get("/api/technologies/kotlin/units").json()["units"] == []


def test_units_by_technology_errors(client, catalog):
    missing = client.get("/api/technologies/no-such-tech/units")
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "TECHNOLOGY_NOT_FOUND"
    assert client.get("/api/technologies/Bad Slug/units").status_code == 422

    with catalog.begin() as connection:
        connection.execute(
            text("UPDATE technologies SET status = 'retired' WHERE slug = 'backend'")
        )
    assert client.get("/api/technologies/backend/units").status_code == 404
    assert {t["slug"] for t in client.get("/api/tracks/py/units/web").json()["technologies"]} == {
        "python"
    }


def test_technology_endpoints_never_write(client):
    writes = []

    def record(conn, cursor, statement, *args):
        if statement.lstrip().split(" ", 1)[0].upper() in {"INSERT", "UPDATE", "DELETE", "REPLACE"}:
            writes.append(statement)

    engine = client.app_ref.state.engine
    event.listen(engine, "before_cursor_execute", record)
    try:
        for url in ("/api/technologies/python/units", "/api/tracks/py/units/web"):
            assert client.get(url).status_code == 200
    finally:
        event.remove(engine, "before_cursor_execute", record)
    assert writes == []


def test_existing_unit_api_keeps_its_shape(client):
    detail = client.get("/api/tracks/py/units/basics").json()
    assert set(detail) == {
        "slug",
        "position",
        "title",
        "summary",
        "estimated_minutes",
        "track",
        "activities",
        "prev",
        "next",
        "quiz",
        "technologies",
    }
    assert detail["activities"][0]["slug"] == activity()["slug"]
