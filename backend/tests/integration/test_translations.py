"""Korean AI translation of English news: collect -> translate (fake LLM) -> store -> News API.

All feeds are synthetic files and the model is a scripted fake; nothing leaves the process.
"""

import copy
import re

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import text

from app.content_loader.taxonomy import SourcesFile
from app.integrations.llm import LLMError, LLMResponse
from app.jobs.translate import MAX_ATTEMPTS, translate_news
from app.main import create_app
from app.summaries.policy import Budget
from tests.collect_helpers import SOURCES, collect_all, fixture, sample_routes, seed_catalog

pytestmark = pytest.mark.integration

EN_FEED = "https://en-news.example.com/rss"
EN_PLAIN_FEED = "https://en-plain.example.com/rss"

KOREAN = {
    "Nimbus delays its N3 AI accelerator to 2027": (
        "Nimbus, N3 AI 가속기 출시를 2027년으로 연기",
        "Nimbus Silicon은 N3 칩을 2026년 말이 아닌 2027년 2분기에 출시한다고 밝혔다.",
    ),
    "DevCloud launches a managed vector database in Seoul": (
        "DevCloud, 서울에서 관리형 벡터 데이터베이스 출시",
        "이 서비스는 하이브리드 검색을 지원하며 데이터를 서울 리전에 보관한다.",
    ),
    "Python 3.14 ships with a free-threaded build": (
        "Python 3.14, free-threaded 빌드와 함께 출시",
        None,
    ),
}


def sources(translate_on: bool = True) -> dict:
    data = copy.deepcopy(SOURCES)
    data["sources"] += [
        {
            "slug": "sample-en",
            "name": "Sample EN",
            "kind": "news",
            "adapter": "rss",
            "language": "en",
            "site_url": "https://en-news.example.com/",
            "feed_url": EN_FEED,
            "ai_translation": translate_on,
        },
        {  # English too, but its terms were never checked: no translation.
            "slug": "sample-en-plain",
            "name": "Sample EN Plain",
            "kind": "news",
            "adapter": "rss",
            "language": "en",
            "site_url": "https://en-plain.example.com/",
            "feed_url": EN_PLAIN_FEED,
        },
    ]
    return data


def routes(feed: bytes | None = None) -> dict:
    r = sample_routes()
    r[EN_FEED] = feed or fixture("news_en.rss.xml")
    r[EN_PLAIN_FEED] = fixture("news_en.rss.xml").replace(
        b"en-news.example.com", b"en-plain.example.com"
    )
    return r


class Translator:
    """Fake model: answers from KOREAN by the title in the request, or raises."""

    model = "fake-translator"

    def __init__(self, error: LLMError | None = None, override: str | None = None):
        self.error, self.override, self.requests = error, override, []

    def complete(self, request):
        self.requests.append(request)
        if self.error:
            raise self.error
        if self.override is not None:
            return LLMResponse(self.override)
        title = re.search(r"<title>(.*)</title>", request.user).group(1)
        ko_title, ko_excerpt = KOREAN[title]
        excerpt = "null" if ko_excerpt is None else f'"{ko_excerpt}"'
        return LLMResponse(f'{{"title": "{ko_title}", "excerpt": {excerpt}}}')


@pytest.fixture()
def engine(clean_db):
    seed_catalog(clean_db, sources=sources())
    collect_all(clean_db, routes())
    return clean_db


@pytest.fixture()
def api(engine, integration_settings):
    with TestClient(create_app(integration_settings)) as client:
        yield client


def news(api) -> dict[str, dict]:
    return {i["url"]: i for i in api.get("/api/news", params={"size": 50}).json()["items"]}


def rows(engine, sql):
    with engine.connect() as connection:
        return [tuple(r) for r in connection.execute(text(sql))]


def test_only_english_news_may_turn_translation_on():
    for override in ({"language": "ko"}, {"kind": "blog", "channel": "c", "channel_name": "C"}):
        data = sources()
        data["sources"][-2] |= override
        with pytest.raises(ValidationError, match="ai_translation is only for English news"):
            SourcesFile.model_validate(data)


def test_translations_are_stored_apart_and_shown_on_news(engine, api):
    before = rows(engine, "SELECT id, title, excerpt FROM contents ORDER BY id")
    result = translate_news(engine, Translator())

    assert (result.done, result.failed, result.calls) == (3, 0, 3)
    # The originals are untouched; the translations live in their own table.
    assert rows(engine, "SELECT id, title, excerpt FROM contents ORDER BY id") == before
    assert rows(
        engine, "SELECT COUNT(*), MIN(status), MAX(attempts) FROM content_translations"
    ) == [(3, "done", 1)]

    items = news(api)
    n3 = items["https://en-news.example.com/articles/n3-delay"]
    assert n3["title"] == "Nimbus delays its N3 AI accelerator to 2027"  # original kept
    assert n3["translation"] == {
        "language": "ko",
        "title": "Nimbus, N3 AI 가속기 출시를 2027년으로 연기",
        "excerpt": "Nimbus Silicon은 N3 칩을 2026년 말이 아닌 2027년 2분기에 출시한다고 밝혔다.",
    }
    assert (
        items["https://en-news.example.com/articles/python-314"]["translation"]["excerpt"] is None
    )
    # Korean news and the source without permission are shown as they are.
    assert items["https://news.example.com/articles/1"]["translation"] is None
    assert items["https://en-plain.example.com/articles/n3-delay"]["translation"] is None
    # Dev lists never carry translations.
    devto = api.get("/api/dev/channels/devto/posts").json()["items"]
    assert devto and all(i["translation"] is None for i in devto)


def test_a_second_run_and_repeated_reads_make_no_new_calls(engine, api):
    translate_news(engine, Translator())
    for _ in range(3):
        news(api)
    again = Translator()
    assert translate_news(engine, again).calls == 0 and again.requests == []


@pytest.mark.parametrize(
    ("translator", "code"),
    [
        (Translator(error=LLMError("server")), "server"),
        (Translator(error=LLMError("rate_limited", retry_after=5)), "rate_limited"),
        (Translator(override="not json"), "invalid_answer"),
        (Translator(override='{"title": "Nimbus delays N3"}'), "not_translated"),
        (
            Translator(override='{"title": "N3 출시 2028년으로 연기", "excerpt": "2028년"}'),
            "unsupported_number",
        ),
    ],
)
def test_failures_keep_the_english_original(engine, api, translator, code):
    result = translate_news(engine, translator)

    assert result.failed == 3 and result.done == 0
    assert {r[0] for r in rows(engine, "SELECT error_code FROM content_translations")} == {code}
    n3 = news(api)["https://en-news.example.com/articles/n3-delay"]
    assert n3["translation"] is None and n3["title"].startswith("Nimbus delays")


def test_failed_items_are_retried_up_to_the_limit_then_left_alone(engine):
    for _ in range(MAX_ATTEMPTS):
        assert translate_news(engine, Translator(error=LLMError("timeout"))).calls == 3
    assert rows(engine, "SELECT DISTINCT attempts FROM content_translations") == [(MAX_ATTEMPTS,)]
    assert translate_news(engine, Translator()).calls == 0


def test_a_changed_article_hides_the_old_translation_until_it_is_redone(engine, api):
    translate_news(engine, Translator())
    changed = fixture("news_en.rss.xml").replace(
        b"Nimbus delays its N3 AI accelerator to 2027",
        b"DevCloud launches a managed vector database in Seoul",
    )
    collect_all(engine, routes(changed))  # the feed now gives the N3 item another title

    assert news(api)["https://en-news.example.com/articles/n3-delay"]["translation"] is None
    redo = Translator()
    assert translate_news(engine, redo).calls == 1
    assert news(api)["https://en-news.example.com/articles/n3-delay"]["translation"][
        "title"
    ].startswith("DevCloud")


def test_turning_the_source_off_hides_translations_and_stops_the_job(engine, api):
    translate_news(engine, Translator())
    seed_catalog(engine, sources=sources(translate_on=False))

    assert all(i["translation"] is None for i in news(api).values())
    blocked = Translator()
    assert translate_news(engine, blocked).calls == 0


def test_the_call_budget_stops_the_run(engine):
    result = translate_news(engine, Translator(), Budget(max_calls=1))
    assert (result.done, result.calls, result.stopped) == (1, 1, "budget_exhausted")
