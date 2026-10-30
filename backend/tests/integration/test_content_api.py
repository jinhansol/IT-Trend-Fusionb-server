"""Home/Dev read API against the MariaDB test database (data from the fake collector)."""

import re
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, text

from app.db.types import utc_now
from app.main import create_app
from tests.collect_helpers import collect_all, sample_routes, seed_catalog

pytestmark = pytest.mark.integration

Z_TIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$")


def shift_dates_to_now(engine) -> None:
    """Sample files carry fixed dates; move them so the newest item is one hour old."""
    with engine.begin() as connection:
        newest = connection.execute(text("SELECT MAX(published_at) FROM contents")).scalar_one()
        seconds = int((utc_now() - timedelta(hours=1) - newest).total_seconds())
        connection.execute(
            text("UPDATE contents SET published_at = published_at + INTERVAL :s SECOND"),
            {"s": seconds},
        )


@pytest.fixture()
def app_client(clean_db, integration_settings):
    application = create_app(integration_settings)
    with TestClient(application) as client:
        yield client, application


@pytest.fixture()
def client(app_client, clean_db):
    seed_catalog(clean_db)
    collect_all(clean_db)
    shift_dates_to_now(clean_db)
    return app_client[0]


def test_news_lists_only_news_newest_first(client):
    body = client.get("/api/news", params={"size": 2}).json()

    assert body["total"] == 3 and body["page"] == 1 and len(body["items"]) == 2
    first = body["items"][0]
    assert first["source"] == {"slug": "sample-news", "name": "Sample News", "license": None}
    assert first["score"] is None and first["comment_count"] is None
    assert Z_TIME.match(first["collected_at"])
    sort_keys = [i["published_at"] or i["collected_at"] for i in body["items"]]
    assert sort_keys == sorted(sort_keys, reverse=True)

    page2 = client.get("/api/news", params={"size": 2, "page": 2}).json()
    assert len(page2["items"]) == 1

    python_only = client.get("/api/news", params={"tech": "python"}).json()
    assert [i["title"] for i in python_only["items"]] == [
        '파이썬 3.14 출시, "free-threaded" 정식 지원'
    ]
    assert python_only["items"][0]["technologies"] == [{"slug": "python", "name": "Python"}]


def test_channels_follow_the_sources_file_order(client):
    items = client.get("/api/dev/channels").json()["items"]
    assert [(c["slug"], c["has_metrics"]) for c in items] == [
        ("devto", True),
        ("hackernews", True),
        ("stackoverflow", True),
        ("kr-techblog", False),
    ]
    assert items[3]["sources"] == [{"slug": "sample-blog", "name": "Sample Blog"}]


def test_channel_posts_latest_and_popular(client, clean_db):
    latest = client.get("/api/dev/channels/devto/posts").json()
    assert latest["total"] == 3
    popular = client.get("/api/dev/channels/devto/posts", params={"sort": "popular"}).json()
    assert [i["score"] for i in popular["items"]] == [250, 42, 3]

    # Popular only looks at the chosen period.
    with clean_db.begin() as connection:
        connection.execute(
            text(
                "UPDATE contents SET published_at = published_at - INTERVAL 10 DAY "
                "WHERE external_id = '1003'"
            )
        )
    week = client.get("/api/dev/channels/devto/posts", params={"sort": "popular", "days": 7})
    assert [i["score"] for i in week.json()["items"]] == [42, 3]

    questions = client.get("/api/dev/channels/stackoverflow/posts").json()["items"]
    assert {(q["score"], q["comment_count"], q["view_count"]) for q in questions} == {
        (27, 3, 1520),
        (0, 0, 40),
    }


def test_channel_errors(client):
    feed_only = client.get("/api/dev/channels/kr-techblog/posts", params={"sort": "popular"})
    assert feed_only.status_code == 422
    assert feed_only.json()["error"]["code"] == "SORT_NOT_SUPPORTED"
    assert client.get("/api/dev/channels/kr-techblog/posts").json()["total"] == 1

    missing = client.get("/api/dev/channels/nope/posts")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "CHANNEL_NOT_FOUND"
    assert client.get("/api/news", params={"tech": "Bad Slug"}).status_code == 422


def test_trends_count_fields_and_technologies(client):
    news = client.get("/api/trends", params={"scope": "news", "days": 7}).json()
    assert news["total"] == 3
    assert news["fields"] == [{"slug": "security", "name": "보안", "count": 1}]
    assert {(t["slug"], t["count"]) for t in news["technologies"]} == {
        ("javascript", 1),
        ("python", 1),
    }
    assert len(news["daily"]) == 7
    assert sum(d["total"] for d in news["daily"]) == 3
    assert news["daily"][-1]["date"] == str(utc_now().date())

    dev = client.get("/api/trends", params={"scope": "dev"}).json()
    assert dev["technologies"][0]["slug"] in {"python", "javascript", "java"}
    assert dev["daily_technologies"] and all(
        set(d["counts"]) == {t["slug"] for t in dev["daily_technologies"]} for d in dev["daily"]
    )


def test_feed_status_before_and_after_collection(app_client, clean_db):
    client, _ = app_client
    seed_catalog(clean_db)
    before = client.get("/api/feed-status", params={"scope": "news"}).json()
    assert before["last_updated_at"] is None and before["stale"] is True

    routes = sample_routes()
    routes["https://blog.example.com/atom"] = b"<html>down</html>"
    collect_all(clean_db, routes)

    news = client.get("/api/feed-status", params={"scope": "news"}).json()
    assert news["stale"] is False and Z_TIME.match(news["last_updated_at"])
    dev = {s["slug"]: s for s in client.get("/api/feed-status?scope=dev").json()["sources"]}
    assert dev["sample-blog"]["last_run_status"] == "failed"
    assert dev["sample-blog"]["stale"] is True
    assert dev["devto"]["last_run_status"] == "succeeded"


def test_read_endpoints_never_write(app_client, clean_db):
    client, application = app_client
    seed_catalog(clean_db)
    collect_all(clean_db)

    writes = []

    def record(conn, cursor, statement, *args):
        if re.match(r"\s*(INSERT|UPDATE|DELETE|REPLACE|CREATE|ALTER|DROP)", statement, re.I):
            writes.append(statement)

    event.listen(application.state.engine, "before_cursor_execute", record)
    try:
        for url in (
            "/api/news",
            "/api/dev/channels",
            "/api/dev/channels/devto/posts?sort=popular",
            "/api/trends?scope=dev",
            "/api/feed-status?scope=news",
        ):
            assert client.get(url).status_code == 200, url
    finally:
        event.remove(application.state.engine, "before_cursor_execute", record)
    assert writes == []
