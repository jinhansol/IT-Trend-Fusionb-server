"""robots.txt check for the collector and the feed diagnosis (RFC 9309).

Rules are read for our own product token first and for `*` otherwise; the longest
matching path wins and an Allow wins a tie. `*` and `$` are supported.

When robots.txt cannot be read:
- 4xx (no file), an HTML page instead of rules, or a redirect to plain http that is not
  followed: "unavailable", so crawling is allowed (RFC 9309 2.3.1.3);
- 5xx or a network error: "unreachable", so nothing on that host is requested
  (RFC 9309 2.3.1.4).
One robots.txt request per host per run; the answer is cached in the policy object.
"""

import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from app.integrations.http import Fetcher, FetchError, InsecureRedirect

PRODUCT_TOKEN = "devhubcollector"  # matches User-Agent: DevHubCollector/2.0 (...)
MAX_ROBOTS_BYTES = 500_000


@dataclass(frozen=True)
class RobotsVerdict:
    allowed: bool
    reason: str


@dataclass(frozen=True)
class _Rules:
    rules: tuple[tuple[bool, str], ...] | None  # (allow, path); None: allow everything
    note: str


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


class RobotsPolicy:
    def __init__(self, fetcher: Fetcher) -> None:
        self._fetcher = fetcher
        self._hosts: dict[str, _Rules] = {}

    def check(self, url: str) -> RobotsVerdict:
        parts = urlsplit(url)
        host = f"{parts.scheme}://{parts.netloc}".lower()
        if host not in self._hosts:
            self._hosts[host] = self._read(host)
        found = self._hosts[host]
        if found.rules is None:
            return RobotsVerdict(found.note != "unreachable", f"robots.txt {found.note}")
        return check_path(found.rules, url)

    def _read(self, host: str) -> _Rules:
        try:
            body = self._fetcher.get(f"{host}/robots.txt")
        except InsecureRedirect:
            return _Rules(None, "unavailable (redirects to plain http)")
        except FetchError as exc:
            status = getattr(exc, "status", None)
            if status is not None and 400 <= status < 500:
                return _Rules(None, f"unavailable (HTTP {status})")
            return _Rules(None, "unreachable")
        if _looks_like_html(body) or len(body) > MAX_ROBOTS_BYTES:
            return _Rules(None, "unavailable (not a robots.txt file)")
        return _Rules(parse_rules(body.decode("utf-8", "replace")), "read")
