"""Dev featured articles (top of Dev) and the board that leaves them out.

Synthetic feeds through the fake collector; summaries are stored rows (no model call).
"""

import copy
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, text
from sqlalchemy.orm import Session

from app.db.types import utc_now
from app.main import create_app
from app.models.content import ContentSummary
from tests.collect_helpers import collect_all, sample_routes, seed_catalog
from tests.summary_helpers import DEV_SPRING
from tests.webdev_helpers import FEED_URL
from tests.webdev_helpers import sources as webdev_sources

pytestmark = pytest.mark.integration

FEED = (Path(__file__).parents[1] / "fixtures" / "webdev" / "feed.rss.xml").read_bytes()


def catalog() -> dict:
    data = copy.deepcopy(webdev_sources())
    for source in data["sources"]:
        if source["slug"] == "sample-blog":
            # A license field without the reviewed ai_summary switch: never featured.
            source["options"] = {"license": "CC-BY-4.0"}
    return data


@pytest.fixture()
def app_client(clean_db, integration_settings):
    seed_catalog(clean_db, sources=catalog())
    routes = sample_routes()
    routes[FEED_URL] = FEED
    collect_all(clean_db, routes)
    application = create_app(integration_settings)
    with TestClient(application) as client:
        yield client, application


def ids(engine, slug):
    with engine.connect() as connection:
        return list(
            connection.execute(
                text(
                    "SELECT c.id FROM contents c JOIN content_sources s ON s.id = c.source_id "
                    "WHERE s.slug = :slug ORDER BY c.sort_at DESC, c.id DESC"
                ),
                {"slug": slug},
            ).scalars()
        )


def summarize(engine, content_ids, status="done"):
    with Session(engine) as db, db.begin():
        for content_id in content_ids:
            db.add(
                ContentSummary(
                    content_id=content_id,
                    kind="dev",
                    status=status,
                    payload=dict(DEV_SPRING) if status == "done" else None,
                    input_hash="0" * 64,
                    prompt_version="dev-e1.1",
                    attempts=1,
                    updated_at=utc_now(),
                )
            )


def featured(client):
    return client.get("/api/dev/featured").json()["items"]


def test_no_summary_means_no_featured_articles(app_client):
    client, _ = app_client
    assert featured(client) == []


def test_one_or_two_newest_summarized_articles_are_featured(app_client, clean_db):
    client, _ = app_client
    webdev = ids(clean_db, "webdev")
    assert len(webdev) == 2
    summarize(clean_db, webdev[1:])
    one = featured(client)
    assert [i["id"] for i in one] == webdev[1:]
    assert one[0]["ai_summary"]["kind"] == "dev"
    assert one[0]["source"]["license"]["name"] == "CC BY 4.0"

    summarize(clean_db, webdev[:1])
    assert [i["id"] for i in featured(client)] == webdev  # newest first, at most two


def test_only_sources_with_the_reviewed_summary_switch_are_featured(app_client, clean_db):
    client, _ = app_client
    summarize(clean_db, ids(clean_db, "sample-blog"))  # licensed, but ai_summary is off
    summarize(clean_db, ids(clean_db, "webdev")[:1], status="failed")
    assert featured(client) == []


def test_the_board_leaves_featured_articles_out_and_pages_stay_exact(app_client, clean_db):
    client, _ = app_client
    webdev = ids(clean_db, "webdev")
    summarize(clean_db, webdev[:1])
    url = "/api/dev/channels/webdev/posts"

    plain = client.get(url).json()
    board = client.get(url, params={"exclude_featured": True}).json()
    assert plain["total"] == 2 and board["total"] == 1
    assert [i["id"] for i in board["items"]] == webdev[1:]

    # Page by page (size 1): every remaining article once, none of the featured ones.
    seen = []
    for page in (1, 2):
        body = client.get(url, params={"exclude_featured": True, "size": 1, "page": page}).json()
        seen += [i["id"] for i in body["items"]]
    assert seen == webdev[1:]

    # Other channels are untouched by the flag.
    devto = client.get("/api/dev/channels/devto/posts", params={"exclude_featured": True})
    assert devto.json()["total"] == 3


def test_featured_reads_never_write(app_client, clean_db):
    client, application = app_client
    summarize(clean_db, ids(clean_db, "webdev"))
    writes = []

    def record(conn, cursor, statement, *args):
        if statement.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE")):
            writes.append(statement)

    event.listen(application.state.engine, "before_cursor_execute", record)
    try:
        assert client.get("/api/dev/featured").status_code == 200
        assert client.get("/api/dev/channels/webdev/posts?exclude_featured=true").status_code == 200
    finally:
        event.remove(application.state.engine, "before_cursor_execute", record)
    assert writes == []
