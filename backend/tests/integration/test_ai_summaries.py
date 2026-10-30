"""E1 AI summaries wired end to end: synthetic feeds -> collector -> summary job (fake LLM)
-> content_summaries -> Home/Dev API. Article bodies are the synthetic E1 test articles;
nothing leaves the process.
"""

import copy

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import text

from app.content_loader.taxonomy import SourcesFile
from app.integrations.llm import LLMError, LLMResponse
from app.jobs.summarize import MAX_ATTEMPTS, summarize_contents
from app.jobs.translate import translate_news
from app.main import create_app
from app.summaries.policy import Budget
from tests.collect_helpers import SOURCES, collect_all, seed_catalog
from tests.integration.test_translations import Translator, routes
from tests.integration.test_translations import sources as translation_sources
from tests.summary_helpers import DEV_SPRING, NEWS_KO, article

pytestmark = pytest.mark.integration

NEWS_URL = "https://news.example.com/articles/1"  # stored without the utm_* parameters
SHORT_URL = "https://news.example.com/articles/2"
BLOG_URL = "https://blog.example.com/posts/k8s-spring"
EN_URL = "https://en-news.example.com/articles/n3-delay"

BODIES = {
    NEWS_URL: ("html", article("news_ko.html")),
    SHORT_URL: ("html", article("short.html")),  # too short: never sent to the model
    BLOG_URL: ("html", article("dev_spring.html")),
    EN_URL: ("html", article("news_en.html")),
}


def bodies(item):
    return BODIES.get(item.url)


class Model:
    """Fake model: a News or Dev answer depending on the prompt, or an error."""

    model = "fake-summarizer"

    def __init__(self, error: LLMError | None = None):
        self.error, self.requests = error, []

    def complete(self, request):
        self.requests.append(request)
        if self.error:
            raise self.error
        if "기술 블로그" in request.system:
            return LLMResponse(_json(DEV_SPRING))
        return LLMResponse(_json(NEWS_KO))


def _json(data):
    import json

    return json.dumps(data, ensure_ascii=False)


def sources(on: bool = True) -> dict:
    data = copy.deepcopy(translation_sources())
    for source in data["sources"]:
        if source["slug"] in ("sample-news", "sample-blog", "sample-en"):
            source["ai_summary"] = on
    return data


@pytest.fixture()
def engine(clean_db):
    seed_catalog(clean_db, sources=sources())
    collect_all(clean_db, routes())
    return clean_db


@pytest.fixture()
def settings(integration_settings):
    return integration_settings


def get(settings, path):
    with TestClient(create_app(settings)) as client:
        return client.get(path, params={"size": 50}).json()["items"]


def by_url(items):
    return {i["url"]: i for i in items}


def rows(engine, sql):
    with engine.connect() as connection:
        return [tuple(r) for r in connection.execute(text(sql))]


def test_only_news_and_blog_sources_may_turn_summaries_on():
    data = copy.deepcopy(SOURCES)
    data["sources"][2]["ai_summary"] = True  # hackernews: community
    with pytest.raises(ValidationError, match="ai_summary is only for news and blog sources"):
        SourcesFile.model_validate(data)


def test_news_and_dev_summaries_are_stored_and_served(engine, settings):
    before = rows(engine, "SELECT id, title, excerpt, summary, summary_status FROM contents")
    model = Model()
    result = summarize_contents(engine, model, bodies)

    assert (result.done, result.failed, result.skipped) == (3, 0, 1)
    assert result.calls == 3 and len(model.requests) == 3  # the short article made no call
    assert (
        rows(engine, "SELECT id, title, excerpt, summary, summary_status FROM contents") == before
    )
    assert sorted(rows(engine, "SELECT kind, status, skip_reason FROM content_summaries")) == [
        ("dev", "done", None),
        ("news", "done", None),
        ("news", "done", None),
        ("news", "skipped", "insufficient_input"),
    ]

    news = by_url(get(settings, "/api/news"))
    summary = news[NEWS_URL]["ai_summary"]
    assert summary["kind"] == "news" and summary["partial_input"] is False
    assert summary["content"]["what_happened"] == NEWS_KO["what_happened"]
    assert "key_concepts" not in summary["content"]
    assert news[SHORT_URL]["ai_summary"] is None  # skipped: the card stays as it was
    assert news["https://news.example.com/articles/3"]["ai_summary"] is None  # no body
    assert news["https://en-plain.example.com/articles/n3-delay"]["ai_summary"] is None  # off

    blog = by_url(get(settings, "/api/dev/channels/kr-techblog/posts"))[BLOG_URL]["ai_summary"]
    assert blog["kind"] == "dev"
    assert blog["content"]["implementation"]["steps"] == DEV_SPRING["implementation"]["steps"]
    assert "what_happened" not in blog["content"]
    assert all(i["ai_summary"] is None for i in get(settings, "/api/dev/channels/devto/posts"))


def test_a_second_run_reuses_stored_summaries_and_they_survive_a_restart(engine, settings):
    summarize_contents(engine, Model(), bodies)
    again = Model()
    result = summarize_contents(engine, again, bodies)

    assert result.calls == 0 and again.requests == [] and result.kept == 4
    # A new app instance (a server restart) reads the same stored summaries.
    for _ in range(2):
        assert by_url(get(settings, "/api/news"))[NEWS_URL]["ai_summary"]["kind"] == "news"


def test_failures_keep_the_plain_card_and_are_retried_up_to_the_limit(engine, settings):
    for _ in range(MAX_ATTEMPTS):
        result = summarize_contents(
            engine, Model(LLMError("server")), bodies, Budget(max_calls=100)
        )
        assert result.failed == 3
    news = by_url(get(settings, "/api/news"))
    assert news[NEWS_URL]["ai_summary"] is None and news[NEWS_URL]["excerpt"]
    assert rows(
        engine, "SELECT DISTINCT attempts FROM content_summaries WHERE status = 'failed'"
    ) == [(MAX_ATTEMPTS,)]
    assert summarize_contents(engine, Model(), bodies).calls == 0


def test_a_changed_body_is_summarized_again(engine):
    summarize_contents(engine, Model(), bodies)
    changed = dict(BODIES)
    changed[NEWS_URL] = ("html", article("news_ko.html").replace("1,200개", "1,300개"))
    model = Model()
    summarize_contents(engine, model, lambda item: changed.get(item.url))
    assert len(model.requests) == 1


def test_turning_a_source_off_hides_its_summaries(engine, settings):
    summarize_contents(engine, Model(), bodies)
    seed_catalog(engine, sources=sources(on=False))

    assert all(i["ai_summary"] is None for i in get(settings, "/api/news"))
    assert summarize_contents(engine, Model(), bodies).calls == 0


def test_summary_and_translation_live_side_by_side(engine, settings):
    translate_news(engine, Translator())
    summarize_contents(engine, Model(), bodies)
    item = by_url(get(settings, "/api/news"))[EN_URL]

    assert item["title"].startswith("Nimbus delays")  # original kept
    assert item["translation"]["title"].startswith("Nimbus, N3")
    assert item["ai_summary"]["kind"] == "news"


def test_the_call_budget_stops_the_run(engine):
    result = summarize_contents(engine, Model(), bodies, Budget(max_calls=1))
    assert (result.done, result.stopped) == (1, "budget_exhausted")
