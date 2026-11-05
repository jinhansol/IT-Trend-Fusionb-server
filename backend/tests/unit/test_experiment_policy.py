"""Experiment policy (A1): identity, window, actions, fields and the database in use.

Synthetic policies only; the shipped registry stays empty. No database or network.
"""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.integrations.sources import CollectedItem
from app.services import experiment_policy as ep

START = datetime(2026, 11, 10, tzinfo=UTC)
END = START + timedelta(days=14)
DURING = START + timedelta(days=1)
FEED = "https://blog.example.invalid/feed.xml"
SITE = "https://blog.example.invalid/"


def grant(**changes) -> ep.SourceGrant:
    values = {
        "slug": "exp-blog",
        "adapter": "rss",
        "kind": "blog",
        "language": "ko",
        "site_url": SITE,
        "feed_url": FEED,
        "actions": frozenset({"metadata_read", "metadata_store"}),
    }
    return ep.SourceGrant(**(values | changes))


def policies(scope="trial-1", **changes) -> dict:
    values = {
        "scope": scope,
        "database": ep.EXPERIMENT_DATABASE,
        "starts_at": START,
        "expires_at": END,
        "basis_ref": "docs/devhub-2.0/basis/trial-1.md#scope",
        "sources": {"exp-blog": grant()},
    }
    return {scope: ep.ExperimentPolicy(**(values | changes))}


def source(**changes):
    values = {
        "slug": "exp-blog",
        "adapter": "rss",
        "kind": "blog",
        "language": "ko",
        "site_url": SITE,
        "feed_url": FEED,
        "options": {"scope": "trial-1", "terms": "approved", "excerpt": False},
        "ai_summary": False,
    }
    return SimpleNamespace(**(values | changes))


def test_the_shipped_registry_is_empty_so_every_experiment_is_refused():
    assert ep.POLICIES == {}
    with pytest.raises(ep.PolicyError, match="unknown_scope"):
        ep.require(source(), "metadata_read", at=DURING)


def test_a_matching_source_inside_the_window_gets_its_grant():
    found = ep.require(source(), "metadata_read", "metadata_store", at=DURING, policies=policies())
    assert found.slug == "exp-blog"
    # Host and scheme compare case-insensitively; nothing else does.
    upper = source(feed_url="HTTPS://BLOG.example.invalid/feed.xml")
    assert ep.require(upper, "metadata_read", at=DURING, policies=policies())


@pytest.mark.parametrize(
    ("changes", "code"),
    [
        ({"options": {"terms": "approved"}}, "scope_missing"),
        ({"slug": "toss-tech"}, "scope_on_non_experiment_slug"),
        ({"options": {"scope": "other"}}, "unknown_scope"),
        ({"slug": "exp-other"}, "source_not_in_policy"),
        ({"adapter": "devto"}, "adapter_mismatch"),
        ({"kind": "news"}, "kind_mismatch"),
        ({"language": "en"}, "language_mismatch"),
        ({"site_url": "https://other.example.invalid/"}, "site_url_mismatch"),
        ({"feed_url": "https://blog.example.invalid/Feed.xml"}, "feed_url_mismatch"),
        ({"feed_url": FEED + "?all=1"}, "feed_url_mismatch"),
        ({"feed_url": "https://user:pw@blog.example.invalid/feed.xml"}, "feed_url_mismatch"),
        ({"ai_summary": True}, "ai_not_allowed_in_experiments"),
        ({"options": {"scope": "trial-1", "excerpt": True}}, "excerpt_store_not_allowed"),
        ({"options": {"scope": "trial-1", "tagging_excerpt": True}}, "excerpt_tagging_not_allowed"),
    ],
)
def test_any_difference_from_the_policy_is_refused(changes, code):
    with pytest.raises(ep.PolicyError, match=code):
        ep.require(source(**changes), "metadata_read", at=DURING, policies=policies())


@pytest.mark.parametrize(
    "moment",
    [START - timedelta(seconds=1), END, END + timedelta(days=1)],
)
def test_outside_the_window_is_refused(moment):
    with pytest.raises(ep.PolicyError, match="outside_policy_window"):
        ep.require(source(), "metadata_read", at=moment, policies=policies())


def test_the_window_starts_inclusive():
    assert ep.require(source(), "metadata_read", at=START, policies=policies())


@pytest.mark.parametrize(
    "changes",
    [
        {"database": "devhub_dev"},
        {"database": "devhub_experiment_test"},
        {"basis_ref": " "},
        {"starts_at": START.replace(tzinfo=None)},
        {"expires_at": START},
        {"sources": {"exp-blog": grant(actions=frozenset({"metadata_read", "everything"}))}},
        {"sources": {"exp-blog": grant(stored_fields=frozenset({"title"}))}},
        {"sources": {"exp-blog": grant(stored_fields=frozenset({"title", "url", "body"}))}},
        {"sources": {"exp-blog": grant(slug="blog")}},
    ],
)
def test_an_incomplete_or_wrong_policy_is_never_used(changes):
    with pytest.raises(ep.PolicyError, match="invalid_policy"):
        ep.require(source(), "metadata_read", at=DURING, policies=policies(**changes))


def test_actions_not_granted_and_the_ai_and_export_actions_are_refused():
    read_only = policies(sources={"exp-blog": grant(actions=frozenset({"metadata_read"}))})
    assert ep.require(source(), "metadata_read", at=DURING, policies=read_only)
    with pytest.raises(ep.PolicyError, match="metadata_store_not_allowed"):
        ep.require(source(), "metadata_store", at=DURING, policies=read_only)
    everything = policies(sources={"exp-blog": grant(actions=ep.ACTIONS)})
    for action in ("ai_input", "summary_store", "public_export"):
        with pytest.raises(ep.PolicyError, match=f"{action}_refused"):
            ep.require(source(), action, at=DURING, policies=everything)


def test_flags_within_the_policy_are_accepted():
    both = policies(
        sources={
            "exp-blog": grant(
                actions=frozenset({"metadata_read", "excerpt_store", "excerpt_tagging"})
            )
        }
    )
    flags = source(options={"scope": "trial-1", "excerpt": True, "tagging_excerpt": True})
    assert ep.require(flags, "metadata_read", at=DURING, policies=both)


def test_projection_keeps_only_granted_fields_and_leaves_the_input_alone():
    item = CollectedItem(
        url="https://blog.example.invalid/1",
        title="T",
        external_id="id-1",
        excerpt="desc",
        author="A",
        published_at=datetime(2026, 11, 11),
        tags=["react"],
        score=3,
        comment_count=1,
        view_count=9,
    )
    (only_basic,) = ep.project([item], grant())
    assert (only_basic.title, only_basic.url, only_basic.published_at) == (
        "T",
        item.url,
        item.published_at,
    )
    assert only_basic.excerpt == "desc"  # left to the excerpt switches
    assert (only_basic.author, only_basic.external_id, only_basic.tags) == (None, None, [])
    assert (only_basic.score, only_basic.comment_count, only_basic.view_count) == (None, None, None)
    assert item.author == "A" and item.tags == ["react"]  # original untouched

    (with_tags,) = ep.project(
        [item], grant(stored_fields=frozenset({"title", "url", "source_tags"}))
    )
    assert with_tags.tags == ["react"] and with_tags.published_at is None


# --- database identity -------------------------------------------------------------------


class FakeConnection:
    def __init__(self, configured, actual=None, fails=False):
        self.engine = SimpleNamespace(url=SimpleNamespace(database=configured))
        self.actual, self.fails = actual, fails

    def execute(self, statement):
        if self.fails:
            raise RuntimeError("mysql://user:secret@db/devhub_experiment refused")
        return SimpleNamespace(scalar=lambda: self.actual)


def test_only_the_exact_experiment_database_is_accepted():
    ep.require_experiment_connection(FakeConnection("devhub_experiment", "devhub_experiment"))


@pytest.mark.parametrize(
    ("configured", "actual"),
    [
        ("devhub_dev", "devhub_dev"),
        ("devhub_test", "devhub_test"),
        ("devhub_experiment", "devhub_dev"),  # URL says experiment, server says dev
        ("devhub_dev", "devhub_experiment"),
        ("devhub_experiment_test", "devhub_experiment_test"),
        ("devhub_experiment2", "devhub_experiment2"),
        ("devhub_experiment", None),  # no database selected
        ("devhub_experiment", ""),
        (None, None),
    ],
)
def test_any_other_or_unclear_database_is_refused(configured, actual):
    with pytest.raises(ep.PolicyError, match="not_the_experiment_database"):
        ep.require_experiment_connection(FakeConnection(configured, actual))


def test_a_failing_lookup_is_refused_without_leaking_the_url():
    with pytest.raises(ep.PolicyError) as caught:
        ep.require_experiment_connection(FakeConnection("devhub_experiment", fails=True))
    assert caught.value.code == "database_unverified"
    assert "secret" not in str(caught.value) and "mysql" not in str(caught.value)


def test_either_name_marks_the_experiment_database():
    assert ep.is_experiment_connection(FakeConnection("devhub_dev", "devhub_experiment"))
    assert ep.is_experiment_connection(FakeConnection("devhub_experiment", "devhub_dev"))
    assert not ep.is_experiment_connection(FakeConnection("devhub_test", "devhub_test"))
