"""robots.txt check for the collector and the feed diagnosis (RFC 9309).

Rules are read for our own product token first and for `*` otherwise; the longest
matching path wins and an Allow wins a tie. `*` and `$` are supported.

When robots.txt cannot be read, the answer is conservative:
- 404, 410 and other "no file" 4xx answers, or an HTML page instead of rules:
  "unavailable", so crawling is allowed (RFC 9309 2.3.1.3);
- 401, 403 or 429 (the site restricts or throttles us), a redirect to plain http that is
  not followed, 5xx, a response over the fetcher's size limit or a network error:
  "unreachable", so nothing on that host is requested (RFC 9309 2.3.1.4). An access
  restriction is never read as permission.
A large file is parsed up to MAX_ROBOTS_BYTES (RFC 9309 2.5: at least 500 KiB); the
rules found there still apply, so size never turns a Disallow into an Allow.

Redirects of a guarded request (guard_redirects) are checked hop by hop: a redirect to a
path the target host's robots.txt disallows is not followed.
One robots.txt request per host per run; the answer is cached in the policy object.
"""

import re
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from urllib.parse import urlsplit

from app.integrations.http import Fetcher, FetchError, InsecureRedirect

PRODUCT_TOKEN = "devhubcollector"  # matches User-Agent: DevHubCollector/2.0 (...)
MAX_ROBOTS_BYTES = 512_000  # RFC 9309 2.5: parse at least 500 KiB
_RESTRICTING = {401, 403, 429}  # answers that mean "not you" or "slow down"


@dataclass(frozen=True)
class RobotsVerdict:
    allowed: bool
    reason: str


@dataclass(frozen=True)
class _Rules:
    rules: tuple[tuple[bool, str], ...] | None  # (allow, path); None: no rules were read
    note: str
    allowed: bool = True  # only for rules None: unavailable (True) or unreachable (False)


def _groups(text: str) -> list[tuple[list[str], list[tuple[bool, str]]]]:
    groups: list[tuple[list[str], list[tuple[bool, str]]]] = []
    agents: list[str] = []
    rules: list[tuple[bool, str]] = []
    in_rules = False
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        key, value = (part.strip() for part in line.split(":", 1))
        key = key.lower()
        if key == "user-agent":
            if in_rules:
                groups.append((agents, rules))
                agents, rules, in_rules = [], [], False
            agents.append(value.lower())
        elif key in ("allow", "disallow"):
            in_rules = True
            if value:  # an empty Disallow allows everything
                rules.append((key == "allow", value))
    if agents:
        groups.append((agents, rules))
    return groups


def parse_rules(text: str, token: str = PRODUCT_TOKEN) -> tuple[tuple[bool, str], ...]:
    """The rules that apply to `token`: its own groups, else the `*` groups."""
    groups = _groups(text)
    named = [rules for agents, rules in groups if any(a != "*" and a in token for a in agents)]
    if named:
        return tuple(r for rules in named for r in rules)
    return tuple(r for agents, rules in groups if "*" in agents for r in rules)


def _pattern(path: str) -> re.Pattern[str]:
    anchored = path.endswith("$")
    body = path[:-1] if anchored else path
    regex = "".join(".*" if c == "*" else re.escape(c) for c in body)
    return re.compile(regex + ("$" if anchored else ""))


def check_path(rules: tuple[tuple[bool, str], ...], url: str) -> RobotsVerdict:
    parts = urlsplit(url)
    path = (parts.path or "/") + (f"?{parts.query}" if parts.query else "")
    best: tuple[int, bool, str] | None = None
    for allow, value in rules:
        if _pattern(value).match(path):
            candidate = (len(value), allow, value)
            if best is None or candidate[:2] > best[:2]:
                best = candidate
    if best is None:
        return RobotsVerdict(True, "robots.txt: no rule for this path")
    _, allow, value = best
    return RobotsVerdict(allow, f"robots.txt: {'Allow' if allow else 'Disallow'} {value}")


def _looks_like_html(body: bytes) -> bool:
    head = body.lstrip()[:64].lower()
    return head.startswith((b"<!doctype", b"<html", b"<head", b"<?xml"))


def _within_limit(body: bytes) -> bytes:
    """The first MAX_ROBOTS_BYTES, cut at the last full line."""
    if len(body) <= MAX_ROBOTS_BYTES:
        return body
    head = body[:MAX_ROBOTS_BYTES]
    return head[: head.rfind(b"\n") + 1] if b"\n" in head else head


class RobotsPolicy:
    def __init__(self, fetcher: Fetcher) -> None:
        self._fetcher = fetcher
        self._hosts: dict[str, _Rules] = {}
        self._reading = False

    def check(self, url: str) -> RobotsVerdict:
        parts = urlsplit(url)
        host = f"{parts.scheme}://{parts.netloc}".lower()
        if host not in self._hosts:
            self._reading = True
            try:
                self._hosts[host] = self._read(host)
            finally:
                self._reading = False
        found = self._hosts[host]
        if found.rules is None:
            return RobotsVerdict(found.allowed, f"robots.txt {found.note}")
        return check_path(found.rules, url)

    def require(self, url: str) -> None:
        """Raise FetchError unless robots.txt allows `url`. Redirects of robots.txt
        requests themselves are not checked (they are how the rules are found)."""
        if self._reading:
            return
        verdict = self.check(url)
        if not verdict.allowed:
            raise FetchError(f"not requested: {url} ({verdict.reason})")

    def _read(self, host: str) -> _Rules:
        try:
            body = self._fetcher.get(f"{host}/robots.txt")
        except InsecureRedirect:
            return _Rules(None, "unreachable (redirects to plain http)", allowed=False)
        except FetchError as exc:
            status = getattr(exc, "status", None)
            if status is not None and 400 <= status < 500 and status not in _RESTRICTING:
                return _Rules(None, f"unavailable (HTTP {status})")
            reason = f"HTTP {status}" if status is not None else str(exc)[:80]
            return _Rules(None, f"unreachable ({reason})", allowed=False)
        if _looks_like_html(body):
            return _Rules(None, "unavailable (not a robots.txt file)")
        return _Rules(parse_rules(_within_limit(body).decode("utf-8", "replace")), "read")


@contextmanager
def guard_redirects(fetcher: Fetcher, robots: RobotsPolicy) -> Iterator[None]:
    """While active, every redirect the fetcher would follow is checked against robots.txt
    first (fetchers without redirect hooks, such as test doubles, are left as they are)."""
    if not hasattr(fetcher, "on_redirect"):
        yield
        return
    previous = fetcher.on_redirect
    fetcher.on_redirect = robots.require
    try:
        yield
    finally:
        fetcher.on_redirect = previous
