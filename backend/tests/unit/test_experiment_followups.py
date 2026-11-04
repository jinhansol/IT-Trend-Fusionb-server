"""A1 review follow-ups (PR #16): fixes for three findings, each with its reproduction.

1. Saving experiment content rechecks the source's status and terms (collect_refusal)
   on the row as it is at write time, before any add or flush.
2. Collect and summarize check the database each connection really selected: the
   pre-check, the lock connection and every session that reads or writes.
3. Experiment grants are RSS feeds only (adapter "rss" and a valid feed URL).

Fake engines, sessions, fetchers and models only; no network, no database.
"""

from types import SimpleNamespace

import pytest

from app.content_loader.taxonomy import SourcesFile, apply_sources
from app.integrations.robots import RobotsPolicy
from app.integrations.sources import CollectedItem, adapters
from app.jobs import __main__ as cli
from app.jobs import summarize as summarize_module
from app.jobs.runner import Collector
from app.jobs.store import store_items
from app.services import experiment_policy as ep
from app.services.tagging import Tagger
from tests.collect_helpers import FakeFetcher
from tests.conftest import make_settings
from tests.experiment_helpers import (
    FakeConnection,
    FakeSession,
    ScriptedEngine,
    ScriptedSession,
    ScriptedSessions,
    as_file,
    exp_source,
    install,
    policy_for,
)

DEV, EXP = "devhub_dev", "devhub_experiment"
FEED = "https://exp-blog.example.invalid/feed.xml"
ROBOTS = "https://exp-blog.example.invalid/robots.txt"
GENERAL_FEED = "https://news.example.invalid/rss"
ONE_ITEM = (
    b'<?xml version="1.0"?><rss version="2.0"><channel><title>x</title>'
    b"<item><title>Notes</title><link>https://exp-blog.example.invalid/1</link>"
    b"<pubDate>Sun, 01 Nov 2026 09:00:00 +0000</pubDate></item></channel></rss>"
)
NO_ITEMS = b'<?xml version="1.0"?><rss version="2.0"><channel><title>x</title></channel></rss>'


def experiment_row(**changes):
    definition = SourcesFile.model_validate(as_file(exp_source())).sources[0]
    values = definition.model_dump() | {"id": 7, "status": "active", "max_items": 30}
    return SimpleNamespace(**(values | changes))


def general_row(**changes):
    values = {
        "id": 3,
        "slug": "plain-news",
        "kind": "news",
        "adapter": "rss",
        "language": "ko",
        "site_url": "https://news.example.invalid/",
        "feed_url": GENERAL_FEED,
        "options": {"terms": "approved"},
        "status": "active",
        "max_items": 30,
        "ai_summary": False,
    }
    return SimpleNamespace(**(values | changes))


def jobrun():
    return SimpleNamespace(status="running")


# --- 1. collect_refusal at the write boundary ---------------------------------------------


def item():
    return CollectedItem(url="https://exp-blog.example.invalid/1", title="Notes")


@pytest.mark.parametrize(
    ("changes", "code"),
    [
        ({"options": {"scope": "trial-1", "terms": "unverified"}}, "terms_not_approved"),
        ({"status": "paused"}, "source_not_active"),
    ],
)
def test_direct_store_refuses_an_unapproved_or_paused_experiment_source(monkeypatch, changes, code):
    install(monkeypatch, policy_for([exp_source()]))
    db = FakeSession(FakeConnection())
    with pytest.raises(ep.PolicyError, match=code):
        store_items(db, experiment_row(**changes), [item()], Tagger.from_aliases([]))
    assert db.added == [] and db.flushes == 0  # before reproduction: 1 add, 2 flushes


def test_direct_store_still_saves_an_approved_active_experiment_source(monkeypatch):
    install(monkeypatch, policy_for([exp_source()]))
    db = ScriptedSession(FakeConnection())
    result = store_items(db, experiment_row(), [item()], Tagger.from_aliases([]))
    assert result.inserted == 1 and len(db.added) == 1 and db.flushes == 2


@pytest.mark.parametrize(
    ("now_row", "code"),
    [
        (experiment_row(status="paused"), "source_not_active"),
        (experiment_row(options={"scope": "trial-1", "terms": "unverified"}), "terms_not_approved"),
    ],
)
def test_a_source_paused_or_unapproved_during_the_request_is_not_saved(monkeypatch, now_row, code):
    """The collector saves with the row read again after the HTTP request."""
    install(monkeypatch, policy_for([exp_source()]))
    fetcher = FakeFetcher({FEED: ONE_ITEM})
    engine = ScriptedEngine(EXP, [EXP])
    runner = Collector(engine, fetcher, adapters(), RobotsPolicy(fetcher))
    sessions = ScriptedSessions(
        [FakeConnection()], objects={"ContentSource": now_row, "JobRun": jobrun()}
    )
    runner._sessions = sessions
    result = runner.run(experiment_row())
    assert result.status == "failed" and code in result.error
    assert [url for url, _ in fetcher.calls] == [ROBOTS, FEED]
    start, store, end = sessions.opened
    assert store.added == [] and store.flushes == 0  # no content written
    assert sessions.objects["JobRun"].status == "failed"  # the started run is closed


# --- 2. the database each connection really selected ---------------------------------------


def test_a_mismatched_first_connection_stops_collect_before_lock_jobrun_or_http():
    fetcher = FakeFetcher({GENERAL_FEED: ONE_ITEM})
    engine = ScriptedEngine(DEV, [EXP])  # configured dev, actually experiment
    runner = Collector(engine, fetcher, adapters(), RobotsPolicy(fetcher))
    runner._sessions = sessions = ScriptedSessions([FakeConnection(DEV, DEV)])
    result = runner.run(general_row())
    assert result.status == "refused" and "general_source_in_experiment_database" in result.error
    assert engine.log == [] and sessions.opened == [] and fetcher.calls == []
    with pytest.raises(ep.PolicyError):
        runner.fetch(general_row())
    assert runner.dry_run(general_row()).status == "failed" and fetcher.calls == []


def test_a_mismatched_lock_connection_stops_before_get_lock():
    fetcher = FakeFetcher({GENERAL_FEED: ONE_ITEM})
    engine = ScriptedEngine(DEV, [DEV, EXP])  # pre-check fine, lock connection not
    runner = Collector(engine, fetcher, adapters(), RobotsPolicy(fetcher))
    runner._sessions = sessions = ScriptedSessions([FakeConnection(DEV, DEV)])
    result = runner.run(general_row())
    assert result.status == "refused" and engine.log == []
    assert sessions.opened == [] and fetcher.calls == []


def test_a_mismatched_jobrun_session_writes_nothing_and_requests_nothing():
    fetcher = FakeFetcher({GENERAL_FEED: ONE_ITEM})
    runner = Collector(ScriptedEngine(DEV, [DEV]), fetcher, adapters(), RobotsPolicy(fetcher))
    runner._sessions = sessions = ScriptedSessions([FakeConnection(DEV, EXP)])
    result = runner.run(general_row())
    assert result.status == "refused" and "general_source_in_experiment_database" in result.error
    (start,) = sessions.opened
    assert start.added == [] and fetcher.calls == []


def test_a_mismatched_store_session_saves_nothing_and_the_run_is_closed_as_failed():
    fetcher = FakeFetcher({GENERAL_FEED: ONE_ITEM})
    runner = Collector(ScriptedEngine(DEV, [DEV]), fetcher, adapters(), RobotsPolicy(fetcher))
    ok, wrong = FakeConnection(DEV, DEV), FakeConnection(DEV, EXP)
    runner._sessions = sessions = ScriptedSessions(
        [ok, wrong, ok], objects={"ContentSource": general_row(), "JobRun": jobrun()}
    )
    result = runner.run(general_row())
    assert result.status == "failed" and "general_source_in_experiment_database" in result.error
    start, store, end = sessions.opened
    assert len(start.added) == 1  # the JobRun, on the right database
    assert store.added == [] and store.flushes == 0
    assert sessions.objects["JobRun"].status == "failed"


def test_a_mismatched_closing_session_does_not_update_the_jobrun():
    fetcher = FakeFetcher({GENERAL_FEED: NO_ITEMS})
    runner = Collector(ScriptedEngine(DEV, [DEV]), fetcher, adapters(), RobotsPolicy(fetcher))
    ok, wrong = FakeConnection(DEV, DEV), FakeConnection(DEV, EXP)
    runner._sessions = sessions = ScriptedSessions(
        [ok, ok, wrong], objects={"ContentSource": general_row(), "JobRun": jobrun()}
    )
    result = runner.run(general_row())
    assert result.status == "failed" and "general_source_in_experiment_database" in result.error
    end = sessions.opened[2]
    assert end.gets == [] and sessions.objects["JobRun"].status == "running"


def test_an_expired_policy_at_save_time_closes_the_run_on_the_experiment_database(monkeypatch):
    from tests.experiment_helpers import WINDOW

    install(monkeypatch, policy_for([exp_source()]))
    fetcher = FakeFetcher({FEED: ONE_ITEM})
    runner = Collector(ScriptedEngine(EXP, [EXP]), fetcher, adapters(), RobotsPolicy(fetcher))
    runner._sessions = sessions = ScriptedSessions(
        [FakeConnection()], objects={"ContentSource": experiment_row(), "JobRun": jobrun()}
    )
    original = runner._fetch

    def fetch_then_expire(source):
        batch = original(source)
        monkeypatch.setattr(ep, "now", lambda: WINDOW[1])  # expires during the request
        return batch

    runner._fetch = fetch_then_expire
    result = runner.run(experiment_row())
    assert result.status == "failed" and "outside_policy_window" in result.error
    start, store, end = sessions.opened
    assert store.added == [] and sessions.objects["JobRun"].status == "failed"


# --- 2b. summarize -----------------------------------------------------------------------


class ExplodingModel:
    model = "never"

    def complete(self, request):
        raise AssertionError("a model was called")


def candidate():
    source = SimpleNamespace(
        slug="plain-news", kind="news", ai_summary=True, options={"terms": "approved"}
    )
    return SimpleNamespace(id=1, url="https://news.example.invalid/a", title="T", source=source)


def test_summarize_cli_refuses_a_mismatched_first_connection_before_reading_or_a_client(
    monkeypatch, tmp_path, capsys
):
    body = tmp_path / "body.html"
    body.write_text("<p>article</p>")
    reads = []
    real_read = type(body).read_text
    monkeypatch.setattr(
        type(body), "read_text", lambda self, *a, **k: reads.append(self) or real_read(self)
    )
    monkeypatch.setattr(cli, "get_settings", lambda: make_settings())
    monkeypatch.setattr(cli, "create_db_engine", lambda settings: ScriptedEngine(DEV, [EXP]))
    monkeypatch.setattr(cli, "gemini_client", lambda settings: pytest.fail("client created"))
    code = cli.main(["summarize", "--body", f"https://x.example.invalid/1={body}"])
    assert code == 2 and "summaries_refused_in_experiment_database" in capsys.readouterr().err
    assert reads == []


def test_a_mismatched_candidate_session_reaches_no_body_or_model(monkeypatch):
    sessions = ScriptedSessions([FakeConnection(DEV, EXP)])
    monkeypatch.setattr(summarize_module, "sessionmaker", lambda **kw: sessions)
    bodies = []
    with pytest.raises(ep.PolicyError, match="summaries_refused_in_experiment_database"):
        summarize_module.summarize_contents(
            ScriptedEngine(DEV, [DEV]), ExplodingModel(), lambda i: bodies.append(i)
        )
    assert bodies == [] and sessions.opened[0].added == []


def test_a_mismatched_write_session_stores_no_summary(monkeypatch):
    sessions = ScriptedSessions(
        [FakeConnection(DEV, DEV), FakeConnection(DEV, EXP)],
        results={0: [[candidate()], []]},
    )
    monkeypatch.setattr(summarize_module, "sessionmaker", lambda **kw: sessions)

    class FakeSummarizer:
        def __init__(self, client, budget):
            pass

        def input_hash_of(self, request):
            return "h" * 64

        def summarize(self, request):
            return SimpleNamespace(
                status="done",
                payload={},
                partial_input=False,
                input_hash="h" * 64,
                model="fake",
                skip_reason=None,
                error_code=None,
            )

    monkeypatch.setattr(summarize_module, "Summarizer", FakeSummarizer)
    with pytest.raises(ep.PolicyError, match="summaries_refused_in_experiment_database"):
        summarize_module.summarize_contents(
            ScriptedEngine(DEV, [DEV]), ExplodingModel(), lambda i: ("html", "<p>x</p>")
        )
    write = sessions.opened[1]
    assert write.added == [] and write.gets == []


# --- 3. RSS-only grants ----------------------------------------------------------------------


def devto_source():
    return exp_source(
        slug="exp-devto",
        adapter="devto",
        feed_url=None,
        site_url="https://dev.example.invalid/",
        options={"scope": "trial-1", "terms": "approved"},
    )


@pytest.mark.parametrize(
    "grant_changes",
    [
        {"adapter": "devto", "feed_url": None},  # the reproduced API path
        {"adapter": "devto"},
        {"feed_url": None},
        {"feed_url": "ftp://exp-blog.example.invalid/feed.xml"},
        {"feed_url": "https://user:pw@exp-blog.example.invalid/feed.xml"},
        {"feed_url": "feed.xml"},
    ],
)
def test_only_rss_grants_with_a_valid_feed_url_are_valid(monkeypatch, grant_changes):
    (policy,) = policy_for([exp_source()]).values()
    grant = policy.sources["exp-blog"]
    bad = {
        policy.scope: ep.ExperimentPolicy(
            **(
                policy.__dict__
                | {"sources": {"exp-blog": ep.SourceGrant(**(grant.__dict__ | grant_changes))}}
            )
        )
    }
    install(monkeypatch, bad)
    with pytest.raises(ep.PolicyError, match="invalid_policy"):
        ep.grant_for(experiment_row())


def test_a_devto_experiment_is_neither_loaded_nor_requested(monkeypatch):
    install(monkeypatch, policy_for([devto_source()]))
    loader = FakeSession(FakeConnection())
    with pytest.raises(ep.PolicyError, match="invalid_policy"):
        apply_sources(loader, SourcesFile.model_validate(as_file(devto_source())))
    assert loader.added == [] and loader.flushes == 0

    definition = SourcesFile.model_validate(as_file(devto_source())).sources[0]
    row = SimpleNamespace(**(definition.model_dump() | {"id": 9, "status": "active"}))
    fetcher = FakeFetcher({})
    runner = Collector(ScriptedEngine(EXP, [EXP]), fetcher, adapters(), RobotsPolicy(fetcher))
    with pytest.raises(ep.PolicyError, match="invalid_policy"):
        runner.fetch(row)
    assert fetcher.calls == []  # no robots.txt, no feed, no API request


def test_rss_grants_keep_working(monkeypatch):
    install(monkeypatch, policy_for([exp_source()]))
    assert ep.grant_for(experiment_row()).adapter == "rss"
