"""python -m app.jobs translate|summarize with Gemini, end to end against the test database.

google.genai.Client is replaced by a fake that answers like Gemini, so the command line,
the settings, the Gemini client and the jobs run as they would; nothing leaves the process.
"""

import json
import re

import pytest
from fastapi.testclient import TestClient
from google.genai import types
from pydantic import SecretStr
from sqlalchemy import text

import app.integrations.gemini as gemini_module
from app.jobs import __main__ as cli
from app.main import create_app
from tests.collect_helpers import collect_all, seed_catalog
from tests.integration.test_ai_summaries import BLOG_URL, EN_URL, NEWS_URL
from tests.integration.test_ai_summaries import sources as summary_sources
from tests.integration.test_translations import KOREAN, routes
from tests.summary_helpers import DEV_SPRING, NEWS_KO

pytestmark = pytest.mark.integration

KEY = "test-key-not-real-0123456789"
FIXTURES = "tests/fixtures/summaries"


def reply(data) -> types.GenerateContentResponse:
    body = json.dumps(data, ensure_ascii=False)
    return types.GenerateContentResponse.model_validate(
        {
            "candidates": [{"content": {"role": "model", "parts": [{"text": body}]}}],
            "usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": 40},
        }
    )


class FakeGemini:
    """Stands in for google.genai.Client; answers by the prompt, or raises."""

    created: list[dict] = []
    requests: list[dict] = []
    error: Exception | None = None

    def __init__(self, **kwargs):
        FakeGemini.created.append(kwargs)
        self.models = self

    def generate_content(self, *, model, contents, config):
        FakeGemini.requests.append({"model": model, "contents": contents})
        if FakeGemini.error:
            raise FakeGemini.error
        if "번역기" in config.system_instruction:
            ko_title, ko_excerpt = KOREAN[re.search(r"<title>(.*)</title>", contents).group(1)]
            return reply({"title": ko_title, "excerpt": ko_excerpt})
        if "기술 블로그" in config.system_instruction:
            return reply(DEV_SPRING)
        return reply(NEWS_KO)


@pytest.fixture()
def engine(clean_db):
    seed_catalog(clean_db, sources=summary_sources())
    collect_all(clean_db, routes())
    return clean_db


@pytest.fixture()
def run(engine, integration_settings, monkeypatch):
    FakeGemini.created, FakeGemini.requests, FakeGemini.error = [], [], None
    monkeypatch.setattr(gemini_module.genai, "Client", FakeGemini)

    def run(*argv, key=KEY):
        settings = integration_settings.model_copy(
            update={"gemini_api_key": SecretStr(key) if key else None}
        )
        monkeypatch.setattr(cli, "get_settings", lambda: settings)
        return cli.main(list(argv))

    return run


def rows(engine, sql):
    with engine.connect() as connection:
        return [tuple(r) for r in connection.execute(text(sql))]


def news(settings):
    with TestClient(create_app(settings)) as client:
        items = client.get("/api/news", params={"size": 50}).json()["items"]
    return {i["url"]: i for i in items}


def test_translate_stores_korean_titles_within_the_call_cap(run, engine, integration_settings):
    assert run("translate", "--max-calls", "2") == 0
    assert len(FakeGemini.requests) == 2  # three English items, two allowed calls
    assert FakeGemini.created[0]["api_key"] == KEY
    assert FakeGemini.requests[0]["model"] == "gemini-3.1-flash-lite"
    assert rows(engine, "SELECT COUNT(*), MIN(model) FROM content_translations") == [
        (2, "gemini-3.1-flash-lite")
    ]

    assert run("translate") == 0  # the third item; stored ones are reused
    assert len(FakeGemini.requests) == 3
    item = news(integration_settings)[EN_URL]
    assert item["title"].startswith("Nimbus delays") and item["translation"]["title"]


def test_summarize_reads_local_bodies_only(run, engine, integration_settings):
    bodies = [
        f"--body={NEWS_URL}={FIXTURES}/news_ko.html",
        f"--body={BLOG_URL}={FIXTURES}/dev_spring.html",
    ]
    assert run("summarize", *bodies) == 0
    assert len(FakeGemini.requests) == 2
    assert sorted(rows(engine, "SELECT kind, status FROM content_summaries")) == [
        ("dev", "done"),
        ("news", "done"),
    ]
    assert news(integration_settings)[NEWS_URL]["ai_summary"]["kind"] == "news"


def test_without_a_key_nothing_is_sent_or_saved(run, engine, capsys):
    assert run("translate", key=None) == 2
    assert run("summarize", f"--body={NEWS_URL}={FIXTURES}/news_ko.html", key=None) == 2
    assert "GEMINI_API_KEY is not set" in capsys.readouterr().err
    assert FakeGemini.created == [] and FakeGemini.requests == []
    assert rows(engine, "SELECT COUNT(*) FROM content_translations") == [(0,)]
    assert rows(engine, "SELECT COUNT(*) FROM content_summaries") == [(0,)]


def test_a_rejected_key_keeps_the_english_original(run, engine, integration_settings, capsys):
    from google.genai import errors

    FakeGemini.error = errors.ClientError(
        401, {"error": {"code": 401, "status": "UNAUTHENTICATED", "message": "bad key"}}
    )
    assert run("translate", "--max-calls", "4") == 1
    err = capsys.readouterr()
    assert "check GEMINI_API_KEY" in err.err and KEY not in err.out + err.err
    assert len(FakeGemini.requests) == 3  # not retried: one request per item
    assert rows(engine, "SELECT DISTINCT status, error_code, title FROM content_translations") == [
        ("failed", "bad_request", None)
    ]
    assert news(integration_settings)[EN_URL]["translation"] is None


def test_bad_arguments_stop_before_any_call(run, capsys):
    assert run("translate", "--max-calls", "0") == 2
    assert run("summarize", "--body", "https://x.example/a") == 2
    assert run("summarize", "--body", "https://x.example/a=missing.html") == 2
    assert FakeGemini.created == []
