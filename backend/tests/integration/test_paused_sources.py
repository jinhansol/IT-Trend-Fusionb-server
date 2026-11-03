"""Paused sources in the repository's sources.yaml stay out of every full collection run.

Uses the real content/sources.yaml on the test database and a fake fetcher, so no feed
is requested.
"""

import copy

import pytest
import yaml
from sqlalchemy import text

from app.jobs import __main__ as cli
from tests.collect_helpers import FakeFetcher, seed_catalog
from tests.conftest import BACKEND_DIR

pytestmark = pytest.mark.integration

PAUSED = {"itworld-korea", "woowahan-tech"}  # robots.txt forbids /feed/; site blocks bots


def repo_sources() -> dict:
    return yaml.safe_load((BACKEND_DIR / "content" / "sources.yaml").read_text(encoding="utf-8"))


def statuses(engine) -> dict[str, str]:
    with engine.connect() as connection:
        return dict(connection.execute(text("SELECT slug, status FROM content_sources")).all())


def test_loading_the_file_pauses_an_existing_active_source(clean_db):
    before = copy.deepcopy(repo_sources())
    for source in before["sources"]:
        source.pop("status", None)  # as the database had it: every source active
    seed_catalog(clean_db, sources=before)
    assert statuses(clean_db)["itworld-korea"] == "active"

    seed_catalog(clean_db, sources=repo_sources())  # python -m app.content_loader sources ...
    listed = {s["slug"] for s in repo_sources()["sources"]}
    after = {slug: status for slug, status in statuses(clean_db).items() if slug in listed}
    assert {slug for slug, status in after.items() if status == "paused"} == PAUSED
    assert all(status == "active" for slug, status in after.items() if slug not in PAUSED)


def test_a_full_collect_never_requests_paused_sources(clean_db, integration_settings, monkeypatch):
    seed_catalog(clean_db, sources=repo_sources())
    fetcher = FakeFetcher({})  # every request answers 404 locally; nothing leaves the process
    fetcher.close = lambda: None
    monkeypatch.setattr(cli, "HttpFetcher", lambda settings: fetcher)
    monkeypatch.setattr(cli, "get_settings", lambda: integration_settings)

    cli.main(["collect"])
    cli.main(["collect", "--dry-run"])

    requested = {url for url, _ in fetcher.calls}
    feeds = {s["slug"]: s["feed_url"] for s in repo_sources()["sources"]}
    assert not requested & {feeds[slug] for slug in PAUSED}
    assert requested == {url for slug, url in feeds.items() if slug not in PAUSED}
    with clean_db.connect() as connection:
        ran = set(
            connection.execute(
                text(
                    "SELECT DISTINCT s.slug FROM job_runs j "
                    "JOIN content_sources s ON s.id = j.source_id"
                )
            ).scalars()
        )
    assert not ran & PAUSED
