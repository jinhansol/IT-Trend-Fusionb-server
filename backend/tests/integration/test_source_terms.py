"""Source terms in practice: what is saved, what is shown, and robots.txt in a real run
(including a redirect of the feed), and that AI summaries need approved terms too."""

import copy

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app.db.session import create_session_factory
from app.integrations.http import HttpFetcher
from app.integrations.robots import RobotsPolicy
from app.integrations.sources import adapters
from app.jobs.runner import Collector
from app.main import create_app
from app.models.content import ContentSource
from app.services.source_terms import ai_summary_allowed, allows_ai_summary
from tests.collect_helpers import (
    SOURCES,
    FakeFetcher,
    collect_all,
    feed_requests,
    fixture,
    sample_routes,
    seed_catalog,
)
from tests.conftest import make_settings
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

    # Terms approved for title and link only: the description is no longer returned,
    # and the next run stops keeping it. Tags (matched on the feed text) stay the same.
    tags_before = tags(clean_db)
    seed_catalog(clean_db, sources=catalog(terms="approved"))
    items = news_items(integration_settings)
    assert items and all(i["excerpt"] is None for i in items)
    assert all(i["title"] and i["url"] and i["source"]["slug"] for i in items)

    collect_all(clean_db)
    assert stored_excerpts(clean_db, "sample-news") == 0
    assert stored_excerpts(clean_db, "sample-blog") > 0  # excerpt: true in the catalog
    assert tags(clean_db) == tags_before and tags_before


def stored_excerpts(engine, slug: str) -> int:
    with engine.connect() as connection:
        return connection.execute(
            text(
                "SELECT COUNT(*) FROM contents c JOIN content_sources s ON s.id = c.source_id "
                "WHERE s.slug = :slug AND c.excerpt IS NOT NULL"
            ),
            {"slug": slug},
        ).scalar_one()


def tags(engine) -> set[tuple[str, int]]:
    with engine.connect() as connection:
        return set(
            connection.execute(
                text(
                    "SELECT c.url, t.technology_id FROM content_technologies t "
                    "JOIN contents c ON c.id = t.content_id"
                )
            ).all()
        )


def test_a_title_only_source_never_stores_the_description(clean_db):
    seed_catalog(clean_db, sources=catalog(terms="approved"))
    collect_all(clean_db)
    assert contents(clean_db, "sample-news") > 0
    assert stored_excerpts(clean_db, "sample-news") == 0


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


def test_a_redirect_into_a_disallowed_path_fails_the_run_without_requesting_it(clean_db):
    seed_catalog(clean_db)
    requested: list[str] = []

    def site(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        requested.append(url)
        if url == "https://news.example.com/rss":
            return httpx.Response(301, headers={"location": "https://news.example.com/members/rss"})
        if url == "https://news.example.com/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /members/\n")
        return httpx.Response(200, content=fixture("news.rss.xml"))

    fetcher = HttpFetcher(make_settings(), httpx.MockTransport(site), sleep=lambda s: None)
    collector = Collector(clean_db, fetcher, adapters(), RobotsPolicy(fetcher))
    (news,) = [s for s in collector.sources() if s.slug == "sample-news"]

    result = collector.run(news)

    assert result.status == "failed" and "Disallow /members/" in result.error
    assert "https://news.example.com/members/rss" not in requested
    assert contents(clean_db, "sample-news") == 0


def test_ai_summary_without_approved_terms_is_never_selected(clean_db):
    data = catalog(terms="approved")
    data["sources"][0]["ai_summary"] = True
    seed_catalog(clean_db, sources=data)
    with create_session_factory(clean_db)() as db:
        allowed = select(ContentSource.slug).where(ai_summary_allowed())
        assert list(db.scalars(allowed)) == ["sample-news"]
        # A row from before the terms option (or edited by hand): ai_summary alone is
        # not enough for the summary job, the featured list or the cards.
        db.execute(text("UPDATE content_sources SET options = '{}' WHERE slug = 'sample-news'"))
        db.commit()
        assert list(db.scalars(allowed)) == []
        news = db.scalar(select(ContentSource).where(ContentSource.slug == "sample-news"))
        assert news.ai_summary and not allows_ai_summary(news)
