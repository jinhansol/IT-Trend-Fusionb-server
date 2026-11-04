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


def test_expiry_between_items_rolls_back_every_write(catalog):
    """The window is checked before each item's first write: the second item finds the
    trial expired, and the first item's flushed rows are rolled back with it."""
    times = iter([INSIDE, datetime(2026, 10, 23, tzinfo=UTC)])
    with pytest.raises(trial.TrialRefused) as refused:
        save(catalog, lambda connection: None, clock=lambda: next(times))
    assert refused.value.code == "trial_expired"
    assert rows(catalog, "SELECT COUNT(*) FROM content_sources")[0][0] == 0
    assert rows(catalog, "SELECT COUNT(*) FROM contents")[0][0] == 0
    assert rows(catalog, "SELECT COUNT(*) FROM content_technologies")[0][0] == 0


def test_expiry_before_the_first_write_writes_nothing(catalog):
    expired = datetime(2026, 10, 23, tzinfo=UTC) + timedelta(seconds=1)
    with pytest.raises(trial.TrialRefused) as refused:
        save(catalog, lambda connection: None, clock=lambda: expired)
    assert refused.value.code == "trial_expired"
    assert rows(catalog, "SELECT COUNT(*) FROM content_sources")[0][0] == 0
