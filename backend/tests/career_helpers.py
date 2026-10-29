"""Builders for throwaway career-role files used by tests (not service content)."""

from pathlib import Path

import yaml

from app.content_loader.careers import apply_careers, read_careers
from app.content_loader.loader import apply_track
from app.content_loader.schema import read_track_directory
from app.db.session import create_session_factory
from tests.collect_helpers import seed_catalog
from tests.content_helpers import unit, write_track


def role(slug="backend-dev", position=1, core=("python",), related=(), **overrides):
    data = {
        "slug": slug,
        "name": f"Role {slug}",
        "position": position,
        "summary": f"Summary of {slug}",
        "description_md": f"What a **{slug}** does.",
        "tasks": ["Task one", "Task two"],
        "technologies": {"core": list(core), "related": list(related)},
        "references": [{"title": "Source", "url": "https://example.com/source"}],
    }
    data.update(overrides)
    return data


def write_careers(path: Path, roles) -> Path:
    path.write_text(yaml.safe_dump({"roles": list(roles)}, allow_unicode=True), "utf-8")
    return path


# Isolated test catalog for career tests: its own tracks and roles, never the real
# content/python unit or content/careers.yaml.
TEST_ROLES = [
    role("backend-dev", 1, core=["python", "backend"], related=["kubernetes"]),
    role("frontend-dev", 2, core=["javascript", "react"]),
    role("no-units", 3, core=["rust"]),
]


def seed_careers(engine, tmp_path, roles=TEST_ROLES):
    """Technologies, two test tracks with technology links, and the given roles."""
    seed_catalog(engine)
    tracks = [
        write_track(
            tmp_path / "tracks",
            slug="py-test",
            position=1,
            units=[
                unit("py-basics", 1, technologies=["python"]),
                unit("py-web", 2, technologies=["python", "backend"]),
                unit("py-draft", 3, technologies=["python"], status="draft"),
            ],
        ),
        write_track(
            tmp_path / "tracks",
            slug="js-test",
            position=2,
            units=[unit("js-basics", 1, technologies=["javascript"])],
        ),
    ]
    session_factory = create_session_factory(engine)
    with session_factory.begin() as db:
        for directory in tracks:
            apply_track(db, read_track_directory(directory))
        apply_careers(db, read_careers(write_careers(tmp_path / "careers.yaml", roles)))
