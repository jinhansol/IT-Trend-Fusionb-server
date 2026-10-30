"""web.dev article bodies: allowed addresses, page checks, and the fetcher's host lock."""

import httpx
import pytest

import app.integrations.http as http_module
from app.integrations.http import FetchError, HttpFetcher
from app.jobs.article_bodies import WEBDEV_HOSTS, webdev_address, webdev_body
from app.summaries.extract import extract_html
from tests.conftest import make_settings
from tests.webdev_helpers import FIRST_PAGE, FIRST_TITLE, page


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://web.dev/blog/sample-post?hl=en", "https://web.dev/blog/sample-post"),
        ("https://web.dev/blog/sample-post", "https://web.dev/blog/sample-post"),
        ("http://web.dev/blog/sample-post", None),
        ("https://evil.example/blog/sample-post", None),
        ("https://web.dev.evil.example/blog/sample-post", None),
        ("https://web.dev@evil.example/blog/sample-post", None),
        ("https://web.dev:8443/blog/sample-post", None),
        ("https://web.dev/articles/sample-post", None),
        ("https://web.dev/blog/../admin", None),
        ("https://web.dev/blog/sample-post?authuser=1", None),
        ("https://web.dev/blog/sample-post#top", None),
    ],
)
def test_only_web_dev_blog_addresses_are_fetched(url, expected):
    assert webdev_address(url) == expected


def body_of(data: bytes, url=FIRST_PAGE, title=FIRST_TITLE):
    return webdev_body(data.decode(), url, title)


def test_the_article_body_is_cut_out_of_the_page():
    body = body_of(page("sample-virtual-threads", FIRST_TITLE))
    text = extract_html(body, 12000).text
    assert "가상 스레드" in text  # the synthetic article
    for left_out in ("Sample Author", "Published:", "Home Blog Learn", "licensed under", "Share"):
        assert left_out not in text
    assert "<script" not in body and "<style" not in body


@pytest.mark.parametrize(
    ("data", "reason"),
    [
        (page("sample-virtual-threads", FIRST_TITLE, license=False), "no CC BY 4.0 notice"),
        (page("other-post", FIRST_TITLE), "canonical URL of another article"),
        (page("sample-virtual-threads", "A different article"), "another title"),
        (b"<html><body>error page</body></html>", "not an article page"),
    ],
)
def test_pages_that_fail_a_check_are_not_used(data, reason):
    assert body_of(data) is None, reason


def test_the_title_check_ignores_case_entities_and_spacing():
    data = page("sample-virtual-threads", "Virtual  threads in a sample   Spring &amp; service")
    assert body_of(data, title="virtual threads in a sample spring & service") is not None


# --- HttpFetcher with allowed_hosts ---------------------------------------------------------


def locked(handler, max_bytes=100_000):
    settings = make_settings(collector_max_response_bytes=max_bytes)
    return HttpFetcher(
        settings, httpx.MockTransport(handler), sleep=lambda s: None, allowed_hosts=WEBDEV_HOSTS
    )


def test_the_locked_fetcher_refuses_other_hosts_and_plain_http():
    seen = []
    http = locked(lambda r: seen.append(r.url) or httpx.Response(200, content=b"ok"))
    for url in ("https://evil.example/blog/a", "http://web.dev/blog/a", "https://127.0.0.1/"):
        with pytest.raises(FetchError, match="refused"):
            http.get(url)
    assert seen == []  # nothing was sent


@pytest.mark.parametrize(
    "location", ["https://evil.example/blog/a", "http://web.dev/blog/a", "https://10.0.0.1/a"]
)
def test_redirects_off_the_allowed_hosts_are_refused(location):
    seen = []

    def handler(request):
        seen.append(str(request.url))
        return httpx.Response(302, headers={"Location": location})

    with pytest.raises(FetchError, match="refused"):
        locked(handler).get("https://web.dev/blog/a")
    assert seen == ["https://web.dev/blog/a"]


def test_redirects_within_web_dev_are_followed():
    def handler(request):
        if request.url.path == "/blog/a":
            return httpx.Response(301, headers={"Location": "/blog/b"})
        return httpx.Response(200, content=b"page b")

    assert locked(handler).get("https://web.dev/blog/a") == b"page b"


def test_the_size_cap_still_applies():
    with pytest.raises(FetchError, match="size limit"):
        locked(lambda r: httpx.Response(200, content=b"x" * 200), max_bytes=100).get(
            "https://web.dev/blog/a"
        )


def test_without_a_proxy_the_host_must_resolve_to_public_addresses(monkeypatch):
    monkeypatch.setattr(http_module, "_behind_proxy", lambda: False)
    answers = {
        "private": [(2, 1, 6, "", ("10.0.0.5", 443))],
        "public": [(2, 1, 6, "", ("216.239.32.21", 443))],
    }
    which = {"value": "private"}
    monkeypatch.setattr(http_module.socket, "getaddrinfo", lambda *a, **k: answers[which["value"]])
    http = locked(lambda r: httpx.Response(200, content=b"ok"))

    with pytest.raises(FetchError, match="non-public address"):
        http.get("https://web.dev/blog/a")
    which["value"] = "public"
    assert http.get("https://web.dev/blog/a") == b"ok"


def test_without_a_proxy_a_host_that_does_not_resolve_is_refused(monkeypatch):
    monkeypatch.setattr(http_module, "_behind_proxy", lambda: False)

    def fail(*args, **kwargs):
        raise OSError("no such host")

    monkeypatch.setattr(http_module.socket, "getaddrinfo", fail)
    with pytest.raises(FetchError, match="does not resolve"):
        locked(lambda r: httpx.Response(200, content=b"ok")).get("https://web.dev/blog/a")


def test_the_collector_fetcher_is_unchanged_without_allowed_hosts(monkeypatch):
    monkeypatch.setattr(http_module.socket, "getaddrinfo", pytest.fail)  # never resolves
    settings = make_settings()
    http = HttpFetcher(settings, httpx.MockTransport(lambda r: httpx.Response(200, content=b"x")))
    assert http.get("https://feeds.example.com/rss") == b"x"
