"""HttpFetcher against httpx.MockTransport: retries, Retry-After, size cap, redirects.

No request leaves the process; sleeps are recorded instead of waited.
"""

from datetime import UTC, datetime

import httpx
import pytest

from app.integrations.http import (
    MAX_ATTEMPTS,
    MAX_REDIRECTS,
    FetchError,
    HttpFetcher,
    retry_after_seconds,
)
from tests.conftest import make_settings

FEED = "https://feeds.example.com/rss"


class Server:
    """Answers requests from a list of responses (or exceptions), one per request."""

    def __init__(self, *answers):
        self.answers = list(answers)
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        answer = self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]
        if isinstance(answer, type) and issubclass(answer, Exception):
            raise answer("simulated", request=request)
        if callable(answer):
            return answer(request)
        return answer


def fetcher(server, max_bytes=1000):
    sleeps: list[float] = []
    settings = make_settings(collector_max_response_bytes=max_bytes)
    return HttpFetcher(settings, httpx.MockTransport(server), sleep=sleeps.append), sleeps


def ok(body=b"<rss/>"):
    return httpx.Response(200, content=body)


def redirect(location, status=301):
    return httpx.Response(status, headers={"Location": location})


# --- normal responses ---------------------------------------------------------------------


def test_200_returns_the_body_and_sends_the_user_agent_and_params():
    server = Server(ok(b"hello"))
    http, sleeps = fetcher(server)

    assert http.get(FEED, {"per_page": 5}) == b"hello"
    request = server.requests[0]
    assert str(request.url) == f"{FEED}?per_page=5"
    assert request.headers["user-agent"].startswith("DevHubCollector/")
    assert sleeps == []


# --- 429 and Retry-After ------------------------------------------------------------------


def test_429_waits_for_retry_after_then_succeeds():
    server = Server(httpx.Response(429, headers={"Retry-After": "3"}), ok())
    http, sleeps = fetcher(server)

    assert http.get(FEED) == b"<rss/>"
    assert sleeps == [3.0] and len(server.requests) == 2


def test_429_without_retry_after_uses_the_backoff():
    server = Server(httpx.Response(429), ok())
    http, sleeps = fetcher(server)

    http.get(FEED)
    assert sleeps == [1.0]


def test_429_asking_for_a_long_wait_fails_at_once():
    server = Server(httpx.Response(429, headers={"Retry-After": "3600"}), ok())
    http, sleeps = fetcher(server)

    with pytest.raises(FetchError, match=r"HTTP 429 .*retry after 3600s, not waiting") as caught:
        http.get(FEED)
    assert not caught.value.retryable
    assert sleeps == [] and len(server.requests) == 1


def test_429_that_never_ends_stops_after_the_attempt_limit():
    server = Server(httpx.Response(429, headers={"Retry-After": "1"}))
    http, sleeps = fetcher(server)

    with pytest.raises(FetchError, match="HTTP 429"):
        http.get(FEED)
    assert len(server.requests) == MAX_ATTEMPTS and sleeps == [1.0] * (MAX_ATTEMPTS - 1)


def test_retry_after_accepts_seconds_and_http_dates():
    now = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
    assert retry_after_seconds("7", now) == 7.0
    assert retry_after_seconds("Fri, 30 Oct 2026 12:00:20 GMT", now) == 20.0
    assert retry_after_seconds("Fri, 30 Oct 2026 11:00:00 GMT", now) == 0.0  # already past
    assert retry_after_seconds("soon", now) is None
    assert retry_after_seconds(None, now) is None


# --- 5xx, timeouts, connection errors -----------------------------------------------------


def test_5xx_is_retried_with_a_growing_wait():
    server = Server(httpx.Response(500), httpx.Response(503), ok(b"third time"))
    http, sleeps = fetcher(server)

    assert http.get(FEED) == b"third time"
    assert sleeps == [1.0, 2.0]


def test_5xx_that_persists_fails_after_the_attempt_limit():
    server = Server(httpx.Response(503))
    http, _ = fetcher(server)

    with pytest.raises(FetchError, match=r"HTTP 503 from feeds\.example\.com/rss"):
        http.get(FEED)
    assert len(server.requests) == MAX_ATTEMPTS


@pytest.mark.parametrize("status", [400, 401, 403, 404, 410])
def test_permanent_errors_are_not_retried(status):
    server = Server(httpx.Response(status), ok())
    http, sleeps = fetcher(server)

    with pytest.raises(FetchError, match=f"HTTP {status}") as caught:
        http.get(FEED)
    assert not caught.value.retryable
    assert len(server.requests) == 1 and sleeps == []


def test_timeouts_are_retried_then_reported_without_the_query():
    server = Server(httpx.ReadTimeout)
    http, sleeps = fetcher(server)

    with pytest.raises(FetchError) as caught:
        http.get(FEED, {"key": "SECRET-KEY"})
    assert str(caught.value) == "ReadTimeout while fetching feeds.example.com/rss"
    assert len(server.requests) == MAX_ATTEMPTS and sleeps == [1.0, 2.0]


def test_a_connection_error_followed_by_success_recovers():
    server = Server(httpx.ConnectError, ok())
    http, _ = fetcher(server)

    assert http.get(FEED) == b"<rss/>"


# --- size limit ---------------------------------------------------------------------------


def test_a_declared_length_over_the_limit_is_refused():
    server = Server(ok(b"x" * 2000))
    http, _ = fetcher(server, max_bytes=1000)

    with pytest.raises(FetchError, match="exceeds the size limit") as caught:
        http.get(FEED)
    assert not caught.value.retryable


def test_a_streamed_body_over_the_limit_is_cut_off():
    def chunks():
        for _ in range(10):
            yield b"x" * 300

    server = Server(httpx.Response(200, content=chunks()))  # no Content-Length
    http, _ = fetcher(server, max_bytes=1000)

    with pytest.raises(FetchError, match="exceeds the size limit"):
        http.get(FEED)


# --- redirects ----------------------------------------------------------------------------


def test_redirects_are_followed_and_relative_locations_resolved():
    server = Server(
        redirect("/moved/rss"),
        redirect("https://cdn.example.net/rss", 308),
        ok(b"final"),
    )
    http, _ = fetcher(server)

    assert http.get(FEED) == b"final"
    assert [str(r.url) for r in server.requests] == [
        FEED,
        "https://feeds.example.com/moved/rss",
        "https://cdn.example.net/rss",
    ]


@pytest.mark.parametrize(
    ("location", "reason"),
    [
        ("http://feeds.example.com/rss", "plain http refused"),
        ("https://127.0.0.1/admin", "non-public address"),
        ("https://10.0.0.5/rss", "non-public address"),
        ("https://[::1]/rss", "non-public address"),
        ("https://169.254.169.254/latest/meta-data", "non-public address"),
        ("https://localhost/rss", "local address"),
        # Legacy IPv4 spellings the system resolver still turns into 127.0.0.1.
        ("https://2130706433/rss", "non-public address"),
        ("https://0x7f.0.0.1/rss", "non-public address"),
        ("https://127.1/rss", "non-public address"),
        ("https://[::ffff:127.0.0.1]/rss", "non-public address"),
        ("https://0.0.0.0/rss", "non-public address"),
        ("https://user:pass@feeds.example.com/rss", "credentials"),
        ("javascript:alert(1)", "invalid redirect|only http"),
        ("ftp://feeds.example.com/rss", "only http"),
    ],
)
def test_unsafe_redirects_are_refused(location, reason):
    server = Server(redirect(location), ok(b"should not be read"))
    http, sleeps = fetcher(server)

    with pytest.raises(FetchError, match=reason) as caught:
        http.get(FEED)
    assert not caught.value.retryable
    assert len(server.requests) == 1 and sleeps == []


def test_a_redirect_without_location_is_an_error():
    server = Server(httpx.Response(302))
    http, _ = fetcher(server)

    with pytest.raises(FetchError, match="without a Location"):
        http.get(FEED)


def test_redirect_loops_stop_at_the_hop_limit():
    server = Server(redirect(FEED))
    http, _ = fetcher(server)

    with pytest.raises(FetchError, match=f"more than {MAX_REDIRECTS} redirects"):
        http.get(FEED)
    assert len(server.requests) == MAX_REDIRECTS + 1


def test_http_to_https_upgrade_is_allowed():
    server = Server(redirect("https://feeds.example.com/rss"), ok())
    http, _ = fetcher(server)

    assert http.get("http://feeds.example.com/rss") == b"<rss/>"


# --- addresses refused before any request -------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "file:///etc/passwd",
        "ftp://feeds.example.com/rss",
        "http://127.0.0.1:8000/api",
        "http://192.168.0.10/rss",
        "http://2130706433/rss",
        "http://127.1/rss",
        "http://localhost/rss",
        "https://user:pw@feeds.example.com/rss",
        "not a url",
    ],
)
def test_unsafe_start_addresses_are_refused_without_a_request(url):
    server = Server(ok())
    http, _ = fetcher(server)

    with pytest.raises(FetchError):
        http.get(url)
    assert server.requests == []


# --- secrets never reach error messages ---------------------------------------------------


def test_query_strings_never_appear_in_errors():
    for answer in (httpx.Response(403), redirect("https://10.0.0.1/x?key=SECRET-KEY")):
        http, _ = fetcher(Server(answer))
        with pytest.raises(FetchError) as caught:
            http.get(FEED, {"key": "SECRET-KEY"})
        assert "SECRET-KEY" not in str(caught.value)


# --- nothing travels to the next hop but the address itself -------------------------------


def test_redirects_carry_no_cookies_credentials_or_original_query():
    server = Server(
        httpx.Response(
            302,
            headers={
                "Location": "https://other.example.org/feed",
                "Set-Cookie": "session=abc; Domain=other.example.org; Path=/",
            },
        ),
        httpx.Response(200, content=b"ok", headers={"Set-Cookie": "track=1; Path=/"}),
    )
    http, _ = fetcher(server)

    http.get(FEED, {"key": "SECRET-KEY"})
    http.get("https://other.example.org/feed")  # a later request to the same site

    hop, later = server.requests[1], server.requests[2]
    assert str(hop.url) == "https://other.example.org/feed"  # the original query is not added
    for request in (hop, later):
        assert "cookie" not in request.headers
        assert "authorization" not in request.headers
    assert set(server.requests[0].headers) <= {
        "host",
        "accept",
        "accept-encoding",
        "connection",
        "user-agent",
    }


def test_public_host_names_and_addresses_are_allowed():
    server = Server(ok())
    http, _ = fetcher(server)

    for url in ("https://8.8.8.8/rss", "https://1e100.net/rss", "https://123.example.com/rss"):
        http.get(url)
    assert len(server.requests) == 3
