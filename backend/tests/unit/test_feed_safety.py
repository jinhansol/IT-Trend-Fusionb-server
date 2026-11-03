"""Collector safety: robots.txt, feed dates, empty responses, the read-only diagnosis."""

import time
from datetime import datetime

import httpx
import pytest

from app.content_loader.taxonomy import SourcesFile
from app.integrations.http import FetchError, HttpFetcher, InsecureRedirect
from app.integrations.robots import (
    MAX_ROBOTS_BYTES,
    RobotsPolicy,
    check_path,
    guard_redirects,
    parse_rules,
)
from app.integrations.sources import feed_date, parse_feed
from app.jobs.diagnose import diagnose, largest_gap
from app.jobs.schedule import Schedule
from tests.collect_helpers import FakeFetcher
from tests.conftest import make_settings

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
    "agent",
    ["Dev", "hub", "Collector", "c", "DevHub", "DevHubCollectorBot", "OtherDevHubCollector"],
)
def test_another_crawlers_group_never_replaces_the_star_group(agent):
    # Before: "a in token" let "Dev", "hub" or "c" select a group meant for another bot.
    robots = f"User-agent: {agent}\nAllow: /\n\nUser-agent: *\nDisallow: /feed/\n"
    assert not verdict(robots, "https://a.example/feed/")


@pytest.mark.parametrize(
    "agent", ["DevHubCollector", "devhubcollector", "DEVHUBCOLLECTOR", "DevHubCollector/2.0"]
)
def test_our_product_token_matches_case_insensitively_as_a_whole(agent):
    robots = f"User-agent: {agent}\nAllow: /feed/\n\nUser-agent: *\nDisallow: /\n"
    assert verdict(robots, "https://a.example/feed/")


@pytest.mark.parametrize(
    ("rule", "url", "allowed"),
    [
        # A percent-encoded unreserved character is the character itself.
        ("/private/", "https://a.example/%70rivate/rss", False),
        ("/private/", "https://a.example/%70RIVATE/rss", True),  # paths are case-sensitive
        ("/%70rivate/", "https://a.example/private/rss", False),
        ("/~user/", "https://a.example/%7euser/feed", False),
        # Reserved characters stay distinct from their encodings; hex case does not matter.
        ("/a/b", "https://a.example/a%2Fb", True),
        ("/a%2fb", "https://a.example/a%2Fb", False),
        ("/q?x=1", "https://a.example/q?x=1", False),
        ("/q?x=1", "https://a.example/q%3Fx=1", True),
        # Non-ASCII paths match in either spelling.
        ("/뉴스/", "https://a.example/%EB%89%B4%EC%8A%A4/rss", False),
        ("/%EB%89%B4%EC%8A%A4/", "https://a.example/뉴스/rss", False),
        ("/%eb%89%b4%ec%8a%a4/", "https://a.example/%EB%89%B4%EC%8A%A4/rss", False),
        ("/뉴스/", "https://a.example/news/rss", True),
        # Wildcards and the end anchor keep working on normalized paths.
        ("/*/%70rivate$", "https://a.example/kr/private", False),
        ("/*.xml$", "https://a.example/%66eed.xml", False),
    ],
)
def test_paths_are_compared_after_percent_encoding_normalization(rule, url, allowed):
    assert verdict(f"User-agent: *\nDisallow: {rule}\n", url) is allowed


def test_the_longest_rule_counts_its_normalized_length():
    # "/%70ublic/" and "/public/" are the same path; the Allow (same length) wins the tie.
    robots = "User-agent: *\nDisallow: /public/\nAllow: /%70ublic/\n"
    assert verdict(robots, "https://a.example/public/rss")


@pytest.mark.parametrize(
    ("answer", "allowed", "reason"),
    [
        (FetchError("HTTP 404 from x", status=404), True, "unavailable (HTTP 404)"),
        (FetchError("HTTP 410 from x", status=410), True, "unavailable (HTTP 410)"),
        # An access restriction or throttling is never read as permission.
        (FetchError("HTTP 401 from x", status=401), False, "unreachable (HTTP 401)"),
        (FetchError("HTTP 403 from x", status=403), False, "unreachable (HTTP 403)"),
        (FetchError("HTTP 429 from x", status=429), False, "unreachable (HTTP 429)"),
        (FetchError("HTTP 503 from x", status=503), False, "unreachable (HTTP 503)"),
        (FetchError("ConnectError while fetching x"), False, "unreachable"),
        (FetchError("response from x exceeds the size limit"), False, "unreachable"),
        (InsecureRedirect("to plain http refused"), False, "redirects to plain http"),
        (b"<!DOCTYPE html><html>lander</html>", True, "not a robots.txt file"),
    ],
)
def test_an_unreadable_robots_file(answer, allowed, reason):
    policy = RobotsPolicy(FakeFetcher({"https://a.example/robots.txt": answer}))
    result = policy.check("https://a.example/feed")
    assert result.allowed is allowed and reason in result.reason


def test_a_large_robots_file_keeps_its_rules():
    # Before: a file over the limit was treated as "no rules" and everything was allowed.
    comments = b"".join(b"# padding line %d\n" % i for i in range(60_000))  # ~1 MB
    body = b"User-agent: *\nDisallow: /feed/\n" + comments + b"Disallow: /late/\n"
    assert len(body) > MAX_ROBOTS_BYTES
    policy = RobotsPolicy(FakeFetcher({"https://a.example/robots.txt": body}))
    assert not policy.check("https://a.example/feed/").allowed
    # Rules past the first MAX_ROBOTS_BYTES (>= 500 KiB, RFC 9309 2.5) may be ignored.
    assert policy.check("https://a.example/late/").allowed
    assert MAX_ROBOTS_BYTES >= 500 * 1024


def test_robots_is_read_once_per_host():
    fetcher = FakeFetcher({"https://a.example/robots.txt": b"User-agent: *\nDisallow: /feed/\n"})
    policy = RobotsPolicy(fetcher)
    assert not policy.check("https://a.example/feed/").allowed
    assert policy.check("https://a.example/rss.xml").allowed
    assert [url for url, _ in fetcher.calls] == ["https://a.example/robots.txt"]


# --- redirects -----------------------------------------------------------------------------


class Site:
    """MockTransport handler: url -> response; records every request."""

    def __init__(self, pages: dict[str, httpx.Response]) -> None:
        self.pages, self.requested = pages, []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requested.append(str(request.url))
        return self.pages.get(str(request.url), httpx.Response(404))


def moved(location: str) -> httpx.Response:
    return httpx.Response(301, headers={"location": location})


def http_fetcher(site: Site) -> HttpFetcher:
    return HttpFetcher(make_settings(), httpx.MockTransport(site), sleep=lambda s: None)


def test_a_redirect_into_a_disallowed_path_is_not_followed():
    site = Site(
        {
            "https://a.example/robots.txt": httpx.Response(200, text="User-agent: *\n"),
            "https://a.example/rss": moved("https://b.example/private/rss"),
            "https://b.example/robots.txt": httpx.Response(
                200, text="User-agent: *\nDisallow: /private/\n"
            ),
            "https://b.example/private/rss": httpx.Response(200, text="<rss/>"),
        }
    )
    fetcher = http_fetcher(site)
    robots = RobotsPolicy(fetcher)
    assert robots.check("https://a.example/rss").allowed
    with guard_redirects(fetcher, robots), pytest.raises(FetchError, match="Disallow /private/"):
        fetcher.get("https://a.example/rss")
    assert "https://b.example/private/rss" not in site.requested
    assert fetcher.on_redirect is None  # the guard is removed afterwards


def test_an_allowed_redirect_is_followed_and_robots_redirects_are_not_guarded():
    site = Site(
        {
            "https://a.example/robots.txt": moved("https://a.example/robots-real.txt"),
            "https://a.example/robots-real.txt": httpx.Response(
                200, text="User-agent: *\nDisallow: /old/\n"
            ),
            "https://a.example/feed/": moved("https://a.example/feed"),
            "https://a.example/feed": httpx.Response(200, text="<rss/>"),
        }
    )
    fetcher = http_fetcher(site)
    robots = RobotsPolicy(fetcher)
    with guard_redirects(fetcher, robots):
        assert fetcher.get("https://a.example/feed/") == b"<rss/>"
    assert not robots.check("https://a.example/old/x").allowed  # rules came via redirect


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
