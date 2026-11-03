"""Source terms in practice: what is saved, what is shown, and robots.txt in a real run."""

import copy

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.integrations.robots import RobotsPolicy
from app.integrations.sources import adapters
from app.jobs.runner import Collector
from app.main import create_app
from tests.collect_helpers import (
    SOURCES,
    FakeFetcher,
    collect_all,
    feed_requests,
    sample_routes,
    seed_catalog,
)
from tests.integration.test_content_api import shift_dates_to_now

pytestmark = pytest.mark.integration


def catalog(**news_options) -> dict:
    data = copy.deepcopy(SOURCES)
    data["sources"][0]["options"] = news_options  # sample-news
    return data


def contents(engine, slug: str) -> int:
    with engine.connect() as connection:
        return connection.execute(
            text(
                "SELECT COUNT(*) FROM contents c JOIN content_sources s ON s.id = c.source_id "
                "WHERE s.slug = :slug"
            ),
            {"slug": slug},
        ).scalar_one()


def test_an_unverified_source_is_refused_and_nothing_is_requested_or_written(clean_db):
    seed_catalog(clean_db, sources=catalog())  # options: {} -> terms: unverified
    results = collect_all(clean_db)
    assert results["sample-news"].status == "refused"
    assert "terms not approved" in results["sample-news"].error
    assert results["sample-blog"].status == "succeeded"
    assert contents(clean_db, "sample-news") == 0
    with clean_db.connect() as connection:
        ran = connection.execute(
            text(
                "SELECT COUNT(*) FROM job_runs j JOIN content_sources s ON s.id = j.source_id "
                "WHERE s.slug = 'sample-news'"
            )
        ).scalar_one()
    assert ran == 0


def news_items(settings) -> list[dict]:
    with TestClient(create_app(settings)) as client:
        return client.get("/api/news").json()["items"]


def test_the_feed_description_is_shown_only_when_the_terms_allow_it(clean_db, integration_settings):
    seed_catalog(clean_db, sources=catalog(terms="approved", excerpt=True))
    collect_all(clean_db)
    shift_dates_to_now(clean_db)
    assert any(i["excerpt"] for i in news_items(integration_settings))

    # Same rows, terms approved for title and link only: the stored description stays
    # (it feeds tagging) but is no longer returned.
    seed_catalog(clean_db, sources=catalog(terms="approved"))
    items = news_items(integration_settings)
    assert items and all(i["excerpt"] is None for i in items)
    assert all(i["title"] and i["url"] and i["source"]["slug"] for i in items)
    with clean_db.connect() as connection:
        stored = connection.execute(
            text("SELECT COUNT(*) FROM contents WHERE excerpt IS NOT NULL")
        ).scalar_one()
    assert stored > 0


def test_a_feed_disallowed_by_robots_is_not_requested_and_the_run_fails(clean_db):
    seed_catalog(clean_db)
    routes = sample_routes()
    routes["https://news.example.com/robots.txt"] = b"User-agent: *\nDisallow: /rss\n"
    fetcher = FakeFetcher(routes)
    collector = Collector(clean_db, fetcher, adapters(), RobotsPolicy(fetcher))
    (news,) = [s for s in collector.sources() if s.slug == "sample-news"]

    result = collector.run(news)

    assert result.status == "failed" and "robots.txt: Disallow /rss" in result.error
    assert "https://news.example.com/rss" not in feed_requests(fetcher)
    assert contents(clean_db, "sample-news") == 0
