"""Experiment boundaries on the dedicated test database (A1).

devhub_test is never the experiment database, so every experiment step here must be
refused and leave the data as it was. Experiment rows are inserted directly through the
ORM where a test needs them (as if loaded by hand), to prove the later stages do not
trust what the loader would have checked. No network: FakeFetcher answers locally.
"""

import copy

import pytest
import yaml
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app.content_loader import __main__ as loader_cli
from app.content_loader.taxonomy import SourcesFile, apply_sources
from app.db.session import create_session_factory
from app.jobs import __main__ as cli
from app.main import create_app
from app.models.content import Content, ContentSource, ContentSummary
from app.services.experiment_policy import PolicyError
from app.services.source_terms import ai_summary_allowed
from tests.collect_helpers import (
    SOURCES,
    FakeFetcher,
    collect_all,
    fixture,
    sample_routes,
    seed_catalog,
)
from tests.experiment_helpers import WINDOW, as_file, exp_news, exp_source, install, policy_for
from tests.integration.test_content_api import shift_dates_to_now
from tests.summary_helpers import NEWS_KO

pytestmark = pytest.mark.integration

EXP_FEED = "https://exp-blog.example.invalid/feed.xml"


def table(engine, sql):
    with engine.connect() as connection:
        return sorted(tuple(r) for r in connection.execute(text(sql)))


def sources_state(engine):
    return table(engine, "SELECT slug, status, options FROM content_sources")


def insert_experiment_row(engine, **changes) -> int:
    """An experiment source row as a hand-made load would leave it."""
    values = SourcesFile.model_validate(as_file(exp_source(**changes))).sources[0].model_dump()
    with create_session_factory(engine).begin() as db:
        row = ContentSource(**(values | {"position": 99}))
        db.add(row)
        db.flush()
        return row.id


@pytest.fixture()
def seeded(clean_db):
    seed_catalog(clean_db)
    return clean_db


# --- loader ----------------------------------------------------------------------------


def test_an_experiment_file_is_refused_by_the_test_database(seeded, monkeypatch):
    install(monkeypatch, policy_for([exp_source(), exp_news()]))
    before = sources_state(seeded)
    content = SourcesFile.model_validate(as_file(exp_source(), exp_news()))
    with create_session_factory(seeded)() as db, pytest.raises(PolicyError) as caught:
        apply_sources(db, content)
    assert caught.value.code == "not_the_experiment_database"
    assert sources_state(seeded) == before  # nothing added, nothing retired


def test_the_loader_cli_refuses_even_a_dry_run(
    seeded, monkeypatch, tmp_path, capsys, integration_settings
):
    install(monkeypatch, policy_for([exp_source()]))
    path = tmp_path / "renamed-general.yaml"
    path.write_text(yaml.safe_dump(as_file(exp_source()), allow_unicode=True))
    monkeypatch.setattr(loader_cli, "get_settings", lambda: integration_settings)
    before = sources_state(seeded)
    for args in (["sources", str(path), "--dry-run"], ["sources", str(path)]):
        assert loader_cli.main(args) == 1
        assert "not_the_experiment_database" in capsys.readouterr().err
    assert sources_state(seeded) == before


def test_a_general_reload_refuses_a_database_with_experiment_rows(seeded):
    insert_experiment_row(seeded)
    before = sources_state(seeded)
    with pytest.raises(PolicyError, match="experiment_rows_in_general_database"):
        seed_catalog(seeded)
    assert sources_state(seeded) == before  # the experiment row is not retired either


def test_general_loading_and_retiring_are_unchanged(seeded):
    smaller = copy.deepcopy(SOURCES)
    smaller["sources"] = smaller["sources"][:2]
    seed_catalog(seeded, sources=smaller)
    statuses = dict(table(seeded, "SELECT slug, status FROM content_sources"))
    assert statuses["sample-news"] == "active" and statuses["sample-blog"] == "retired"


# --- collect, scheduled collect and diagnose ------------------------------------------------


@pytest.fixture()
def fake_network(monkeypatch, integration_settings):
    fetcher = FakeFetcher(sample_routes() | {EXP_FEED: fixture("blog.atom.xml")})
    fetcher.close = lambda: None
    monkeypatch.setattr(cli, "HttpFetcher", lambda settings: fetcher)
    monkeypatch.setattr(cli, "get_settings", lambda: integration_settings)
    return fetcher


def job_runs(engine):
    return table(engine, "SELECT COUNT(*) FROM job_runs")[0][0]


def test_collect_refuses_an_experiment_row_and_still_collects_general_ones(
    seeded, fake_network, monkeypatch, capsys
):
    insert_experiment_row(seeded)
    install(monkeypatch, policy_for([exp_source()]))
    assert cli.main(["collect", "--source", "exp-blog"]) == 1
    out = capsys.readouterr().out
    assert "exp-blog" in out and "not_the_experiment_database" in out
    assert fake_network.calls == [] and job_runs(seeded) == 0

    assert cli.main(["collect"]) == 1  # the refusal is reported as a failure
    requested = {url for url, _ in fake_network.calls}
    assert EXP_FEED not in requested and "https://news.example.com/rss" in requested
    assert table(
        seeded,
        "SELECT COUNT(*) FROM contents c JOIN content_sources s "
        "ON s.id = c.source_id WHERE s.slug = 'exp-blog'",
    ) == [(0,)]


def test_scheduled_collect_refuses_an_expired_experiment(
    seeded, fake_network, monkeypatch, tmp_path, capsys
):
    insert_experiment_row(seeded)
    install(monkeypatch, policy_for([exp_source()]), at=WINDOW[1])
    schedule = tmp_path / "schedule.yaml"
    schedule.write_text(
        "timezone: Asia/Seoul\ngroups:\n"
        "  news: {minute: 0, hours: [2], sources: []}\n"
        "  dev: {minute: 0, hours: [5], sources: [exp-blog]}\n"
    )
    assert cli.main(["collect", "--group", "dev", "--schedule", str(schedule)]) == 1
    assert "outside_policy_window" in capsys.readouterr().out
    assert fake_network.calls == [] and job_runs(seeded) == 0


def test_experiment_diagnose_is_refused_by_the_test_database(
    seeded, fake_network, monkeypatch, tmp_path, capsys
):
    install(monkeypatch, policy_for([exp_source()]))
    path = tmp_path / "copy.yaml"
    path.write_text(yaml.safe_dump(as_file(exp_source()), allow_unicode=True))
    assert cli.main(["diagnose", "--sources-file", str(path)]) == 1
    assert "not_the_experiment_database" in capsys.readouterr().out
    assert fake_network.calls == []


# --- excerpt tagging for general sources ------------------------------------------------------

QUIET_FEED = (
    b'<?xml version="1.0"?><rss version="2.0"><channel><title>x</title>'
    b"<item><title>Weekly notes</title><link>https://news.example.com/w1</link>"
    b"<description>Kubernetes upgrade notes</description>"
    b"<pubDate>Sun, 01 Nov 2026 09:00:00 +0000</pubDate></item></channel></rss>"
)


def tags_of(engine, url):
    return table(
        engine,
        "SELECT t.slug FROM content_technologies ct JOIN contents c ON c.id = ct.content_id "
        f"JOIN technologies t ON t.id = ct.technology_id WHERE c.url = '{url}'",
    )


@pytest.mark.parametrize(("flag", "expected"), [(None, [("kubernetes",)]), (False, [])])
def test_general_sources_can_turn_off_excerpt_tagging(clean_db, flag, expected):
    data = copy.deepcopy(SOURCES)
    if flag is not None:
        data["sources"][0]["options"]["tagging_excerpt"] = flag
    seed_catalog(clean_db, sources=data)
    collect_all(clean_db, sample_routes() | {"https://news.example.com/rss": QUIET_FEED})
    assert tags_of(clean_db, "https://news.example.com/w1") == expected


# --- AI ---------------------------------------------------------------------------------------


def test_the_sql_gate_excludes_experiment_rows(seeded):
    with create_session_factory(seeded).begin() as db:
        news = db.scalar(select(ContentSource).where(ContentSource.slug == "sample-news"))
        news.ai_summary = True
    insert_experiment_row(seeded, kind="news", channel=None, channel_name=None)
    with seeded.begin() as connection:  # ai_summary set by hand on the experiment row
        connection.execute(
            text("UPDATE content_sources SET ai_summary = 1 WHERE slug LIKE 'exp-%'")
        )
    with create_session_factory(seeded)() as db:
        allowed = list(db.scalars(select(ContentSource.slug).where(ai_summary_allowed())))
    assert allowed == ["sample-news"]


def test_an_experiment_summary_is_never_shown_for_the_same_link(seeded, integration_settings):
    with create_session_factory(seeded).begin() as db:
        db.scalar(
            select(ContentSource).where(ContentSource.slug == "sample-news")
        ).ai_summary = True
    collect_all(seeded)
    shift_dates_to_now(seeded)
    exp_id = insert_experiment_row(seeded, kind="news", channel=None, channel_name=None)
    with create_session_factory(seeded).begin() as db:
        general = db.scalar(select(Content).where(Content.url.like("%/articles/2")))
        copy_row = Content(
            source_id=exp_id,
            url=general.url,
            url_hash=general.url_hash,
            title="copied",
            summary_status="pending",
        )
        db.add(copy_row)
        db.flush()
        db.add(
            ContentSummary(
                content_id=copy_row.id,
                kind="news",
                status="done",
                payload=NEWS_KO,
                partial_input=False,
                input_hash="0" * 64,
                prompt_version="test",
                attempts=1,
            )
        )
    with TestClient(create_app(integration_settings)) as client:
        items = client.get("/api/news").json()["items"]
    article = next(i for i in items if i["url"].endswith("/articles/2"))
    assert article["ai_summary"] is None
