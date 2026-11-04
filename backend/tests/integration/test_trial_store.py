"""Manual trial saving on the test database (synthetic fixtures, fake fetcher).

The test database is devhub_test, so the real connection check must refuse it before
any write; the storing itself is then exercised with the check replaced, to show that
a second save of the same URLs adds no rows and that `collect` never picks the trial
sources up.
"""

import copy
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml
from sqlalchemy import text

from app.content_loader.taxonomy import TechnologiesFile, apply_technologies
from app.db.session import create_session_factory
from app.jobs import __main__ as cli
from app.jobs import trial
from tests.collect_helpers import TECHNOLOGIES, FakeFetcher, seed_catalog

pytestmark = pytest.mark.integration

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "trial"
ALLOW = b"User-agent: *\nAllow: /\n"
INSIDE = datetime(2026, 10, 22, tzinfo=UTC)  # inside the example window


def manifest() -> trial.Manifest:
    data = yaml.safe_load((FIXTURES / "manifest.example.yaml").read_text(encoding="utf-8"))
    return trial.Manifest.model_validate(data)


def prepared():
    fetcher = FakeFetcher(
        {
            "https://cloud.example.invalid/robots.txt": ALLOW,
            "https://devlog.example.invalid/robots.txt": ALLOW,
            "https://cloud.example.invalid/more/notices/1001": (
                FIXTURES / "notice.html"
            ).read_bytes(),
            "https://devlog.example.invalid/feed.xml": (FIXTURES / "feed.atom.xml").read_bytes(),
        }
    )
    return trial.fetch_items(manifest(), fetcher, lambda: INSIDE)[0]


def rows(engine, sql: str):
    with engine.connect() as connection:
        return connection.execute(text(sql)).all()


@pytest.fixture()
def catalog(clean_db):
    technologies = copy.deepcopy(TECHNOLOGIES)
    technologies["technologies"].append(
        {"slug": "kafka", "name": "Kafka", "kind": "tool", "aliases": ["kafka"]}
    )
    with create_session_factory(clean_db).begin() as db:
        apply_technologies(db, TechnologiesFile.model_validate(technologies))
    return clean_db


def save(engine, check=trial.check_connection, clock=lambda: INSIDE):
    items = prepared()
    with create_session_factory(engine)() as db, db.begin():
        return trial.save(db, manifest(), items, connection_check=check, clock=clock)


def test_the_real_check_refuses_the_test_database_and_nothing_is_written(catalog):
    with pytest.raises(trial.TrialRefused) as refused:
        save(catalog)
    assert refused.value.code == "not_the_experiment_database"
    assert rows(catalog, "SELECT COUNT(*) FROM content_sources")[0][0] == 0
    assert rows(catalog, "SELECT COUNT(*) FROM contents")[0][0] == 0


def test_a_second_save_of_the_same_urls_adds_no_rows(catalog):
    def allow(connection):  # stands for the experiment database (checked above)
        return None

    first = save(catalog, allow)
    assert [(r.inserted, r.updated) for r in first] == [(1, 0), (1, 0)]
    second = save(catalog, allow)
    assert [r.inserted for r in second] == [0, 0]

    stored = rows(
        catalog,
        "SELECT s.slug, s.status, s.options, c.url, c.excerpt, c.author, c.source_tags"
        " FROM contents c JOIN content_sources s ON s.id = c.source_id ORDER BY s.slug",
    )
    assert [r.url for r in stored] == [
        "https://cloud.example.invalid/more/notices/1001",
        "https://devlog.example.invalid/posts/kafka-delivery/",
    ]
    assert all(r.status == "paused" for r in stored)
    assert all('"unverified"' in r.options and "kafka-pair-example" in r.options for r in stored)
    assert all(r.excerpt is None for r in stored)
    assert [r.author for r in stored] == [None, "example-author"]
    assert all(r.source_tags in ("[]", []) for r in stored)
    assert rows(catalog, "SELECT COUNT(*) FROM content_sources")[0][0] == 2
    tags = rows(
        catalog,
        "SELECT t.slug FROM content_technologies ct JOIN technologies t"
        " ON t.id = ct.technology_id ORDER BY t.slug",
    )
    assert {t.slug for t in tags} == {"kafka"}


def test_collect_never_requests_or_writes_for_trial_sources(
    catalog, integration_settings, monkeypatch, capsys
):
    save(catalog, lambda connection: None)
    before = rows(catalog, "SELECT COUNT(*) FROM contents")[0][0]
    fetcher = FakeFetcher({})
    fetcher.close = lambda: None
    monkeypatch.setattr(cli, "HttpFetcher", lambda settings: fetcher)
    monkeypatch.setattr(cli, "get_settings", lambda: integration_settings)

    assert cli.main(["collect"]) == 0
    assert cli.main(["collect", "--source", "trial-example-devlog"]) == 0
    out = capsys.readouterr().out
    assert fetcher.calls == []
    assert "trial-example-devlog" in out and "refused" in out
    assert rows(catalog, "SELECT COUNT(*) FROM contents")[0][0] == before
    assert rows(catalog, "SELECT COUNT(*) FROM job_runs")[0][0] == 0


def test_a_slug_held_by_another_source_is_refused(catalog):
    seed_catalog(
        catalog,
        technologies=TECHNOLOGIES,
        sources={
            "sources": [
                {
                    "slug": "trial-example-cloud",
                    "name": "Someone else",
                    "kind": "news",
                    "adapter": "rss",
                    "language": "ko",
                    "site_url": "https://other.example.invalid/",
                    "feed_url": "https://other.example.invalid/rss",
                }
            ]
        },
    )
    with pytest.raises(trial.TrialRefused) as refused:
        save(catalog, lambda connection: None)
    assert refused.value.code == "source_slug_belongs_to_something_else"
    assert rows(catalog, "SELECT COUNT(*) FROM contents")[0][0] == 0


EXPIRED = datetime(2026, 10, 23, tzinfo=UTC)
COUNTS = (
    "SELECT (SELECT COUNT(*) FROM content_sources), (SELECT COUNT(*) FROM contents),"
    " (SELECT COUNT(*) FROM content_technologies)"
)


def nothing_left(engine) -> bool:
    return tuple(rows(engine, COUNTS)[0]) == (0, 0, 0)


def test_expiry_between_items_rolls_back_every_write(catalog):
    """The first item is written and flushed, then the window ends before the second:
    the refusal rolls the first item's rows back with the rest of the transaction."""
    items = prepared()
    seen = []  # (sources, contents, links) as the writing session sees them, per check
    with create_session_factory(catalog)() as db:

        def clock():
            seen.append(tuple(db.execute(text(COUNTS)).one()))
            return INSIDE if len(seen) < 3 else EXPIRED  # 1: after the connection check

        with pytest.raises(trial.TrialRefused) as refused, db.begin():
            trial.save(db, manifest(), items, connection_check=lambda c: None, clock=clock)

    assert refused.value.code == "trial_expired"
    # checks: after the connection check, before item 1, before item 2 (expired)
    assert seen[:2] == [(0, 0, 0), (0, 0, 0)]
    assert seen[2][:2] == (1, 1) and seen[2][2] >= 1  # item 1 flushed, tagged
    assert nothing_left(catalog)


def trial_routes() -> dict:
    return {
        "https://cloud.example.invalid/robots.txt": ALLOW,
        "https://devlog.example.invalid/robots.txt": ALLOW,
        "https://cloud.example.invalid/more/notices/1001": (FIXTURES / "notice.html").read_bytes(),
        "https://devlog.example.invalid/feed.xml": (FIXTURES / "feed.atom.xml").read_bytes(),
    }


def run_trial(engine, expire_at_call: int | None, seen: list | None = None):
    """trial.run on the test database with the connection check replaced; the clock
    answers INSIDE until call `expire_at_call` (1-based), then EXPIRED. `seen` collects
    (sources, contents, links) as the writing session sees them at each clock call
    once the session is open. Returns (report, clock calls)."""
    factory = create_session_factory(engine)
    opened = []

    def sessions():
        opened.append(factory())
        return opened[-1]

    calls = []
    seen = seen if seen is not None else []

    def clock():
        calls.append(1)
        if opened:
            seen.append(tuple(opened[-1].execute(text(COUNTS)).one()))
        expired = expire_at_call is not None and len(calls) >= expire_at_call
        return EXPIRED if expired else INSIDE

    result = trial.run(
        manifest(),
        FakeFetcher(trial_routes()),
        engine=engine,
        sessions=sessions,
        clock=clock,
        connection_check=lambda connection: None,
    )
    return result, len(calls)


# Clock calls in a saving run: 1 start, 4 requests, 1 after the connection check,
# 2 before each item's first write, 1 after the last save (before the commit).
LAST_CALL = 9


def test_a_run_inside_the_window_commits(catalog):
    report, calls = run_trial(catalog, expire_at_call=None)
    assert calls == LAST_CALL
    assert [r.inserted for r in report.stored] == [1, 1]
    assert tuple(rows(catalog, COUNTS)[0])[:2] == (2, 2)


def test_expiry_right_after_the_last_save_commits_nothing(catalog):
    """Both items are saved and flushed; the window ends at the check after the last
    save, and the rollback leaves no source, content or technology link."""
    seen = []
    with pytest.raises(trial.TrialRefused) as refused:
        run_trial(catalog, expire_at_call=LAST_CALL, seen=seen)
    assert refused.value.code == "trial_expired"
    sources, contents, links = seen[-1]  # at the last check, before the rollback
    assert (sources, contents) == (2, 2) and links >= 1
    assert nothing_left(catalog)


def test_expiry_before_the_first_write_writes_nothing(catalog):
    expired = datetime(2026, 10, 23, tzinfo=UTC) + timedelta(seconds=1)
    with pytest.raises(trial.TrialRefused) as refused:
        save(catalog, lambda connection: None, clock=lambda: expired)
    assert refused.value.code == "trial_expired"
    assert rows(catalog, "SELECT COUNT(*) FROM content_sources")[0][0] == 0
