"""Outbound HTTP for the collector: timeouts, a size cap, checked redirects and a small retry.

Only the collector imports this module; the web app never calls external sites.
Errors never include query strings, so API keys cannot leak into job_runs.

Retry policy (at most MAX_ATTEMPTS requests per get()):
- 429: wait for Retry-After (seconds or an HTTP date) when it is at most
  MAX_RETRY_AFTER_SECONDS; a longer wait fails at once instead of stalling the run.
- 500/502/503/504, timeouts and connection errors: retry after BACKOFF_SECONDS.
- Any other status (400, 401, 403, 404, ...) fails at once: asking again gives the same answer.

Redirects are followed by hand, at most MAX_REDIRECTS hops. Every address, the first one
included, must be http(s) without credentials, must not name localhost or a non-public IP
address (legacy forms such as 2130706433 or 127.1 included), and a redirect may not drop
from https to http. Only the User-Agent header is sent: no Authorization, and cookies a
site sets are never stored or sent back. A redirect target is the Location as given; the
original query (where an API key lives) is not carried over.

Limit: host names are not resolved here, so a public-looking name that resolves to a
private address (for example 127.0.0.1.nip.io) is not caught. That is acceptable for the
collector, which only starts from feed addresses in the reviewed sources file. Fetching
article pages from arbitrary links (design E1/F3) must also resolve each host, refuse
non-public results and connect to the address it checked.
"""

import ipaddress
import socket
import time
from collections.abc import Callable
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from http.cookiejar import CookieJar, DefaultCookiePolicy
from typing import Protocol

import httpx

from app.core.config import Settings

_RETRY_STATUSES = {500, 502, 503, 504}
_REDIRECT_STATUSES = {301, 302, 303, 307, 308}
MAX_ATTEMPTS = 3
BACKOFF_SECONDS = (1.0, 2.0)  # before the 2nd and the 3rd attempt
MAX_RETRY_AFTER_SECONDS = 30.0
MAX_REDIRECTS = 5


class FetchError(Exception):
    def __init__(
        self, message: str, retryable: bool = False, retry_after: float | None = None
    ) -> None:
        super().__init__(message)
        self.retryable = retryable
        # Seconds the server asked us to wait (429); None means "use the backoff".
        self.retry_after = retry_after


class Fetcher(Protocol):
    def get(self, url: str, params: dict | None = None) -> bytes: ...


def _where(url: httpx.URL) -> str:
    return f"{url.host}{url.path}"


def check_address(url: httpx.URL) -> None:
    """Refuse addresses the collector must never request."""
    if url.scheme not in ("http", "https") or not url.host:
        raise FetchError("only http(s) addresses with a host are allowed")
    if url.userinfo:
        raise FetchError(f"address with credentials refused: {_where(url)}")
    host = url.host.rstrip(".").lower()
    if host == "localhost" or host.endswith(".localhost"):
        raise FetchError(f"local address refused: {_where(url)}")
    ip = _ip_literal(host)
    if ip is not None and not ip.is_global:
        raise FetchError(f"non-public address refused: {_where(url)}")


def _ip_literal(host: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    """The address a host string stands for without DNS, including the legacy IPv4 forms
    (2130706433, 0x7f.0.0.1, 127.1) that the system resolver still accepts."""
    try:
        return ipaddress.ip_address(host)
    except ValueError:
        pass
    try:
        return ipaddress.IPv4Address(socket.inet_aton(host))
    except OSError:
        return None  # a host name


def retry_after_seconds(value: str | None, now: datetime | None = None) -> float | None:
    """Retry-After as seconds to wait, or None when absent or unreadable."""
    if not value:
        return None
    value = value.strip()
    if value.isdigit():
        return float(value)
    try:
        when = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    return max(0.0, (when - (now or datetime.now(UTC))).total_seconds())


class HttpFetcher:
    def __init__(
        self,
        settings: Settings,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._max_bytes = settings.collector_max_response_bytes
        self._sleep = sleep
        self._client = httpx.Client(
            timeout=settings.collector_timeout_seconds,
            headers={"User-Agent": settings.collector_user_agent},
            follow_redirects=False,
            transport=transport,
            # Accept no cookies, so none can travel from one request (or site) to the next.
            cookies=CookieJar(policy=DefaultCookiePolicy(allowed_domains=[])),
        )

    def get(self, url: str, params: dict | None = None) -> bytes:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                return self._get_once(url, params)
            except FetchError as exc:
                if attempt == MAX_ATTEMPTS or not exc.retryable:
                    raise
                wait = exc.retry_after
                self._sleep(BACKOFF_SECONDS[attempt - 1] if wait is None else wait)
        raise AssertionError("unreachable")

    def _get_once(self, url: str, params: dict | None) -> bytes:
        try:
            target = httpx.URL(url, params=params) if params else httpx.URL(url)
        except httpx.InvalidURL:
            raise FetchError("invalid address") from None
        check_address(target)
        start = target
        try:
            for _hop in range(MAX_REDIRECTS + 1):
                with self._client.stream("GET", target) as response:
                    if response.status_code in _REDIRECT_STATUSES:
                        target = self._redirect_target(response)
                        continue
                    return self._read(response)
        except httpx.TransportError as exc:
            raise FetchError(
                f"{type(exc).__name__} while fetching {_where(start)}", retryable=True
            ) from None
        except httpx.InvalidURL:
            # httpx parses a redirect's Location itself, before we get to check it.
            raise FetchError(f"invalid redirect from {_where(target)}") from None
        raise FetchError(f"more than {MAX_REDIRECTS} redirects from {_where(start)}")

    def _redirect_target(self, response: httpx.Response) -> httpx.URL:
        location = response.headers.get("location")
        if not location:
            raise FetchError(
                f"HTTP {response.status_code} without a Location from {_where(response.url)}"
            )
        try:
            target = response.url.join(location)
        except httpx.InvalidURL:
            raise FetchError(f"invalid redirect from {_where(response.url)}") from None
        try:
            check_address(target)
        except FetchError as exc:
            raise FetchError(f"redirect from {_where(response.url)} refused: {exc}") from None
        if response.url.scheme == "https" and target.scheme != "https":
            raise FetchError(f"redirect from {_where(response.url)} to plain http refused")
        return target

    def _read(self, response: httpx.Response) -> bytes:
        where = _where(response.url)
        status = response.status_code
        if status == 429:
            wait = retry_after_seconds(response.headers.get("retry-after"))
            if wait is not None and wait > MAX_RETRY_AFTER_SECONDS:
                raise FetchError(f"HTTP 429 from {where} (retry after {wait:.0f}s, not waiting)")
            raise FetchError(f"HTTP 429 from {where}", retryable=True, retry_after=wait)
        if status != 200:
            raise FetchError(f"HTTP {status} from {where}", retryable=status in _RETRY_STATUSES)
        declared = response.headers.get("content-length", "")
        if declared.isdigit() and int(declared) > self._max_bytes:
            raise FetchError(f"response from {where} exceeds the size limit")
        body = bytearray()
        for chunk in response.iter_bytes():
            body.extend(chunk)
            if len(body) > self._max_bytes:
                raise FetchError(f"response from {where} exceeds the size limit")
        return bytes(body)

    def close(self) -> None:
        self._client.close()
