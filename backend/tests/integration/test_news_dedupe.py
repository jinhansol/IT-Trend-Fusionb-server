"""P2 (C-4): Home news shows each normalized URL once, through a representative row.

Fixture: "sample-news" (news.rss.xml, position 1) and "sample-news-2" (news2.rss.xml,
position 2) share three links:
  /articles/1  both have a publish time; sample-news-2's is earlier  -> sample-news-2
  /articles/2  only sample-news has a publish time                   -> sample-news
  /articles/3  neither has one; collection time, then source order   -> sample-news
plus one link only sample-news-2 has (/rust-2027).
"""

import copy

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, text

from app.main import create_app
from tests.collect_helpers import SOURCES, collect_all, sample_routes, seed_catalog
from tests.integration.test_content_api import shift_dates_to_now

pytestmark = pytest.mark.integration

NEWS_2 = {
    "slug": "sample-news-2",
    "name": "Second News",
    "kind": "news",
    "adapter": "rss",
    "language": "ko",
    "site_url": "https://news2.example.com/",
    "feed_url": "https://news2.example.com/rss",
}


def sources_with_second_outlet():
    sources = copy.deepcopy(SOURCES)
    sources["sources"].insert(1, NEWS_2)  # right after sample-news
    return sources


@pytest.fixture()
def seeded(clean_db):
    seed_catalog(clean_db, sources=sources_with_second_outlet())
    routes = sample_routes()
    routes["https://news2.example.com/rss"] = "news2.rss.xml"
    results = collect_all(clean_db, routes)
    assert all(r.status == "succeeded" for r in results.values())
    shift_dates_to_now(clean_db)
    return clean_db


@pytest.fixture()
def client(seeded, integration_settings):
    application = create_app(integration_settings)
    with TestClient(application) as test_client:
        test_client.app_ref = application
        yield test_client


def news(client, **params):
    return client.get("/api/news", params={"size": 50, **params}).json()


def by_path(items):
    return {i["url"].split("example.com", 1)[1]: i for i in items}


def test_each_link_appears_once_with_a_deterministic_representative(client, seeded):
    with seeded.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT COUNT(*) FROM contents c JOIN content_sources s ON s.id = c.source_id "
                "WHERE s.kind = 'news'"
            )
        ).scalar_one()
    body = news(client)

    assert rows == 7  # 3 + 4 stored rows: duplicates are kept for per-source data
    assert body["total"] == 4 and len(body["items"]) == 4
    items = by_path(body["items"])
    assert items["/articles/1"]["source"]["slug"] == "sample-news-2"  # earlier publish time
    assert items["/articles/1"]["title"] == "파이썬 3.14 출시 (제휴 기사)"  # title of that row
    assert items["/articles/2"]["source"]["slug"] == "sample-news"  # has a publish time
    assert items["/articles/2"]["published_at"] is not None
    assert items["/articles/3"]["source"]["slug"] == "sample-news"  # collected first
    assert items["/rust-2027"]["source"]["slug"] == "sample-news-2"


def test_list_is_sorted_by_the_representative_date(client):
    items = news(client)["items"]
    keys = [(i["published_at"] or i["collected_at"]) for i in items]
    assert keys == sorted(keys, reverse=True)
    assert [i["url"].split("example.com", 1)[1] for i in items] == [
        "/articles/3",  # no publish time: shown by collection time (now)
        "/articles/2",
        "/articles/1",
        "/rust-2027",
    ]


def test_source_order_breaks_a_full_tie(client, seeded):
    with seeded.begin() as connection:
        connection.execute(
            text(
                "UPDATE contents SET collected_at = '2026-10-28 00:00:00', published_at = NULL "
                "WHERE url LIKE '%/articles/3'"
            )
        )
    assert by_path(news(client)["items"])["/articles/3"]["source"]["slug"] == "sample-news"


def test_filter_uses_the_tags_of_every_copy(client):
    # Only sample-news-2's copy of /articles/1 mentions Kubernetes; the group still matches
    # and is shown through its representative.
    kube = news(client, tech="kubernetes")
    assert kube["total"] == 1
    assert kube["items"][0]["url"].endswith("/articles/1")
    techs = {t["slug"] for t in kube["items"][0]["technologies"]}
    assert techs == {"python", "kubernetes"}  # union of both copies' tags

    assert [i["url"][-10:] for i in news(client, tech="javascript")["items"]] == ["articles/2"]
    assert news(client, tech="python")["total"] == 1  # two tagged copies, one group
    assert news(client, tech="rust")["total"] == 1


@pytest.mark.parametrize("tech", [None, "python", "security"])
def test_paging_one_by_one_never_repeats_or_skips(client, tech):
    params = {"tech": tech} if tech else {}
    full = news(client, **params)
    seen = []
    for page in range(1, full["total"] + 2):
        body = client.get("/api/news", params={"size": 1, "page": page, **params}).json()
        assert body["total"] == full["total"]
        seen.extend(i["id"] for i in body["items"])
    assert seen == [i["id"] for i in full["items"]]
    assert len(seen) == len(set(seen))


def test_news_mention_counts_count_each_link_once(client):
    report = client.get("/api/trends", params={"scope": "news", "days": 7}).json()
    counts = {t["slug"]: t["count"] for t in report["technologies"] + report["fields"]}

    assert report["total"] == 4
    assert counts["python"] == 1  # both copies of /articles/1 are tagged python
    assert counts["kubernetes"] == 1
    assert counts["javascript"] == 1
    assert counts["security"] == 1
    assert sum(day["total"] for day in report["daily"]) == 4
    assert sum(day["counts"].get("python", 0) for day in report["daily"]) == 1


def test_dev_lists_and_counts_are_not_deduplicated(client, seeded):
    with seeded.connect() as connection:
        dev_rows = connection.execute(
            text(
                "SELECT COUNT(*) FROM contents c JOIN content_sources s ON s.id = c.source_id "
                "WHERE s.kind <> 'news'"
            )
        ).scalar_one()
    assert client.get("/api/trends", params={"scope": "dev"}).json()["total"] == dev_rows
    assert client.get("/api/dev/channels/devto/posts").json()["total"] == 3


def test_deduplicated_reads_never_write(client):
    writes = []

    def record(conn, cursor, statement, *args):
        if statement.lstrip().split(" ", 1)[0].upper() in {"INSERT", "UPDATE", "DELETE", "REPLACE"}:
            writes.append(statement)

    engine = client.app_ref.state.engine
    event.listen(engine, "before_cursor_execute", record)
    try:
        for url in ("/api/news", "/api/news?tech=python&page=2&size=1", "/api/trends?scope=news"):
            assert client.get(url).status_code == 200
    finally:
        event.remove(engine, "before_cursor_execute", record)
    assert writes == []
