"""Collector safety: robots.txt, feed dates, empty responses, the read-only diagnosis."""

import time
from datetime import datetime

import pytest

from app.content_loader.taxonomy import SourcesFile
from app.integrations.http import FetchError, InsecureRedirect
from app.integrations.robots import RobotsPolicy, check_path, parse_rules
from app.integrations.sources import feed_date, parse_feed
from app.jobs.diagnose import diagnose, largest_gap
from app.jobs.schedule import Schedule
from tests.collect_helpers import FakeFetcher

NOW = datetime(2026, 11, 3, 12, 0)


# --- robots.txt ---------------------------------------------------------------------------


def verdict(robots: str, url: str) -> bool:
    return check_path(parse_rules(robots), url).allowed


def test_longest_match_wins_and_allow_wins_a_tie():
    robots = "User-agent: *\nDisallow: /feed/\nAllow: /feed/public/\nDisallow: /x\nAllow: /x\n"
    assert not verdict(robots, "https://a.example/feed/")
    assert verdict(robots, "https://a.example/feed/public/rss.xml")
    assert verdict(robots, "https://a.example/x")
    assert verdict(robots, "https://a.example/news/rss")


def test_wildcards_and_end_anchor():
    robots = "User-agent: *\nDisallow: */feed/\nDisallow: /*.php$\n"
    assert not verdict(robots, "https://a.example/kr/feed/")
    assert not verdict(robots, "https://a.example/rss.php")
    assert verdict(robots, "https://a.example/rss.php?x=1")


def test_ambiguous_feed_rules_resolve_to_the_longer_path():
    # byline.network-style: a wildcard Disallow and a root Allow for the same feed.
    robots = "User-agent: *\nDisallow: */feed/\nAllow: /feed/\n"
    assert not verdict(robots, "https://a.example/feed/")  # "*/feed/" is longer


def test_our_own_group_replaces_the_star_group():
    robots = (
        "User-agent: GPTBot\nDisallow: /\n\n"
        "User-agent: DevHubCollector\nDisallow: /private/\n\n"
        "User-agent: *\nDisallow: /\n"
    )
    assert verdict(robots, "https://a.example/rss")
    assert not verdict(robots, "https://a.example/private/rss")
    assert verdict("User-agent: *\nDisallow:\n", "https://a.example/feed")  # empty Disallow


@pytest.mark.parametrize(
    ("answer", "allowed", "reason"),
    [
        (FetchError("HTTP 404 from x", status=404), True, "unavailable (HTTP 404)"),
        (FetchError("HTTP 403 from x", status=403), True, "unavailable (HTTP 403)"),
        (FetchError("HTTP 503 from x", status=503), False, "unreachable"),
        (FetchError("ConnectError while fetching x"), False, "unreachable"),
        (InsecureRedirect("to plain http refused"), True, "redirects to plain http"),
        (b"<!DOCTYPE html><html>lander</html>", True, "not a robots.txt file"),
    ],
)
def test_an_unreadable_robots_file(answer, allowed, reason):
    policy = RobotsPolicy(FakeFetcher({"https://a.example/robots.txt": answer}))
    result = policy.check("https://a.example/feed")
    assert result.allowed is allowed and reason in result.reason


def test_robots_is_read_once_per_host():
    fetcher = FakeFetcher({"https://a.example/robots.txt": b"User-agent: *\nDisallow: /feed/\n"})
    policy = RobotsPolicy(fetcher)
    assert not policy.check("https://a.example/feed/").allowed
    assert policy.check("https://a.example/rss.xml").allowed
    assert [url for url, _ in fetcher.calls] == ["https://a.example/robots.txt"]


# --- dates and empty responses ------------------------------------------------------------


def rss(*dates: str) -> bytes:
    items = "".join(
        f"<item><title>t{i}</title><link>https://a.example/{i}</link><pubDate>{d}</pubDate></item>"
        for i, d in enumerate(dates)
    )
    channel = f"<channel><title>x</title>{items}</channel>"
    return f'<?xml version="1.0"?><rss version="2.0">{channel}</rss>'.encode()


def test_dotted_korean_dates_are_read_per_entry():
    # Before: feedparser read every "2026.MM.DD" as 2026-11-01, so all entries looked equal.
    batch = parse_feed(rss("2026.11.02", "2026.10.29", "2026.10.13 14:30"), 30)
    assert [i.published_at for i in batch.items] == [
        datetime(2026, 11, 2),
        datetime(2026, 10, 29),
        datetime(2026, 10, 13, 14, 30),
    ]


def test_standard_dates_are_unchanged():
    batch = parse_feed(rss("Mon, 02 Nov 2026 09:30:00 +0900", "2026-11-02T01:00:00Z"), 30)
    assert [i.published_at for i in batch.items] == [
        datetime(2026, 11, 2, 0, 30),
        datetime(2026, 11, 2, 1, 0),
    ]


def test_a_missing_unreadable_or_future_date_is_none_never_the_collection_time():
    assert feed_date({}, NOW) is None
    assert feed_date({"published": "어제"}, NOW) is None
    assert feed_date({"published": "2026.13.45"}, NOW) is None
    assert feed_date({"published": "2027.01.01"}, NOW) is None  # more than a day ahead
    assert feed_date({"published": "2026.11.04"}, NOW) == datetime(2026, 11, 4)  # tolerance
    updated = time.strptime("2026-11-01", "%Y-%m-%d")
    assert feed_date({"published": "어제", "updated_parsed": updated}, NOW) == datetime(2026, 11, 1)


@pytest.mark.parametrize("body", [b"", b"   \n", b"\xef\xbb\xbf"])
def test_an_empty_response_is_a_feed_error(body):
    with pytest.raises(FetchError, match="not a readable RSS/Atom feed"):
        parse_feed(body, 30)


def test_a_feed_with_no_entries_is_not_an_error():
    assert parse_feed(rss(), 30).items == []


# --- diagnose -----------------------------------------------------------------------------

SCHEDULE = Schedule.model_validate(
    {
        "timezone": "Asia/Seoul",
        "groups": {
            "news": {"minute": 0, "hours": [2, 14]},
            "dev": {"minute": 0, "hours": [5, 11, 17, 23]},
        },
    }
)


def sources(*defs) -> list:
    base = {"kind": "news", "adapter": "rss", "language": "ko", "site_url": "https://a.example/"}
    return SourcesFile.model_validate({"sources": [base | d for d in defs]}).sources


def test_largest_gap_between_runs():
    assert largest_gap([2, 14]) == 12
    assert largest_gap([5, 11, 17, 23]) == 6
    assert largest_gap([9]) == 24


def test_diagnose_reads_feeds_without_a_database_and_respects_robots():
    listed = sources(
        {"slug": "blocked", "name": "B", "feed_url": "https://b.example/feed/", "status": "paused"},
        {"slug": "busy", "name": "N", "feed_url": "https://a.example/rss", "max_items": 3},
        {"slug": "empty", "name": "E", "feed_url": "https://a.example/empty"},
    )
    fetcher = FakeFetcher(
        {
            "https://b.example/robots.txt": b"User-agent: *\nDisallow: /feed/\n",
            # Three entries within 2 hours: a 12-hour gap would lose articles.
            "https://a.example/rss": rss(
                "Tue, 03 Nov 2026 10:00:00 +0000",
                "Tue, 03 Nov 2026 09:00:00 +0000",
                "Tue, 03 Nov 2026 08:00:00 +0000",
                "2026.10.01",
            ),
            "https://a.example/empty": b"",
        }
    )
    blocked, busy, empty = diagnose(listed, fetcher, SCHEDULE, now=NOW)

    assert (blocked.outcome, blocked.status) == ("not requested", "paused")
    assert "Disallow /feed/" in blocked.detail
    assert "https://b.example/feed/" not in [u for u, _ in fetcher.calls]

    assert (busy.items, busy.last_7d, busy.last_30d, busy.no_date) == (4, 3, 3, 0)
    assert (busy.window_hours, busy.gap_hours, busy.schedule_risk) == (2.0, 12, "risk")
    assert busy.terms == "unverified" and busy.newest == datetime(2026, 11, 3, 10)

    assert empty.outcome == "failed" and "empty response" in empty.detail
