"""Manual trial: store one notice page and one Atom entry, on a personal PC, for at most
48 hours. `python -m app.jobs trial MANIFEST [--dry-run]`

Separate from sources.yaml and scheduled collection; the general terms gate is unchanged.
The manifest (a local file, not in the repository) names, per item, the input URL, the
exact original URL to store, the allowed fields, the usage basis and the trial window.

Order, each step refusing before the next:
1. the manifest is valid and now is inside its window (no request otherwise);
2. unless --dry-run, the database is checked (also before any request);
3. per item: robots.txt, then one request for the page or feed; no redirects, one
   attempt per request and at most two requests per item. Unlike the collector, a
   robots.txt that cannot be read as rules (any error status, an HTML page) refuses;
   a feed answered with an HTML page fails. The window is checked again before each
   request;
4. only the allowed fields of the one target entry are kept (title, original URL,
   source, publish time, optionally author and source tags); the feed's other entries,
   descriptions, bodies and images are dropped in memory and never logged;
5. in the write transaction, the connection that will write is checked again with
   SELECT DATABASE() and CURRENT_USER() before autoflush or any write: configured and
   actual database devhub_experiment, account devhub_experiment (the server may be the
   local dev/test one; the account's grants keep it to this database). The window is
   checked again before the first write of each item. Then store_items saves (a stored
   URL is updated, never duplicated).

Trial source rows are created paused with terms: unverified, so `collect` never picks
them up and the general gate stays as it is.
"""

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

import httpx
import yaml
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError, model_validator
from sqlalchemy import Connection, func, select, text
from sqlalchemy.orm import Session

from app.integrations.http import FetchError, check_address
from app.integrations.notice_page import notice_id_from, parse_notice
from app.integrations.robots import RobotsPolicy, _Rules
from app.integrations.sources import CollectedItem, parse_feed
from app.jobs.store import StoreResult, normalize_url, store_items
from app.models.content import ContentSource
from app.services.tagging import Tagger, load_tagger

DATABASE = "devhub_experiment"
ACCOUNT = "devhub_experiment"
MAX_WINDOW = timedelta(hours=48)
REQUESTS_PER_ITEM = 2  # robots.txt + the page or feed
FEED_ENTRIES = 1000  # read the whole feed to find the one entry
REQUIRED_FIELDS = {"title", "url", "published_at", "source"}
OPTIONAL_FIELDS = {"author", "source_tags"}
Field_ = Literal["title", "url", "published_at", "source", "author", "source_tags"]


class TrialRefused(RuntimeError):
    """A trial step was refused. The message is a reason code (no URL secrets, no text)."""

    def __init__(self, code: str, detail: str | None = None) -> None:
        super().__init__(code + (f" ({detail})" if detail else ""))
        self.code = code


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def _https(url: str) -> str:
    """A public https URL on the default port, without credentials or odd characters."""
    if any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in url):
        raise ValueError("URLs must not contain spaces or control characters")
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
        raise ValueError("URLs must be https, with a host and without credentials")
    try:
        port = parts.port
    except ValueError:
        raise ValueError("URLs must not carry an invalid port") from None
    if port not in (None, 443):
        raise ValueError("URLs must use the default https port")
    try:
        check_address(httpx.URL(url))  # localhost and non-public IP literals
    except (httpx.InvalidURL, FetchError):
        raise ValueError("URLs must name a public host") from None
    return url


class TrialSource(_Strict):
    slug: str = Field(pattern=r"^trial-[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=64)
    name: str = Field(min_length=1, max_length=100)
    kind: Literal["news", "blog"]
    site_url: str
    language: Literal["ko", "en"] = "ko"
    channel: str | None = Field(default=None, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    channel_name: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def _check(self) -> "TrialSource":
        _https(self.site_url)
        if (self.kind == "blog") != (self.channel is not None and self.channel_name is not None):
            raise ValueError("blog sources need channel and channel_name; news sources none")
        return self


class TrialItem(_Strict):
    kind: Literal["notice_page", "atom_entry"]
    source: TrialSource
    input_url: str
    target_url: str
    fields: list[Field_]
    basis: str = Field(min_length=10, max_length=2000)

    @model_validator(mode="after")
    def _check(self) -> "TrialItem":
        _https(self.input_url)
        _https(self.target_url)
        fields = set(self.fields)
        if not REQUIRED_FIELDS <= fields:
            raise ValueError(f"fields must include {sorted(REQUIRED_FIELDS)}")
        if self.kind == "notice_page":
            if normalize_url(self.input_url) != normalize_url(self.target_url):
                raise ValueError("a notice page is stored at the URL it is read from")
            if fields & OPTIONAL_FIELDS:
                raise ValueError("a notice page provides title, URL, source and date only")
            try:
                notice_id_from(self.target_url)
            except FetchError:
                raise ValueError("a notice URL ends in its numeric id") from None
        else:
            if urlsplit(self.input_url).hostname != urlsplit(self.target_url).hostname:
                raise ValueError("an Atom entry must be on the feed's own host")
            if normalize_url(self.input_url) == normalize_url(self.target_url):
                raise ValueError("an Atom entry's URL differs from its feed's")
        return self


class Manifest(_Strict):
    trial: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=64)
    database: Literal["devhub_experiment"]
    created_at: AwareDatetime
    expires_at: AwareDatetime
    items: list[TrialItem] = Field(min_length=1, max_length=2)

    @model_validator(mode="after")
    def _check(self) -> "Manifest":
        if not timedelta(0) < self.expires_at - self.created_at <= MAX_WINDOW:
            raise ValueError("a trial lasts more than 0 and at most 48 hours")
        slugs = [i.source.slug for i in self.items]
        if len(set(slugs)) != len(slugs):
            raise ValueError("each item has its own source slug")
        return self


def read_manifest(path: Path) -> Manifest:
    try:
        return Manifest.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    except (OSError, yaml.YAMLError, ValidationError) as exc:
        raise TrialRefused("invalid_manifest", type(exc).__name__) from None


Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(UTC)


def check_window(manifest: Manifest, now: datetime) -> None:
    if now < manifest.created_at:
        raise TrialRefused("trial_not_started")
    if now >= manifest.expires_at:
        raise TrialRefused("trial_expired")


# --- the database actually connected ----------------------------------------------------


def check_connection(connection: Connection) -> None:
    """Configured and actual database and account must be the trial's own. The server
    may be shared (e.g. the local dev/test one): the dedicated account's grants, checked
    by hand with SHOW GRANTS, keep it to devhub_experiment. Reason codes only."""
    url = connection.engine.url
    try:
        actual_db = connection.execute(text("SELECT DATABASE()")).scalar()
        actual_user = connection.execute(text("SELECT CURRENT_USER()")).scalar()
    except Exception:
        raise TrialRefused("database_unverified") from None
    if url.database != DATABASE or actual_db != DATABASE:
        raise TrialRefused("not_the_experiment_database")
    if url.username != ACCOUNT or str(actual_user or "").split("@")[0] != ACCOUNT:
        raise TrialRefused("not_the_experiment_account")


# --- network -----------------------------------------------------------------------------


class _StrictRobots(RobotsPolicy):
    """The collector's robots.txt policy, except that no rules read means refused: an
    error status (including 404) or an HTML page in place of robots.txt is not taken as
    permission in a trial. The collector's own policy is unchanged."""

    def _read(self, host: str) -> _Rules:
        found = super()._read(host)
        return replace(found, allowed=False) if found.rules is None else found


def _looks_like_html_page(body: bytes) -> bool:
    head = body.lstrip()[:64].lower()
    return head.startswith((b"<!doctype html", b"<html"))


class _Budget:
    """At most `limit` requests through the wrapped fetcher; redirects are refused, and
    `before_request` (the window check) runs before each one."""

    def __init__(self, fetcher, limit: int, before_request: Callable[[], None]) -> None:
        self._fetcher, self.limit, self.used = fetcher, limit, 0
        self._before_request = before_request
        if hasattr(fetcher, "on_redirect"):
            fetcher.on_redirect = self._refuse_redirect

    @staticmethod
    def _refuse_redirect(url: str) -> None:
        raise FetchError("redirect refused in a trial")

    def get(self, url: str, params=None) -> bytes:
        if self.used >= self.limit:
            raise TrialRefused("request_limit_reached")
        self._before_request()
        self.used += 1
        return self._fetcher.get(url, params)


def _collected(item: TrialItem, raw: bytes) -> CollectedItem:
    """The one target as a CollectedItem holding only the allowed fields."""
    target = normalize_url(item.target_url)
    fields = set(item.fields)
    if item.kind == "notice_page":
        title, published = parse_notice(raw, notice_id_from(item.target_url))
        return CollectedItem(url=target, title=title, published_at=published)
    if _looks_like_html_page(raw):
        raise FetchError("feed: an HTML page was returned instead of the feed")
    entries = [e for e in parse_feed(raw, FEED_ENTRIES).items if normalize_url(e.url) == target]
    if len(entries) != 1:
        raise FetchError(f"feed: expected exactly one entry for the target, found {len(entries)}")
    entry = entries[0]
    if entry.published_at is None:
        raise FetchError("feed: the target entry has no publish time")
    return CollectedItem(
        url=target,
        title=entry.title,
        published_at=entry.published_at,
        author=entry.author if "author" in fields else None,
        tags=list(entry.tags) if "source_tags" in fields else [],
    )


def input_hosts(manifest: Manifest) -> frozenset[str]:
    """The only hosts the trial's fetcher may reach (https, the manifest's input URLs)."""
    return frozenset(urlsplit(i.input_url).hostname for i in manifest.items)


def fetch_items(
    manifest: Manifest, fetcher, clock: Clock = utc_now
) -> tuple[list[tuple[TrialItem, CollectedItem]], int]:
    """(items with their allowed fields, requests made)."""
    budget = _Budget(
        fetcher,
        REQUESTS_PER_ITEM * len(manifest.items),
        before_request=lambda: check_window(manifest, clock()),
    )
    robots = _StrictRobots(budget)
    prepared = []
    for item in manifest.items:
        verdict = robots.check(item.input_url)
        if not verdict.allowed:
            raise TrialRefused("robots_refused", item.source.slug)
        prepared.append((item, _collected(item, budget.get(item.input_url))))
    return prepared, budget.used


# --- saving ------------------------------------------------------------------------------


def _source_row(db: Session, manifest: Manifest, item: TrialItem) -> ContentSource:
    spec = item.source
    row = db.scalar(select(ContentSource).where(ContentSource.slug == spec.slug))
    if row is not None:
        if (row.options or {}).get("trial") != manifest.trial or row.site_url != spec.site_url:
            raise TrialRefused("source_slug_belongs_to_something_else", spec.slug)
        return row
    position = (db.scalar(select(func.max(ContentSource.position))) or 0) + 1
    row = ContentSource(
        slug=spec.slug,
        name=spec.name,
        kind=spec.kind,
        adapter="rss",  # a recorded adapter value only; trials never run through collect
        site_url=spec.site_url,
        feed_url=item.input_url,
        language=spec.language,
        options={"terms": "unverified", "trial": manifest.trial},
        max_items=1,
        channel=spec.channel,
        channel_name=spec.channel_name,
        position=position,
        ai_summary=False,
        status="paused",  # never collected by `collect`; shown in lists like paused sources
    )
    db.add(row)
    db.flush()
    return row


def save(
    db: Session,
    manifest: Manifest,
    prepared: list[tuple[TrialItem, CollectedItem]],
    tagger_for: Callable[[Session], Tagger] = load_tagger,
    connection_check: Callable[[Connection], None] = check_connection,
    clock: Clock = utc_now,
) -> list[StoreResult]:
    """In the caller's transaction: check the writing connection first, then store. The
    window is checked before each item's first write; a refusal there rolls back the
    caller's transaction, so nothing of the trial is kept."""
    with db.no_autoflush:
        connection_check(db.connection())
        check_window(manifest, clock())  # before any other statement in the transaction
    tagger = tagger_for(db)
    results = []
    for item, collected in prepared:
        check_window(manifest, clock())
        source = _source_row(db, manifest, item)
        results.append(store_items(db, source, [collected], tagger))
    return results


@dataclass
class TrialReport:
    items: list[tuple[TrialItem, CollectedItem]]
    stored: list[StoreResult] | None  # None for --dry-run
    requests: int


def run(
    manifest: Manifest,
    fetcher,
    engine=None,
    sessions=None,
    clock: Clock = utc_now,
    dry_run: bool = False,
) -> TrialReport:
    check_window(manifest, clock())
    if not dry_run:
        try:
            with engine.connect() as connection:
                check_connection(connection)
        except TrialRefused:
            raise
        except Exception:
            raise TrialRefused("database_unverified") from None
    prepared, requests = fetch_items(manifest, fetcher, clock)
    if dry_run:
        return TrialReport(prepared, None, requests)
    with sessions() as db, db.begin():
        stored = save(db, manifest, prepared, clock=clock)
    return TrialReport(prepared, stored, requests)
