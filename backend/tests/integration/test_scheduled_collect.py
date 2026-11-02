"""Scheduled collection end to end on the test database: `collect --group` with a fake
fetcher, then the read API. The rendered cron command is also run for real (sh + flock)
for a group with no sources, so nothing leaves the machine.
"""

import fcntl
import os
import subprocess
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient
from sqlalchemy import text

import app.integrations.gemini as gemini_module
import app.integrations.http as http_module
from app.jobs import __main__ as cli
from app.jobs.schedule import crontab, load_schedule
from app.main import create_app
from tests.collect_helpers import FakeFetcher, fixture, sample_routes, seed_catalog
from tests.conftest import BACKEND_DIR, TEST_JWT_SECRET

pytestmark = pytest.mark.integration

NEWS_FEED = "https://news.example.com/rss"
NEW_ITEM = b"""
    <item>
      <title>Scheduled run finds a new article</title>
      <link>https://news.example.com/articles/99</link>
      <guid>https://news.example.com/articles/99</guid>
      <description>A new item.</description>
      <pubDate>Wed, 28 Oct 2026 09:00:00 +0900</pubDate>
    </item>
  </channel>"""


def schedule_file(tmp_path: Path, news=("sample-news", "hackernews"), dev=("devto", "sample-blog")):
    path = tmp_path / "schedule.yaml"
    data = {
        "timezone": "Asia/Seoul",
        "groups": {
            "news": {"minute": 0, "hours": [2, 14], "sources": list(news)},
            "dev": {"minute": 0, "hours": [5, 11, 17, 23], "sources": list(dev)},
        },
    }
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


class NoGemini:
    def __init__(self, **kwargs):
        raise AssertionError("scheduled collection must not create a Gemini client")


@pytest.fixture()
def run(clean_db, integration_settings, monkeypatch, tmp_path):
    seed_catalog(clean_db)
    monkeypatch.setattr(gemini_module.genai, "Client", NoGemini)
    monkeypatch.setattr(cli, "get_settings", lambda: integration_settings)
    fetchers = []

    def run(group, routes=None, schedule=None):
        fetcher = FakeFetcher(routes or sample_routes())
        fetcher.close = lambda: None
        fetchers.append(fetcher)
        monkeypatch.setattr(cli, "HttpFetcher", lambda settings: fetcher)
        path = schedule or schedule_file(tmp_path)
        return cli.main(["collect", "--group", group, "--schedule", str(path)]), fetcher

    run.fetchers = fetchers
    return run


def rows(engine, sql, **params):
    with engine.connect() as connection:
        return [tuple(r) for r in connection.execute(text(sql), params)]


def counts(engine):
    return dict(
        rows(
            engine,
            "SELECT s.slug, COUNT(c.id) FROM content_sources s "
            "LEFT JOIN contents c ON c.source_id = s.id GROUP BY s.slug",
        )
    )


def test_a_group_collects_only_its_listed_sources(run, clean_db, capsys):
    code, fetcher = run("dev")
    assert code == 0
    fetched = {url for url, _ in fetcher.calls}
    assert fetched == {"https://blog.example.com/atom", "https://dev.to/api/articles"}
    found = counts(clean_db)
    assert found["devto"] == 3 and found["sample-blog"] == 1
    assert found["sample-news"] == found["hackernews"] == found["stackoverflow"] == 0

    code, fetcher = run("news")
    out = capsys.readouterr().out
    assert code == 0
    assert "not collected: hackernews: a community source is not in the news group" in out
    assert {url for url, _ in fetcher.calls} == {NEWS_FEED}
    assert counts(clean_db)["hackernews"] == 0


def test_running_again_stores_no_duplicates(run, clean_db):
    run("news")
    before = rows(clean_db, "SELECT id, url_hash FROM contents ORDER BY id")
    code, _ = run("news")
    assert code == 0
    assert rows(clean_db, "SELECT id, url_hash FROM contents ORDER BY id") == before
    assert rows(
        clean_db, "SELECT inserted_count FROM job_runs WHERE job_name = 'collect' ORDER BY id"
    ) == [(3,), (0,)]


def test_a_new_article_is_stored_and_served(run, clean_db, integration_settings):
    run("news")
    run("dev")
    routes = sample_routes()
    routes[NEWS_FEED] = fixture("news.rss.xml").replace(b"\n  </channel>", NEW_ITEM, 1)
    code, _ = run("news", routes)
    assert code == 0
    assert rows(clean_db, "SELECT inserted_count FROM job_runs ORDER BY id DESC LIMIT 1") == [(1,)]

    with TestClient(create_app(integration_settings)) as client:
        news = client.get("/api/news", params={"size": 50}).json()["items"]
        articles = client.get("/api/dev/articles", params={"size": 3}).json()["items"]
    assert "https://news.example.com/articles/99" in {i["url"] for i in news}
    assert len(articles) == 3 and all(i["source"]["slug"] != "sample-news" for i in articles)


def test_one_failing_source_does_not_stop_the_others_and_the_next_run_recovers(run, clean_db):
    broken = sample_routes()
    broken.pop("https://blog.example.com/atom")  # 404 for the blog feed
    code, fetcher = run("dev", broken)
    assert code == 1
    tried = {url for url, _ in fetcher.calls}
    assert tried == {"https://dev.to/api/articles", "https://blog.example.com/atom"}
    statuses = dict(
        rows(
            clean_db,
            "SELECT s.slug, j.status FROM job_runs j JOIN content_sources s ON s.id = j.source_id",
        )
    )
    assert statuses == {"devto": "succeeded", "sample-blog": "failed"}

    code, _ = run("dev")  # the next scheduled run
    assert code == 0
    assert counts(clean_db)["sample-blog"] == 1
    assert rows(
        clean_db,
        "SELECT j.status FROM job_runs j JOIN content_sources s ON s.id = j.source_id "
        "WHERE s.slug = 'sample-blog' ORDER BY j.id",
    ) == [("failed",), ("succeeded",)]


def test_a_source_already_being_collected_is_skipped(run, clean_db):
    with clean_db.connect() as other:
        source_id = other.execute(
            text("SELECT id FROM content_sources WHERE slug = 'sample-news'")
        ).scalar_one()
        assert (
            other.execute(
                text("SELECT GET_LOCK(:n, 0)"), {"n": f"devhub:collect:{source_id}"}
            ).scalar_one()
            == 1
        )
        code, fetcher = run("news")
        other.execute(text("SELECT RELEASE_LOCK(:n)"), {"n": f"devhub:collect:{source_id}"})
    assert code == 0 and fetcher.calls == []
    assert rows(clean_db, "SELECT status FROM job_runs") == [("skipped",)]
    assert counts(clean_db)["sample-news"] == 0


def test_an_empty_group_does_nothing(run, clean_db, tmp_path):
    code, fetcher = run("news", schedule=schedule_file(tmp_path, news=()))
    assert code == 0 and fetcher.calls == []
    assert rows(clean_db, "SELECT COUNT(*) FROM job_runs") == [(0,)]


def test_reading_the_site_never_collects(run, clean_db, integration_settings, monkeypatch):
    run("news")
    run("dev")

    def no_fetch(*args, **kwargs):
        raise AssertionError("a page view must not fetch anything")

    monkeypatch.setattr(http_module.HttpFetcher, "get", no_fetch)
    before = rows(clean_db, "SELECT COUNT(*) FROM job_runs")
    with TestClient(create_app(integration_settings)) as client:
        for url in ("/api/news", "/api/dev/articles", "/api/dev/channels/devto/posts"):
            assert client.get(url).status_code == 200
    assert rows(clean_db, "SELECT COUNT(*) FROM job_runs") == before
    assert rows(clean_db, "SELECT COUNT(*) FROM content_summaries") == [(0,)]
    assert rows(clean_db, "SELECT COUNT(*) FROM content_translations") == [(0,)]


def test_the_rendered_cron_command_runs_and_overlapping_runs_are_skipped(
    clean_db, integration_settings, tmp_path
):
    """Runs the crontab's news line through sh, as cron would, with an empty news group
    (the repository's own setting), and again while the group lock is held."""
    seed_catalog(clean_db)
    schedule = load_schedule()
    assert schedule.groups["news"].sources == []
    uv = subprocess.run(["sh", "-c", "command -v uv"], capture_output=True, text=True)
    line = next(
        line
        for line in crontab(schedule, BACKEND_DIR, uv.stdout.strip(), tmp_path).splitlines()
        if "--group news" in line
    )
    command = line.split(" * * * ", 1)[1]
    lock = "/tmp/devhub-collect-news.lock"
    env = {k: v for k, v in os.environ.items() if k not in ("GEMINI_API_KEY", "DATABASE_URL")} | {
        "APP_ENV": "test",
        "DATABASE_URL": integration_settings.database_url.get_secret_value(),
        "JWT_SECRET": TEST_JWT_SECRET,
    }

    first = subprocess.run(["sh", "-c", command], env=env, timeout=120)
    assert first.returncode == 0
    log = (tmp_path / "collect-news.log").read_text(encoding="utf-8")
    assert "0 sources, 0 failed (group news)" in log

    with open(lock, "w") as held:
        fcntl.flock(held, fcntl.LOCK_EX)
        second = subprocess.run(["sh", "-c", command], env=env, timeout=120)
    assert second.returncode == 1  # flock -n: the previous run still holds the lock
    assert (tmp_path / "collect-news.log").read_text(encoding="utf-8") == log
    assert rows(clean_db, "SELECT COUNT(*) FROM job_runs") == [(0,)]
