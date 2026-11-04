"""Re-tagging keeps tags set by hand (A2).

content_technologies has one row per (content, technology) with a method. The collector
owns only the "rule" rows: when an item's text changes it deletes them and inserts the
new matches. A row with another method (a hand-set "manual" tag) is never deleted or
overwritten, and a rule match for the same technology is not inserted next to it.
Before this fix that insert hit the primary key and failed the whole source run.

Uses the dedicated test database (clean_db) and stored sample feeds; no network.
"""

import pytest
from sqlalchemy import text

from tests.collect_helpers import collect_all, fixture, sample_routes, seed_catalog

pytestmark = pytest.mark.integration

NEWS_FEED = "https://news.example.com/rss"
PYTHON_ARTICLE = "https://news.example.com/articles/1"
PYTHON_TITLE = "파이썬 3.14 출시".encode()
# The title changes but still names Python: the item is re-tagged, python matches again.
RETITLED = (PYTHON_TITLE, "파이썬 3.14 정식 출시".encode())
# Title and description now name Rust only: python no longer matches.
NOW_RUST = (
    (PYTHON_TITLE, "Rust 1.90 출시".encode()),
    ("Python 3.14가".encode(), "Rust 1.90이".encode()),
)


def run(engine, *changes: tuple[bytes, bytes]):
    """Collect the sample feed once, with (old, new) text replacements applied."""
    routes = sample_routes()
    feed = fixture("news.rss.xml")
    for old, new in changes:
        assert old in feed
        feed = feed.replace(old, new)
    routes[NEWS_FEED] = feed
    return collect_all(engine, routes)["sample-news"]


def tags(engine, url: str = PYTHON_ARTICLE) -> set[tuple[str, str]]:
    with engine.connect() as connection:
        return set(
            connection.execute(
                text(
                    "SELECT t.slug, ct.method FROM content_technologies ct "
                    "JOIN contents c ON c.id = ct.content_id "
                    "JOIN technologies t ON t.id = ct.technology_id WHERE c.url = :url"
                ),
                {"url": url},
            ).all()
        )


def all_tag_rows(engine) -> list[tuple]:
    with engine.connect() as connection:
        return sorted(
            tuple(r)
            for r in connection.execute(
                text("SELECT content_id, technology_id, method FROM content_technologies")
            )
        )


def set_manual(engine, slug: str, url: str = PYTHON_ARTICLE) -> None:
    """A hand-set tag: turns the rule row into manual, or adds a manual row."""
    with engine.begin() as connection:
        ids = {
            "content": connection.execute(
                text("SELECT id FROM contents WHERE url = :url"), {"url": url}
            ).scalar_one(),
            "tech": connection.execute(
                text("SELECT id FROM technologies WHERE slug = :slug"), {"slug": slug}
            ).scalar_one(),
        }
        connection.execute(
            text(
                "INSERT INTO content_technologies (content_id, technology_id, method) "
                "VALUES (:content, :tech, 'manual') "
                "ON DUPLICATE KEY UPDATE method = 'manual'"
            ),
            ids,
        )


@pytest.fixture()
def collected(clean_db):
    seed_catalog(clean_db)
    assert run(clean_db).status == "succeeded"
    assert tags(clean_db) == {("python", "rule")}
    return clean_db


def test_a_manual_tag_for_a_technology_the_rules_also_match_is_kept(collected):
    set_manual(collected, "python")
    # A changed title makes the collector re-tag the item; the rules match python again.
    result = run(collected, RETITLED)
    assert result.status == "succeeded", result.error
    assert result.updated == 1
    assert tags(collected) == {("python", "manual")}  # one row, still manual


def test_recollecting_without_manual_tags_still_refreshes_rule_tags(collected):
    result = run(collected, RETITLED)
    assert result.status == "succeeded" and result.updated == 1
    assert tags(collected) == {("python", "rule")}


def test_a_manual_tag_for_another_technology_stays_next_to_the_rule_tags(collected):
    set_manual(collected, "kubernetes")
    result = run(collected, RETITLED)
    assert result.status == "succeeded", result.error
    assert tags(collected) == {("python", "rule"), ("kubernetes", "manual")}


def test_changed_rule_results_replace_rule_tags_and_keep_manual_ones(collected):
    set_manual(collected, "kubernetes")
    result = run(collected, *NOW_RUST)
    assert result.status == "succeeded", result.error
    # python no longer matches and its rule row is gone; rust is new; manual stays.
    assert tags(collected) == {("rust", "rule"), ("kubernetes", "manual")}


def test_a_manual_tag_outlives_the_rule_match_that_it_replaced(collected):
    set_manual(collected, "python")
    result = run(collected, *NOW_RUST)
    assert result.status == "succeeded", result.error
    assert tags(collected) == {("python", "manual"), ("rust", "rule")}


def test_repeated_collection_is_idempotent_with_manual_tags(collected):
    set_manual(collected, "python")
    set_manual(collected, "kubernetes")
    first = run(collected, RETITLED)
    rows = all_tag_rows(collected)
    for _ in range(2):
        again = run(collected, RETITLED)
        assert again.status == "succeeded" and (again.inserted, again.updated) == (0, 0)
        assert all_tag_rows(collected) == rows
    assert first.status == "succeeded"
    assert tags(collected) == {("python", "manual"), ("kubernetes", "manual")}


def test_other_items_and_sources_are_unaffected(collected):
    before_other = tags(collected, "https://news.example.com/articles/3")
    set_manual(collected, "python")
    run(collected, RETITLED)
    assert tags(collected, "https://news.example.com/articles/3") == before_other
    assert ("security", "rule") in before_other
