"""Collector jobs and the taxonomy/source loaders against the MariaDB test database."""

import copy
import json
import threading

import pytest
from sqlalchemy import text

from app.content_loader.taxonomy import (
    SourcesFile,
    TechnologiesFile,
    apply_sources,
    apply_technologies,
)
from app.db.session import create_session_factory
from app.integrations.http import FetchError
from app.integrations.sources import SE_QUESTIONS, adapters
from app.jobs.runner import Collector
from tests.collect_helpers import (
    SOURCES,
    TECHNOLOGIES,
    FakeFetcher,
    collect_all,
    fixture,
    sample_routes,
    seed_catalog,
)

pytestmark = pytest.mark.integration


def rows(engine, sql, **params):
    with engine.connect() as connection:
        return [tuple(r) for r in connection.execute(text(sql), params)]


def scalar(engine, sql, **params):
    return rows(engine, sql, **params)[0][0]


def tags_of(engine, title_like):
    return sorted(
        r[0]
        for r in rows(
            engine,
            "SELECT t.slug FROM content_technologies ct "
            "JOIN technologies t ON t.id = ct.technology_id "
            "JOIN contents c ON c.id = ct.content_id WHERE c.title LIKE :t",
            t=title_like,
        )
    )


@pytest.fixture()
def seeded(clean_db):
    seed_catalog(clean_db)
    return clean_db


def test_first_run_saves_items_metrics_and_tags(seeded):
    results = collect_all(seeded)

    assert {slug: r.status for slug, r in results.items()} == dict.fromkeys(results, "succeeded")
    # 5 feed entries: one without a link is skipped, one duplicates another after
    # dropping utm_* parameters.
    assert (results["sample-news"].fetched, results["sample-news"].inserted) == (4, 3)
    assert results["devto"].inserted == 3  # latest + top, merged

    assert rows(
        seeded,
        "SELECT title, score, comment_count, view_count FROM contents "
        "WHERE external_id = '79000001'",
    ) == [('Why does asyncio.gather "hang" with a semaphore?', 27, 3, 1520)]
    # Feeds provide no metrics: NULL, not 0.
    assert rows(
        seeded,
        "SELECT COUNT(*) FROM contents c JOIN content_sources s ON s.id = c.source_id "
        "WHERE s.slug = 'sample-news' AND c.score IS NULL",
    ) == [(3,)]
    assert scalar(seeded, "SELECT url FROM contents WHERE title LIKE '파이썬 3.14%'") == (
        "https://news.example.com/articles/1"
    )
    assert scalar(seeded, "SELECT COUNT(*) FROM contents WHERE summary_status <> 'pending'") == 0

    assert tags_of(seeded, "파이썬 3.14%") == ["python"]
    assert tags_of(seeded, "JavaScript 런타임%") == ["javascript"]  # not java
    assert tags_of(seeded, "%랜섬웨어%") == ["security"]
    assert tags_of(seeded, "React Server Components%") == ["javascript", "react"]  # from tags
    assert tags_of(seeded, "쿠버네티스 위에서%") == ["kubernetes"]
    assert tags_of(seeded, "Why does asyncio%") == ["python"]  # tag python-3.x

    runs = rows(seeded, "SELECT status, fetched_count, inserted_count FROM job_runs ORDER BY id")
    assert len(runs) == 5 and all(r[0] == "succeeded" for r in runs)


def test_second_run_adds_nothing_and_only_refreshes_metrics(seeded):
    collect_all(seeded)
    before = scalar(seeded, "SELECT COUNT(*) FROM contents")

    routes = sample_routes()
    bumped = fixture("hn_front_page.json").replace(b'"points": 312', b'"points": 400')
    routes["https://hn.algolia.com/api/v1/search"] = bumped
    results = collect_all(seeded, routes)

    assert scalar(seeded, "SELECT COUNT(*) FROM contents") == before
    assert all(r.inserted == 0 for r in results.values())
    assert results["hackernews"].updated == 1
    assert results["sample-news"].updated == 0
    assert scalar(seeded, "SELECT score FROM contents WHERE external_id = '45000001'") == 400
    # Tags are not duplicated by the second run.
    assert scalar(seeded, "SELECT COUNT(*) FROM content_technologies") == scalar(
        seeded, "SELECT COUNT(DISTINCT content_id, technology_id) FROM content_technologies"
    )


def test_a_failing_source_is_recorded_and_does_not_stop_others(seeded):
    routes = sample_routes()
    routes["https://news.example.com/rss"] = FetchError("HTTP 503 from news.example.com/rss")
    routes["https://blog.example.com/atom"] = b"<html>not a feed</html>"
    results = collect_all(seeded, routes)

    assert results["sample-news"].status == "failed"
    assert results["sample-blog"].status == "failed"
    assert results["devto"].status == "succeeded"
    assert rows(
        seeded,
        "SELECT s.slug, j.status, j.error_summary FROM job_runs j "
        "JOIN content_sources s ON s.id = j.source_id WHERE j.status = 'failed' ORDER BY s.slug",
    ) == [
        ("sample-blog", "failed", "FetchError: not a readable RSS/Atom feed (no feed found)"),
        ("sample-news", "failed", "FetchError: HTTP 503 from news.example.com/rss"),
    ]
    assert scalar(seeded, "SELECT COUNT(*) FROM contents WHERE title LIKE '파이썬%'") == 0


def test_concurrent_run_of_the_same_source_is_skipped(seeded):
    started, release = threading.Event(), threading.Event()

    def slow_feed(_params):
        started.set()
        assert release.wait(10)
        return fixture("news.rss.xml")

    routes = sample_routes()
    routes["https://news.example.com/rss"] = slow_feed
    collector = Collector(seeded, FakeFetcher(routes), adapters())
    source = next(s for s in collector.sources() if s.slug == "sample-news")

    results = {}
    worker = threading.Thread(target=lambda: results.setdefault("first", collector.run(source)))
    worker.start()
    assert started.wait(10)
    results["second"] = collector.run(source)  # while the first still holds the lock
    release.set()
    worker.join(10)

    assert results["first"].status == "succeeded"
    assert results["second"].status == "skipped"
    assert scalar(seeded, "SELECT COUNT(*) FROM contents") == 3
    statuses = sorted(r[0] for r in rows(seeded, "SELECT status FROM job_runs"))
    assert statuses == ["skipped", "succeeded"]


def test_dry_run_writes_nothing(seeded):
    collector = Collector(seeded, FakeFetcher(sample_routes()), adapters())
    results = [collector.dry_run(s) for s in collector.sources()]

    assert all(r.status == "dry-run" for r in results)
    assert results[0].fetched == 4 and results[0].sample_titles
    assert scalar(seeded, "SELECT COUNT(*) FROM contents") == 0
    assert scalar(seeded, "SELECT COUNT(*) FROM job_runs") == 0


def test_taxonomy_and_sources_reload_is_idempotent_and_retires(clean_db):
    seed_catalog(clean_db)
    factory = create_session_factory(clean_db)

    with factory.begin() as db:
        assert not apply_technologies(db, TechnologiesFile.model_validate(TECHNOLOGIES)).changed
        assert not apply_sources(db, SourcesFile.model_validate(SOURCES)).changed

    technologies = copy.deepcopy(TECHNOLOGIES)
    technologies["technologies"] = [t for t in technologies["technologies"] if t["slug"] != "rust"]
    # Move an alias from one technology to another.
    technologies["technologies"][0]["aliases"].append("pip")
    sources = copy.deepcopy(SOURCES)
    sources["sources"] = sources["sources"][1:]
    with factory.begin() as db:
        tech_report = apply_technologies(db, TechnologiesFile.model_validate(technologies))
        source_report = apply_sources(db, SourcesFile.model_validate(sources))

    assert tech_report.retired == ["rust"]
    assert "alias 'pip' added" in tech_report.updated
    assert source_report.retired == ["sample-news"]
    assert rows(clean_db, "SELECT status FROM technologies WHERE slug = 'rust'") == [("retired",)]
    assert rows(clean_db, "SELECT status, position FROM content_sources WHERE slug = 'devto'") == [
        ("active", 1)
    ]


MIXED_FEED = b"""<?xml version="1.0"?>
<rss version="2.0"><channel><title>t</title>
  <item><title>Python 3.14 notes</title><link>https://news.example.com/ok/1</link></item>
  <item><title>script link</title><link>javascript:alert(1)</link></item>
  <item><title></title><link>https://news.example.com/ok/2</link></item>
  <item><title>Kubernetes notes</title><link>https://news.example.com/ok/3</link></item>
</channel></rss>"""

MIXED_SE = json.dumps(
    {
        "items": [
            {"question_id": 1, "title": "ok", "link": "https://stackoverflow.com/q/1"},
            {"question_id": 2, "title": "no link"},
        ]
    }
).encode()

ONLY_BAD_FEED = b"""<?xml version="1.0"?>
<rss version="2.0"><channel><title>t</title>
  <item><title>a</title><link>javascript:alert(1)</link></item>
  <item><title>b</title><link>ftp://news.example.com/x</link></item>
</channel></rss>"""


def test_unusable_entries_are_skipped_recorded_and_never_stored(seeded):
    routes = sample_routes()
    routes["https://news.example.com/rss"] = MIXED_FEED
    results = collect_all(seeded, routes)

    news = results["sample-news"]
    assert (news.status, news.fetched, news.inserted, news.skipped) == ("succeeded", 2, 2, 2)
    assert rows(
        seeded,
        "SELECT j.status, j.fetched_count, j.inserted_count, j.failed_count, j.error_summary "
        "FROM job_runs j JOIN content_sources s ON s.id = j.source_id "
        "WHERE s.slug = 'sample-news'",
    ) == [("succeeded", 2, 2, 2, "skipped 2 entries: link is not http(s) 1, no title 1")]
    # Only http(s) links reach the table, and the good entries are tagged as before.
    assert (
        scalar(seeded, "SELECT COUNT(*) FROM contents WHERE url NOT REGEXP '^https?://[^/]+'") == 0
    )
    assert tags_of(seeded, "Python 3.14 notes") == ["python"]
    assert tags_of(seeded, "Kubernetes notes") == ["kubernetes"]
    # Other sources are unaffected.
    assert results["devto"].status == "succeeded" and results["devto"].skipped == 0


def test_a_response_with_only_unusable_entries_fails_the_source(seeded):
    routes = sample_routes()
    routes["https://news.example.com/rss"] = ONLY_BAD_FEED
    results = collect_all(seeded, routes)

    news = results["sample-news"]
    assert news.status == "failed"
    assert news.error == (
        "UnusableResponse: no usable entries (skipped 2 entries: link is not http(s) 2)"
    )
    assert rows(
        seeded,
        "SELECT j.status, j.failed_count FROM job_runs j "
        "JOIN content_sources s ON s.id = j.source_id WHERE s.slug = 'sample-news'",
    ) == [("failed", 2)]
    assert results["sample-blog"].status == "succeeded"


def test_a_broken_api_entry_does_not_cost_the_rest_of_the_source(seeded):
    latest = json.loads(fixture("devto_latest.json"))
    latest.append({"id": 9999, "title": "no url here"})
    routes = sample_routes()
    routes["https://dev.to/api/articles"] = lambda params: (
        fixture("devto_top.json") if "top" in params else json.dumps(latest).encode()
    )
    results = collect_all(seeded, routes)

    assert (results["devto"].status, results["devto"].inserted) == ("succeeded", 3)
    assert results["devto"].skipped == 1
    assert scalar(seeded, "SELECT COUNT(*) FROM contents WHERE external_id = '9999'") == 0


def test_failed_count_means_skipped_entries_in_every_outcome(seeded):
    """job_runs.failed_count counts entries left out, never "the source failed" (see status)."""
    routes = sample_routes()
    routes["https://news.example.com/rss"] = FetchError("HTTP 503 from news.example.com/rss")
    routes["https://blog.example.com/atom"] = ONLY_BAD_FEED
    routes[SE_QUESTIONS] = MIXED_SE
    collect_all(seeded, routes)

    assert rows(
        seeded,
        "SELECT s.slug, j.status, j.failed_count FROM job_runs j "
        "JOIN content_sources s ON s.id = j.source_id ORDER BY s.slug",
    ) == [
        ("devto", "succeeded", 0),  # clean run
        ("hackernews", "succeeded", 0),
        ("sample-blog", "failed", 2),  # every entry unusable
        ("sample-news", "failed", 0),  # the source could not be read: no entries to count
        ("stackoverflow", "succeeded", 1),  # one entry skipped, the rest saved
    ]
