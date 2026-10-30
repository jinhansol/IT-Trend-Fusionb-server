"""web.dev end to end without manual bodies: RSS collect -> article page -> summary (fake
Gemini) -> content_summaries -> Dev API with the license.

The feed and pages are synthetic web.dev-shaped files served by httpx.MockTransport through
the real HttpFetcher (host lock included); google.genai.Client is the fake from
test_gemini_jobs. Nothing leaves the process.
"""

from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import text

import app.integrations.gemini as gemini_module
import app.integrations.http as http_module
from app.integrations.http import HttpFetcher
from app.jobs import __main__ as cli
from app.main import create_app
from tests.collect_helpers import collect_all, sample_routes, seed_catalog
from tests.integration.test_gemini_jobs import KEY, FakeGemini
from tests.webdev_helpers import (
    FEED_URL,
    FIRST,
    FIRST_PAGE,
    FIRST_TITLE,
    SECOND_PAGE,
    SECOND_TITLE,
    page,
    sources,
)

pytestmark = pytest.mark.integration

FEED = (Path(__file__).parents[1] / "fixtures" / "webdev" / "feed.rss.xml").read_bytes()
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"


class Site:
    """The synthetic web.dev pages, by URL; anything else is a 404."""

    def __init__(self, pages: dict[str, bytes | int]):
        self.pages, self.requests = pages, []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(str(request.url))
        answer = self.pages.get(str(request.url), 404)
        if isinstance(answer, int):
            return httpx.Response(answer)
        return httpx.Response(200, content=answer)


PAGES = {
    FIRST_PAGE: page("sample-virtual-threads", FIRST_TITLE),
    SECOND_PAGE: page("sample-second-post", SECOND_TITLE),
}


@pytest.fixture()
def engine(clean_db):
    seed_catalog(clean_db, sources=sources())
    routes = sample_routes()
    routes[FEED_URL] = FEED
    collect_all(clean_db, routes)
    return clean_db


@pytest.fixture()
def run(engine, integration_settings, monkeypatch):
    FakeGemini.created, FakeGemini.requests, FakeGemini.error = [], [], None
    monkeypatch.setattr(gemini_module.genai, "Client", FakeGemini)
    resolved = []
    monkeypatch.setattr(http_module, "_behind_proxy", lambda: False)
    monkeypatch.setattr(http_module, "check_resolved", resolved.append)
    settings = integration_settings.model_copy(update={"gemini_api_key": SecretStr(KEY)})
    monkeypatch.setattr(cli, "get_settings", lambda: settings)

    def run(site: Site, *argv):
        def fetcher(settings, **kwargs):
            return HttpFetcher(settings, httpx.MockTransport(site), sleep=lambda s: None, **kwargs)

        monkeypatch.setattr(cli, "HttpFetcher", fetcher)
        return cli.main(["summarize", *argv])

    run.resolved = resolved
    return run


def rows(engine, sql):
    with engine.connect() as connection:
        return [tuple(r) for r in connection.execute(text(sql))]


def webdev_items(settings):
    with TestClient(create_app(settings)) as client:
        items = client.get("/api/dev/channels/webdev/posts").json()["items"]
    return {i["url"]: i for i in items}


def test_feed_items_are_summarized_from_their_pages(run, engine, integration_settings):
    site = Site(PAGES)
    assert run(site, "--max-calls", "4") == 0

    assert sorted(site.requests) == [SECOND_PAGE, FIRST_PAGE]  # the article pages only
    assert run.resolved and set(run.resolved) == {"web.dev"}
    assert len(FakeGemini.requests) == 2
    assert FIRST_TITLE in FakeGemini.requests[0]["contents"] + FakeGemini.requests[1]["contents"]
    assert sorted(rows(engine, "SELECT kind, status, model FROM content_summaries")) == [
        ("dev", "done", "gemini-3.1-flash-lite"),
        ("dev", "done", "gemini-3.1-flash-lite"),
    ]

    items = webdev_items(integration_settings)
    first = items[FIRST]
    assert first["title"] == FIRST_TITLE and first["url"] == FIRST  # original link kept
    assert first["ai_summary"]["kind"] == "dev"
    assert first["source"] == {
        "slug": "webdev",
        "name": "web.dev",
        "license": {"name": "CC BY 4.0", "url": LICENSE_URL},
    }


def test_a_second_run_fetches_and_calls_nothing(run):
    run(Site(PAGES))
    again = Site(PAGES)
    FakeGemini.requests.clear()
    assert run(again) == 0
    assert again.requests == [] and FakeGemini.requests == []


def test_the_call_cap_holds(run, engine):
    site = Site(PAGES)
    assert run(site, "--max-calls", "1") == 0
    assert len(FakeGemini.requests) == 1
    assert rows(engine, "SELECT COUNT(*) FROM content_summaries") == [(1,)]


@pytest.mark.parametrize(
    "pages",
    [
        {FIRST_PAGE: 404, SECOND_PAGE: 503},  # not fetched
        {FIRST_PAGE: page("sample-virtual-threads", FIRST_TITLE, license=False)},  # no license
        {FIRST_PAGE: page("sample-second-post", SECOND_TITLE)},  # another article's page
        {FIRST_PAGE: page("sample-virtual-threads", "Something else entirely")},  # title differs
    ],
)
def test_unusable_pages_send_nothing_and_keep_the_card(run, engine, integration_settings, pages):
    assert run(Site(pages)) == 0
    assert FakeGemini.requests == []
    assert rows(engine, "SELECT COUNT(*) FROM content_summaries") == [(0,)]
    first = webdev_items(integration_settings)[FIRST]
    assert first["ai_summary"] is None and first["excerpt"]  # the plain card


def test_other_sources_are_never_fetched(run, engine, integration_settings):
    site = Site(PAGES)
    run(site)
    assert all(url.startswith("https://web.dev/blog/") for url in site.requests)
    with TestClient(create_app(integration_settings)) as client:
        devto = client.get("/api/dev/channels/devto/posts").json()["items"]
        news = client.get("/api/news").json()["items"]
    assert all(i["ai_summary"] is None and i["source"]["license"] is None for i in devto + news)
