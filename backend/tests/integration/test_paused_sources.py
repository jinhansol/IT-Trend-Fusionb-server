"""The repository's sources.yaml: nothing unapproved is saved, paused feeds are not read.

Uses the real content/sources.yaml on the test database and a fake fetcher, so no feed
is requested from the network. No source in the file has approved terms yet, so a
saving `collect` refuses every source before any request; `--dry-run` reads only the
active ones (after their robots.txt) and writes nothing.
"""

import copy

import pytest
import yaml
from sqlalchemy import text

from app.jobs import __main__ as cli
from tests.collect_helpers import FakeFetcher, feed_requests, seed_catalog
from tests.conftest import BACKEND_DIR

pytestmark = pytest.mark.integration

PAUSED = {
    "itworld-korea",  # robots.txt forbids /feed/
    "woowahan-tech",  # the site blocks automated requests
    "ciokorea",  # no working feed
    "ddaily",  # no working feed
    "aitimes",  # candidates: terms not checked
    "boho-notice",
    "kurly-tech",
    "outsider-blog",
}


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


@pytest.fixture()
def fake_network(clean_db, integration_settings, monkeypatch):
    seed_catalog(clean_db, sources=repo_sources())
    fetcher = FakeFetcher({})  # every request answers 404 locally; nothing leaves the process
    fetcher.close = lambda: None
    monkeypatch.setattr(cli, "HttpFetcher", lambda settings: fetcher)
    monkeypatch.setattr(cli, "get_settings", lambda: integration_settings)
    return fetcher


def job_run_count(engine) -> int:
    with engine.connect() as connection:
        return connection.execute(text("SELECT COUNT(*) FROM job_runs")).scalar_one()


def test_collect_refuses_every_unapproved_source_before_any_request(clean_db, fake_network, capsys):
    assert cli.main(["collect"]) == 0
    assert cli.main(["collect", "--source", "zdnet-korea", "--source", "itworld-korea"]) == 0
    out = capsys.readouterr().out
    assert fake_network.calls == []
    assert job_run_count(clean_db) == 0
    assert "zdnet-korea      refused" in out and "terms not approved" in out
    assert "itworld-korea    refused" in out and "paused" in out


def test_a_dry_run_reads_only_active_feeds_and_writes_nothing(clean_db, fake_network):
    cli.main(["collect", "--dry-run"])
    feeds = {s["slug"]: s["feed_url"] for s in repo_sources()["sources"]}
    assert feed_requests(fake_network) == {url for slug, url in feeds.items() if slug not in PAUSED}
    assert job_run_count(clean_db) == 0
