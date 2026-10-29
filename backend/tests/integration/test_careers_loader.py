"""P3-1: career roles file loader (roles, role technologies) and reserved track slugs."""

import copy

import pytest
import yaml
from sqlalchemy import text

from app.content_loader.careers import apply_careers, read_careers
from app.content_loader.schema import ContentError, read_track_directory
from app.content_loader.taxonomy import TechnologiesFile, apply_technologies
from app.db.session import create_session_factory
from tests.career_helpers import role, write_careers
from tests.collect_helpers import TECHNOLOGIES, seed_catalog
from tests.content_helpers import unit, write_track

pytestmark = pytest.mark.integration


@pytest.fixture()
def catalog(clean_db):
    seed_catalog(clean_db)  # technologies first
    return clean_db


def load(engine, path):
    with create_session_factory(engine).begin() as db:
        return apply_careers(db, read_careers(path))


def rows(engine, sql):
    with engine.connect() as connection:
        return [tuple(r) for r in connection.execute(text(sql))]


def role_links(engine):
    return rows(
        engine,
        "SELECT r.slug, t.slug, l.importance, l.position FROM career_role_technologies l "
        "JOIN career_roles r ON r.id = l.role_id JOIN technologies t ON t.id = l.technology_id "
        "ORDER BY r.slug, l.importance, l.position",
    )


def test_roles_load_with_technologies_and_reloading_changes_nothing(catalog, tmp_path):
    path = write_careers(
        tmp_path / "careers.yaml",
        [
            role("backend-dev", 1, core=["python", "java"], related=["kubernetes"]),
            role("frontend-dev", 2, core=["javascript", "react"]),
        ],
    )
    first = load(catalog, path)
    assert first.created == ["backend-dev", "frontend-dev"]
    assert role_links(catalog) == [
        ("backend-dev", "python", "core", 1),
        ("backend-dev", "java", "core", 2),
        ("backend-dev", "kubernetes", "related", 1),
        ("frontend-dev", "javascript", "core", 1),
        ("frontend-dev", "react", "core", 2),
    ]
    stored = rows(
        catalog,
        "SELECT slug, position, status, JSON_LENGTH(tasks), "
        "JSON_UNQUOTE(JSON_EXTRACT(reference_links, '$[0].url')) FROM career_roles ORDER BY slug",
    )
    assert stored == [
        ("backend-dev", 1, "published", 2, "https://example.com/source"),
        ("frontend-dev", 2, "published", 2, "https://example.com/source"),
    ]

    again = load(catalog, path)
    assert not again.changed


def test_changes_follow_the_file_and_missing_roles_are_retired(catalog, tmp_path):
    path = tmp_path / "careers.yaml"
    load(catalog, write_careers(path, [role("a", 1, core=["python"]), role("b", 2)]))

    report = load(
        catalog,
        write_careers(
            path, [role("a", 1, core=["java"], related=["python"], summary="New summary")]
        ),
    )
    assert report.updated == ["a", "a technologies"]
    assert report.retired == ["b"]
    assert role_links(catalog) == [
        ("a", "java", "core", 1),
        ("a", "python", "related", 1),
        ("b", "python", "core", 1),  # a retired role keeps its rows (nothing is deleted)
    ]
    assert rows(catalog, "SELECT slug, status FROM career_roles ORDER BY slug") == [
        ("a", "published"),
        ("b", "retired"),
    ]

    # Listing it again brings it back.
    load(catalog, write_careers(path, [role("a", 1, core=["java"]), role("b", 2)]))
    assert rows(catalog, "SELECT status FROM career_roles WHERE slug = 'b'") == [("published",)]


@pytest.mark.parametrize("slug", ["no-such-tech", "rust"])
def test_unknown_or_retired_technology_stops_the_whole_load(catalog, tmp_path, slug):
    if slug == "rust":
        technologies = copy.deepcopy(TECHNOLOGIES)
        technologies["technologies"] = [
            t for t in technologies["technologies"] if t["slug"] != "rust"
        ]
        with create_session_factory(catalog).begin() as db:
            apply_technologies(db, TechnologiesFile.model_validate(technologies))
    path = write_careers(tmp_path / "careers.yaml", [role("a", 1), role("b", 2, related=[slug])])
    with pytest.raises(ContentError, match=f"unknown or retired technologies \\({slug}\\)"):
        load(catalog, path)
    assert rows(catalog, "SELECT COUNT(*) FROM career_roles") == [(0,)]


def test_careers_cannot_load_before_technologies(clean_db, tmp_path):
    with pytest.raises(ContentError, match="Load content/technologies.yaml first"):
        load(clean_db, write_careers(tmp_path / "careers.yaml", [role("a", 1)]))


@pytest.mark.parametrize(
    ("roles", "message"),
    [
        ([role("a", 1), role("a", 2)], "duplicate role slug"),
        ([role("a", 1), role("b", 1)], "duplicate role position"),
        ([role("a", 1, core=["python"], related=["python"])], "duplicate technology in role a"),
        ([role("a", 1, core=[])], "core"),
        ([role("a", 1, references=[])], "references"),
        ([role("a", 1, references=[{"title": "x", "url": "ftp://x"}])], "http"),
        ([role("a", 1, tasks=[])], "tasks"),
        ([role("a", 1, description_md="**직무(job)**는")], "bold"),
        ([role("a", 1, salary="1")], "salary"),  # unknown keys are rejected
    ],
)
def test_file_errors(tmp_path, roles, message):
    with pytest.raises(ContentError, match=message):
        read_careers(write_careers(tmp_path / "careers.yaml", roles))


@pytest.mark.parametrize("slug", ["explore", "roles", "goals"])
def test_track_slugs_used_by_career_screens_are_reserved(tmp_path, slug):
    with pytest.raises(ContentError, match="reserved for Career screens"):
        read_track_directory(write_track(tmp_path, slug=slug, units=[unit("one", 1)]))


def test_e2e_test_roles_file_is_valid_and_loads(clean_db):
    """The E2E seed loads it on top of the real technology taxonomy."""
    from tests.e2e_seed import CAREERS_FILE, TECHNOLOGIES_FILE

    seed_catalog(clean_db, technologies=yaml.safe_load(TECHNOLOGIES_FILE.read_text("utf-8")))
    report = load(clean_db, CAREERS_FILE)
    assert report.created == ["e2e-backend", "e2e-frontend"]
