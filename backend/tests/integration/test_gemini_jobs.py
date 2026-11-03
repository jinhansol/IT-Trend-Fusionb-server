"""python -m app.jobs summarize with Gemini, end to end against the test database.

google.genai.Client is replaced by a fake that answers like Gemini, so the command line,
the settings, the Gemini client and the jobs run as they would; nothing leaves the process.
"""

import json

import pytest
from fastapi.testclient import TestClient
from google.genai import types
from pydantic import SecretStr
from sqlalchemy import text

import app.integrations.gemini as gemini_module
from app.jobs import __main__ as cli
from app.main import create_app
from tests.collect_helpers import collect_all, seed_catalog
from tests.integration.test_ai_summaries import BLOG_URL, NEWS_URL, routes
from tests.integration.test_ai_summaries import sources as summary_sources
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


def test_summarize_stays_within_the_call_cap(run, engine):
    bodies = [
        f"--body={NEWS_URL}={FIXTURES}/news_ko.html",
        f"--body={BLOG_URL}={FIXTURES}/dev_spring.html",
    ]
    assert run("summarize", "--max-calls", "1", *bodies) == 0
    assert len(FakeGemini.requests) == 1  # two bodies, one allowed call
    assert FakeGemini.created[0]["api_key"] == KEY
    assert FakeGemini.requests[0]["model"] == "gemini-3.1-flash-lite"
    assert rows(engine, "SELECT COUNT(*), MIN(model) FROM content_summaries") == [
        (1, "gemini-3.1-flash-lite")
    ]


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
    assert run("summarize", f"--body={NEWS_URL}={FIXTURES}/news_ko.html", key=None) == 2
    assert "GEMINI_API_KEY is not set" in capsys.readouterr().err
    assert FakeGemini.created == [] and FakeGemini.requests == []
    assert rows(engine, "SELECT COUNT(*) FROM content_summaries") == [(0,)]


def test_a_rejected_key_keeps_the_plain_card(run, engine, integration_settings, capsys):
    from google.genai import errors

    FakeGemini.error = errors.ClientError(
        401, {"error": {"code": 401, "status": "UNAUTHENTICATED", "message": "bad key"}}
    )
    assert run("summarize", f"--body={NEWS_URL}={FIXTURES}/news_ko.html") == 1
    err = capsys.readouterr()
    assert "check GEMINI_API_KEY" in err.err and KEY not in err.out + err.err
    assert len(FakeGemini.requests) == 1  # not retried
    assert rows(engine, "SELECT status, error_code FROM content_summaries") == [
        ("failed", "bad_request")
    ]
    item = news(integration_settings)[NEWS_URL]
    assert item["ai_summary"] is None and item["excerpt"]


def test_bad_arguments_stop_before_any_call(run, capsys):
    assert run("summarize", "--max-calls", "0") == 2
    assert run("summarize", "--body", "https://x.example/a") == 2
    assert run("summarize", "--body", "https://x.example/a=missing.html") == 2
    assert FakeGemini.created == []
