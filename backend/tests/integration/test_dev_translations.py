"""Korean title translations for Dev (web.dev): job -> content_translations -> Dev APIs.

Synthetic web.dev-shaped feed through the fake collector and a fake model; nothing leaves
the process. News translation keeps its own tests (test_translations.py).
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.types import utc_now
from app.integrations.llm import LLMError, LLMResponse
from app.jobs.translate import translate_news
from app.main import create_app
from app.models.content import ContentSummary
from tests.collect_helpers import collect_all, sample_routes, seed_catalog
from tests.summary_helpers import DEV_SPRING
from tests.webdev_helpers import FEED_URL, FIRST, FIRST_TITLE, SECOND, sources

pytestmark = pytest.mark.integration

FEED = (Path(__file__).parents[1] / "fixtures" / "webdev" / "feed.rss.xml").read_bytes()
KOREAN = {
    FIRST_TITLE: "샘플 Spring 서비스의 가상 스레드",
    "A second sample post": "두 번째 샘플 글",
}


class Translator:
    model = "fake-translator"

    def __init__(self, fail: set[str] = frozenset()):
        self.fail, self.titles = fail, []

    def complete(self, request):
        title = request.user.split("<title>")[1].split("</title>")[0]
        self.titles.append(title)
        if title in self.fail:
            raise LLMError("server")
        return LLMResponse(f'{{"title": "{KOREAN[title]}", "excerpt": "합성 소개문입니다."}}')


@pytest.fixture()
def engine(clean_db):
    seed_catalog(clean_db, sources=sources())  # web.dev exactly as content/sources.yaml has it
    routes = sample_routes()
    routes[FEED_URL] = FEED
    collect_all(clean_db, routes)
    return clean_db


def get(settings, path):
    with TestClient(create_app(settings)) as client:
        return {i["url"]: i for i in client.get(path, params={"size": 50}).json()["items"]}


def test_web_dev_titles_are_translated_and_shown_on_every_dev_list(engine, integration_settings):
    model = Translator()
    result = translate_news(engine, model)
    # Only web.dev: Korean sources and English sources without the switch are left alone.
    assert sorted(model.titles) == sorted(KOREAN) and result.done == 2

    board = get(integration_settings, "/api/dev/channels/webdev/posts")
    assert board[FIRST]["title"] == FIRST_TITLE  # the original stays
    assert board[FIRST]["translation"]["title"] == KOREAN[FIRST_TITLE]
    assert get(integration_settings, "/api/dev/articles")[SECOND]["translation"]["title"] == (
        "두 번째 샘플 글"
    )
    devto = get(integration_settings, "/api/dev/channels/devto/posts")
    assert all(i["translation"] is None for i in devto.values())  # English blog, switch off

    with engine.connect() as connection:
        first_id = connection.execute(
            text("SELECT id FROM contents WHERE url = :u"), {"u": FIRST}
        ).scalar_one()
    with Session(engine) as db, db.begin():
        db.add(
            ContentSummary(
                content_id=first_id,
                kind="dev",
                status="done",
                payload=dict(DEV_SPRING),
                input_hash="0" * 64,
                prompt_version="dev-e1.1",
                attempts=1,
                updated_at=utc_now(),
            )
        )
    featured = get(integration_settings, "/api/dev/featured")[FIRST]
    assert featured["translation"]["title"] == KOREAN[FIRST_TITLE]
    assert featured["ai_summary"]["kind"] == "dev"


def test_stored_translations_are_reused(engine):
    translate_news(engine, Translator())
    again = Translator()
    assert translate_news(engine, again).calls == 0 and again.titles == []


def test_a_failed_translation_falls_back_to_the_original(engine, integration_settings):
    result = translate_news(engine, Translator(fail={FIRST_TITLE}))
    assert (result.done, result.failed) == (1, 1)
    board = get(integration_settings, "/api/dev/channels/webdev/posts")
    assert board[FIRST]["translation"] is None and board[FIRST]["title"] == FIRST_TITLE
    assert board[SECOND]["translation"]["title"] == "두 번째 샘플 글"
