"""Outbound HTTP for the collector: timeouts, a size cap and a small retry.

Only the collector imports this module; the web app never calls external sites.
Errors never include query strings, so API keys cannot leak into job_runs.
"""

from typing import Protocol
from urllib.parse import urlsplit

import httpx

from app.core.config import Settings

_RETRY_STATUSES = {500, 502, 503, 504}
_ATTEMPTS = 2


class FetchError(Exception):
    def __init__(self, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


class Fetcher(Protocol):
    def get(self, url: str, params: dict | None = None) -> bytes: ...


def _where(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.netloc}{parts.path}"


class HttpFetcher:
    def __init__(self, settings: Settings) -> None:
        self._max_bytes = settings.collector_max_response_bytes
        self._client = httpx.Client(
            timeout=settings.collector_timeout_seconds,
            headers={"User-Agent": settings.collector_user_agent},
            follow_redirects=True,
        )

    def get(self, url: str, params: dict | None = None) -> bytes:
        for attempt in range(1, _ATTEMPTS + 1):
            try:
                return self._get_once(url, params)
            except FetchError as exc:
                if attempt == _ATTEMPTS or not exc.retryable:
                    raise
        raise AssertionError("unreachable")

    def _get_once(self, url: str, params: dict | None) -> bytes:
        try:
            with self._client.stream("GET", url, params=params) as response:
                if response.status_code != 200:
                    raise FetchError(
                        f"HTTP {response.status_code} from {_where(url)}",
                        retryable=response.status_code in _RETRY_STATUSES,
                    )
                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > self._max_bytes:
                        raise FetchError(f"response from {_where(url)} exceeds the size limit")
                return bytes(body)
        except httpx.TransportError as exc:
            raise FetchError(
                f"{type(exc).__name__} while fetching {_where(url)}", retryable=True
            ) from None

    def close(self) -> None:
        self._client.close()
