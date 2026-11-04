"""Experiment boundaries outside the loader (A1): collector, write guard, diagnose,
redirects, excerpt switches and AI. Fake engines, fetchers and models; no network,
no database. The dedicated test database is used in tests/integration/."""

from datetime import datetime
from types import SimpleNamespace

import httpx
import pytest

from app.content_loader.taxonomy import SourcesFile
from app.integrations.http import FetchError, HttpFetcher
from app.integrations.robots import RobotsPolicy, guard_redirects, refuse_redirects
from app.integrations.sources import CollectedItem, adapters
from app.jobs import __main__ as cli
from app.jobs.diagnose import diagnose
from app.jobs.runner import Collector
from app.jobs.schedule import Schedule
from app.jobs.store import _guard
from app.jobs.summarize import summarize_contents
from app.services import experiment_policy as ep
from app.services.source_terms import allows_ai_summary, tags_with_excerpt
from tests.collect_helpers import FakeFetcher
from tests.conftest import make_settings
from tests.experiment_helpers import (
    WINDOW,
    FakeConnection,
    FakeEngine,
    FakeSession,
    NoDatabase,
    exp_source,
    install,
    policy_for,
)

FEED = "https://exp-blog.example.invalid/feed.xml"
ROBOTS = "https://exp-blog.example.invalid/robots.txt"
RSS = (
    b'<?xml version="1.0"?><rss version="2.0"><channel><title>x</title>'
    b"<item><title>Kubernetes notes</title><link>https://exp-blog.example.invalid/1</link>"
    b"<description>Python and Rust</description><author>a@example.invalid (A)</author>"
    b"<guid>id-1</guid><category>react</category>"
    b"<pubDate>Sun, 01 Nov 2026 09:00:00 +0000</pubDate></item></channel></rss>"
)
SCHEDULE = Schedule.model_validate(
    {
        "timezone": "Asia/Seoul",
        "groups": {"news": {"minute": 0, "hours": [2, 14]}, "dev": {"minute": 0, "hours": [5]}},
    }
)


def row(**changes):
    """A ContentSource-like row built from the validated YAML shape."""
    definition = SourcesFile.model_validate({"sources": [exp_source(**changes)]}).sources[0]
    values = definition.model_dump() | {"id": 1, "status": "active", "max_items": 30}
    return SimpleNamespace(**values)


def collector(engine, routes=None, robots=True):
    fetcher = FakeFetcher(routes if routes is not None else {FEED: RSS})
    return Collector(
        engine, fetcher, adapters(), RobotsPolicy(fetcher) if robots else None
    ), fetcher


# --- Collector ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("engine", "policies", "robots", "code"),
    [
        (FakeEngine(), {}, True, "unknown_scope"),  # the shipped empty registry
        (FakeEngine("devhub_test", "devhub_test"), None, True, "not_the_experiment_database"),
        (FakeEngine("devhub_experiment", "devhub_dev"), None, True, "not_the_experiment_database"),
        (FakeEngine(), None, False, "robots_check_required"),
    ],
)
def test_run_refuses_before_the_lock_job_runs_or_any_request(
    monkeypatch, engine, policies, robots, code
):
    install(monkeypatch, policy_for([exp_source()]) if policies is None else policies)
    runner, fetcher = collector(engine, robots=robots)
    result = runner.run(row())
    assert result.status == "refused" and code in result.error
    assert fetcher.calls == [] and engine.connects <= 1  # at most the identity check


def test_run_refuses_an_expired_policy(monkeypatch):
    install(monkeypatch, policy_for([exp_source()]), at=WINDOW[1])
    runner, fetcher = collector(FakeEngine())
    assert "outside_policy_window" in runner.run(row()).error
    assert fetcher.calls == []


def test_run_refuses_a_read_only_grant_for_storing(monkeypatch):
    install(monkeypatch, policy_for([exp_source()], actions=("metadata_read",)))
    runner, fetcher = collector(FakeEngine())
    assert "metadata_store_not_allowed" in runner.run(row()).error
    assert fetcher.calls == []


def test_general_sources_are_refused_in_the_experiment_database():
    runner, fetcher = collector(FakeEngine())
    general = SimpleNamespace(
        id=1,
        slug="toss-tech",
        status="active",
        adapter="rss",
        feed_url=FEED,
        options={"terms": "approved"},
    )
    result = runner.run(general)
    assert "general_source_in_experiment_database" in result.error and fetcher.calls == []
    assert runner.dry_run(general).status == "failed" and fetcher.calls == []


def test_fetch_and_dry_run_check_the_policy_before_robots(monkeypatch):
    install(monkeypatch, {})
    runner, fetcher = collector(FakeEngine())
    with pytest.raises(ep.PolicyError, match="unknown_scope"):
        runner.fetch(row())
    assert runner.dry_run(row()).status == "failed"
    assert fetcher.calls == []  # not even robots.txt


def test_an_allowed_fetch_keeps_only_the_granted_fields(monkeypatch):
    install(monkeypatch, policy_for([exp_source()]))
    runner, fetcher = collector(FakeEngine())
    (item,) = runner.fetch(row()).items
    assert [url for url, _ in fetcher.calls] == [ROBOTS, FEED]
    assert (item.title, item.published_at) == ("Kubernetes notes", datetime(2026, 11, 1, 9, 0))
    assert (item.author, item.external_id, item.tags) == (None, None, [])
    assert item.excerpt == "Python and Rust"  # kept for the excerpt switches to decide


# --- redirects ------------------------------------------------------------------------------


class Site:
    def __init__(self, pages):
        self.pages, self.requested = pages, []

    def __call__(self, request):
        self.requested.append(str(request.url))
        return self.pages.get(str(request.url), httpx.Response(404))


def moved(location):
    return httpx.Response(301, headers={"location": location})


def http(site):
    return HttpFetcher(make_settings(), httpx.MockTransport(site), sleep=lambda s: None)


def test_an_experiment_feed_redirect_is_refused_before_its_target(monkeypatch):
    install(monkeypatch, policy_for([exp_source()]))
    site = Site(
        {
            ROBOTS: httpx.Response(200, text="User-agent: *\n"),
            FEED: moved("https://exp-blog.example.invalid/feed"),
        }
    )
    fetcher = http(site)
    runner = Collector(FakeEngine(), fetcher, adapters(), RobotsPolicy(fetcher))
    with pytest.raises(FetchError, match="redirect refused"):
        runner.fetch(row())
    assert "https://exp-blog.example.invalid/feed" not in site.requested
    assert fetcher.on_redirect is None  # every hook restored


def test_an_experiment_robots_redirect_means_nothing_is_requested(monkeypatch):
    install(monkeypatch, policy_for([exp_source()]))
    site = Site({ROBOTS: moved("https://exp-blog.example.invalid/robots-real.txt")})
    fetcher = http(site)
    runner = Collector(FakeEngine(), fetcher, adapters(), RobotsPolicy(fetcher))
    with pytest.raises(FetchError, match="robots.txt unreachable"):
        runner.fetch(row())
    assert site.requested == [ROBOTS]


def test_guard_redirects_keeps_an_outer_hook_and_restores_it():
    seen = []
    fetcher = SimpleNamespace(on_redirect=seen.append)
    robots = SimpleNamespace(require=lambda url: seen.append(f"robots {url}"))
    with guard_redirects(fetcher, robots):
        fetcher.on_redirect("https://a.example/x")
    assert seen == ["https://a.example/x", "robots https://a.example/x"]
    assert fetcher.on_redirect == seen.append
    with refuse_redirects(fetcher), pytest.raises(FetchError):
        fetcher.on_redirect("https://a.example/y")
    assert fetcher.on_redirect == seen.append


# --- the write boundary and the excerpt switches -----------------------------------------


def item():
    return CollectedItem(
        url="https://exp-blog.example.invalid/1",
        title="T",
        excerpt="desc",
        author="A",
        external_id="id",
        tags=["react"],
    )


def test_the_write_guard_uses_the_sessions_own_connection(monkeypatch):
    install(monkeypatch, policy_for([exp_source()]))
    db = FakeSession(FakeConnection())
    (kept,) = _guard(db, row(), [item()])
    assert (kept.author, kept.external_id, kept.tags) == (None, None, [])
    assert db.autoflush_disabled == 1 and db._connection.queries == 1
    for wrong in (FakeConnection("devhub_test", "devhub_test"), FakeConnection(actual="x")):
        with pytest.raises(ep.PolicyError, match="not_the_experiment_database"):
            _guard(FakeSession(wrong), row(), [item()])


def test_the_write_guard_refuses_general_sources_in_the_experiment_database():
    general = SimpleNamespace(slug="toss-tech", options={"terms": "approved"})
    with pytest.raises(ep.PolicyError, match="general_source_in_experiment_database"):
        _guard(FakeSession(FakeConnection()), general, [item()])
    items = [item()]
    assert _guard(FakeSession(FakeConnection("devhub_dev", "devhub_dev")), general, items) is items


def test_the_write_guard_rechecks_the_window(monkeypatch):
    install(monkeypatch, policy_for([exp_source()]), at=WINDOW[1])
    with pytest.raises(ep.PolicyError, match="outside_policy_window"):
        _guard(FakeSession(FakeConnection()), row(), [item()])


@pytest.mark.parametrize(
    ("slug", "options", "expected"),
    [
        ("toss-tech", {}, True),  # general: unchanged default
        ("toss-tech", {"tagging_excerpt": True}, True),
        ("toss-tech", {"tagging_excerpt": False}, False),
        ("exp-blog", {"scope": "trial-1"}, False),  # experiment: off unless asked for
        ("exp-blog", {"scope": "trial-1", "tagging_excerpt": False}, False),
        ("exp-blog", {"scope": "trial-1", "tagging_excerpt": True}, True),
    ],
)
def test_excerpt_tagging_switch(slug, options, expected):
    assert tags_with_excerpt(SimpleNamespace(slug=slug, options=options)) is expected


# --- diagnose ---------------------------------------------------------------------------


def defs(*sources):
    return SourcesFile.model_validate({"sources": list(sources)}).sources


def test_general_diagnose_never_opens_a_database():
    general = defs(
        {
            "slug": "plain",
            "name": "Plain",
            "kind": "news",
            "adapter": "rss",
            "language": "ko",
            "site_url": "https://plain.example.invalid/",
            "feed_url": "https://plain.example.invalid/rss",
        }
    )
    fetcher = FakeFetcher({"https://plain.example.invalid/rss": RSS})
    (report,) = diagnose(general, fetcher, SCHEDULE, engine=NoDatabase())
    assert report.outcome == "ok"


@pytest.mark.parametrize(
    ("engine", "code"),
    [
        (None, "experiment_needs_its_database"),
        (FakeEngine("devhub_dev", "devhub_dev"), "not_the_experiment_database"),
    ],
)
def test_experiment_diagnose_needs_the_experiment_database(monkeypatch, engine, code):
    install(monkeypatch, policy_for([exp_source()]))
    fetcher = FakeFetcher({FEED: RSS})
    (report,) = diagnose(defs(exp_source()), fetcher, SCHEDULE, engine=engine)
    assert report.outcome == "not requested" and code in report.detail
    assert fetcher.calls == []


def test_experiment_diagnose_without_a_policy_requests_nothing():
    fetcher = FakeFetcher({FEED: RSS})
    (report,) = diagnose(defs(exp_source()), fetcher, SCHEDULE, engine=FakeEngine())
    assert "unknown_scope" in report.detail and fetcher.calls == []


def test_allowed_experiment_diagnose_reads_and_projects(monkeypatch):
    install(monkeypatch, policy_for([exp_source()]))
    fetcher = FakeFetcher({FEED: RSS})
    (report,) = diagnose(defs(exp_source()), fetcher, SCHEDULE, engine=FakeEngine())
    assert report.outcome == "ok" and report.items == 1
    assert [url for url, _ in fetcher.calls] == [ROBOTS, FEED]


def test_diagnose_cli_reports_a_policy_refusal_as_failure(monkeypatch, tmp_path, capsys):
    path = tmp_path / "anything.yaml"
    path.write_text(
        "sources:\n  - " + str(exp_source()).replace("'", '"').replace("None", "null") + "\n"
    )
    monkeypatch.setattr(cli, "get_settings", lambda: make_settings())
    monkeypatch.setattr(cli, "create_db_engine", lambda settings: FakeEngine())
    fetcher = FakeFetcher({})
    fetcher.close = lambda: None
    monkeypatch.setattr(cli, "HttpFetcher", lambda settings: fetcher)
    monkeypatch.setattr(FakeEngine, "dispose", lambda self: None, raising=False)
    assert cli.main(["diagnose", "--sources-file", str(path)]) == 1
    assert "unknown_scope" in capsys.readouterr().out and fetcher.calls == []


# --- AI ------------------------------------------------------------------------------


def test_experiment_sources_never_qualify_for_ai_summaries():
    approved = {"terms": "approved"}
    assert allows_ai_summary(SimpleNamespace(slug="news", ai_summary=True, options=approved))
    for slug, options in (("exp-news", approved), ("news", approved | {"scope": "trial-1"})):
        assert not allows_ai_summary(SimpleNamespace(slug=slug, ai_summary=True, options=options))


class ExplodingModel:
    model = "never"

    def complete(self, request):
        raise AssertionError("a model was called")


@pytest.mark.parametrize(
    "engine",
    [FakeEngine(), FakeEngine("devhub_dev", "devhub_experiment")],
)
def test_summaries_are_refused_in_the_experiment_database_before_any_body(engine):
    bodies_read = []
    with pytest.raises(ep.PolicyError, match="summaries_refused_in_experiment_database"):
        summarize_contents(engine, ExplodingModel(), lambda item: bodies_read.append(item))
    assert bodies_read == []


def test_summarize_cli_refuses_before_reading_bodies_or_making_a_client(
    monkeypatch, tmp_path, capsys
):
    body = tmp_path / "body.html"
    body.write_text("<p>secret article text</p>")
    monkeypatch.setattr(cli, "get_settings", lambda: make_settings())
    monkeypatch.setattr(cli, "create_db_engine", lambda settings: FakeEngine())
    monkeypatch.setattr(FakeEngine, "dispose", lambda self: None, raising=False)
    monkeypatch.setattr(cli, "gemini_client", lambda settings: pytest.fail("client created"))
    code = cli.main(["summarize", "--body", f"https://x.example.invalid/1={body}"])
    err = capsys.readouterr().err
    assert code == 2 and "summaries_refused_in_experiment_database" in err
    assert "secret article text" not in err
