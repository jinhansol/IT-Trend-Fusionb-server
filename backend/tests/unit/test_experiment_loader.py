"""Sources loader guard (A1): which file may go into which database, checked before any
write. Fake sessions only; the dedicated test database is used in the integration file."""

import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.content_loader.taxonomy import SourcesFile, apply_sources, read_sources
from app.services.experiment_policy import PolicyError
from tests.collect_helpers import SOURCES
from tests.experiment_helpers import (
    FakeConnection,
    FakeSession,
    as_file,
    exp_news,
    exp_source,
    install,
    policy_for,
)

EXAMPLE = Path(__file__).resolve().parents[2] / "content" / "sources.experiment.example.yaml"


def experiment_file(*sources):
    return SourcesFile.model_validate(as_file(*(sources or (exp_source(), exp_news()))))


# --- the YAML markers ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("source", "message"),
    [
        (exp_source(options={"terms": "approved"}), "both a 'exp-' slug and options.scope"),
        (exp_source(slug="blog-x"), "both a 'exp-' slug and options.scope"),
        (exp_source(ai_summary=True), "cannot use ai_summary"),
        (exp_source(options={"scope": "Bad Scope"}), "String should match pattern"),
        (exp_source(options={"scope": "trial-1", "database": "devhub_experiment"}), "Extra inputs"),
        (exp_source(options={"scope": "trial-1", "actions": ["ai_input"]}), "Extra inputs"),
        (exp_source(options={"scope": "trial-1", "expires_at": "2099-01-01"}), "Extra inputs"),
    ],
)
def test_experiment_markers_and_strict_options(source, message):
    with pytest.raises(ValidationError, match=message):
        SourcesFile.model_validate(as_file(source))


def test_general_and_experiment_sources_cannot_share_a_file():
    general = SOURCES["sources"][0]
    with pytest.raises(ValidationError, match="not mixed"):
        SourcesFile.model_validate(as_file(general, exp_source()))
    other_scope = exp_news(options={"scope": "trial-2", "terms": "approved"})
    with pytest.raises(ValidationError, match="not mixed"):
        SourcesFile.model_validate(as_file(exp_source(), other_scope))


def test_general_options_keep_their_shape():
    general = SourcesFile.model_validate(as_file(SOURCES["sources"][0])).sources[0]
    assert "scope" not in general.options and "tagging_excerpt" not in general.options


# --- the database the session is really connected to -----------------------------------


def test_an_experiment_file_loads_into_the_experiment_database(monkeypatch):
    content = experiment_file()
    install(monkeypatch, policy_for([exp_source(), exp_news()]))
    db = FakeSession(FakeConnection())
    report = apply_sources(db, content)
    assert report.created == ["exp-blog", "exp-news"]
    assert [row.options["scope"] for row in db.added] == ["trial-1", "trial-1"]
    assert db.autoflush_disabled == 1


@pytest.mark.parametrize(
    ("configured", "actual"),
    [
        ("devhub_dev", "devhub_dev"),
        ("devhub_test", "devhub_test"),
        ("devhub_experiment", "devhub_dev"),
        ("devhub_dev", "devhub_experiment"),
        ("devhub_experiment_x", "devhub_experiment_x"),
        ("devhub_experiment", None),
    ],
)
def test_an_experiment_file_never_goes_elsewhere(monkeypatch, configured, actual):
    install(monkeypatch, policy_for([exp_source(), exp_news()]))
    db = FakeSession(FakeConnection(configured, actual))
    with pytest.raises(PolicyError, match="not_the_experiment_database"):
        apply_sources(db, experiment_file())
    assert db.added == [] and db.flushes == 0


@pytest.mark.parametrize(
    ("configured", "actual"),
    [("devhub_experiment", "devhub_experiment"), ("devhub_dev", "devhub_experiment")],
)
def test_a_general_file_never_goes_into_the_experiment_database(configured, actual):
    db = FakeSession(FakeConnection(configured, actual))
    with pytest.raises(PolicyError, match="general_file_in_experiment_database"):
        apply_sources(db, SourcesFile.model_validate(SOURCES))
    assert db.added == [] and db.flushes == 0


def test_a_general_file_still_loads_into_a_general_database():
    db = FakeSession(FakeConnection("devhub_dev", "devhub_dev"))
    report = apply_sources(db, SourcesFile.model_validate(SOURCES))
    assert len(report.created) == len(SOURCES["sources"]) and db.flushes == 1


def test_without_a_policy_the_example_file_is_refused_before_the_database_is_asked():
    db = FakeSession(FakeConnection())
    with pytest.raises(PolicyError, match="unknown_scope"):
        apply_sources(db, read_sources(EXAMPLE))
    assert db.added == [] and db._connection.queries == 0


def test_a_bad_source_at_the_end_stops_the_whole_file(monkeypatch):
    late = exp_news(feed_url="https://exp-news.example.invalid/other.xml")
    install(monkeypatch, policy_for([exp_source(), exp_news()]))
    db = FakeSession(FakeConnection())
    with pytest.raises(PolicyError, match="feed_url_mismatch"):
        apply_sources(db, experiment_file(exp_source(), late))
    assert db.added == [] and db.flushes == 0


def test_an_expired_policy_is_refused(monkeypatch):
    from tests.experiment_helpers import WINDOW

    install(monkeypatch, policy_for([exp_source(), exp_news()]), at=WINDOW[1])
    db = FakeSession(FakeConnection())
    with pytest.raises(PolicyError, match="outside_policy_window"):
        apply_sources(db, experiment_file())
    assert db.added == []


def row(slug, scope=None, status="active"):
    options = {"terms": "approved"} | ({"scope": scope} if scope else {})
    return SimpleNamespace(slug=slug, options=options, status=status)


@pytest.mark.parametrize(
    "existing",
    [
        row("toss-tech"),  # a general row the experiment file would retire
        row("exp-old", scope="trial-0"),  # another experiment
        row("exp-blog"),  # same slug, scope removed by hand
    ],
)
def test_an_experiment_file_never_touches_rows_of_another_scope(monkeypatch, existing):
    install(monkeypatch, policy_for([exp_source(), exp_news()]))
    db = FakeSession(FakeConnection(), rows=[existing])
    with pytest.raises(PolicyError, match="rows_of_another_scope"):
        apply_sources(db, experiment_file())
    assert db.added == [] and db.flushes == 0
    assert existing.status == "active"


def test_retired_rows_do_not_block_and_same_scope_rows_are_updated(monkeypatch):
    install(monkeypatch, policy_for([exp_source(), exp_news()]))
    db = FakeSession(FakeConnection(), rows=[row("toss-tech", status="retired")])
    assert apply_sources(db, experiment_file()).created == ["exp-blog", "exp-news"]


def test_a_general_file_refuses_a_database_holding_experiment_rows():
    stray = row("exp-blog", scope="trial-1")
    db = FakeSession(FakeConnection("devhub_dev", "devhub_dev"), rows=[stray])
    with pytest.raises(PolicyError, match="experiment_rows_in_general_database"):
        apply_sources(db, SourcesFile.model_validate(SOURCES))
    assert stray.status == "active" and db.added == []


def test_the_file_name_and_location_do_not_matter(tmp_path):
    copies = [tmp_path / "sources.yaml", tmp_path / "nested" / "general.yaml"]
    copies[1].parent.mkdir()
    for copy in copies:
        shutil.copy(EXAMPLE, copy)
    link = tmp_path / "link.yaml"
    link.symlink_to(EXAMPLE)
    for path in [*copies, link, Path("content/../content/sources.experiment.example.yaml")]:
        if not path.is_absolute():
            path = EXAMPLE.parents[1] / path
        content = read_sources(path)
        assert {s.options["scope"] for s in content.sources} == {"example-trial"}
        db = FakeSession(FakeConnection("devhub_dev", "devhub_dev"))
        with pytest.raises(PolicyError, match="unknown_scope"):
            apply_sources(db, content)
        assert db.added == []
