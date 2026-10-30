"""Source adapters: turn an RSS feed or a public API response into CollectedItems.

Each adapter takes a Fetcher, so tests run on stored sample responses and never
reach the network. Adapters only parse; saving and tagging happen in app.jobs.

A response that cannot be read at all fails the source (FetchError). A single entry
that lacks a usable link or title, or has the wrong shape, is skipped and counted in
Batch.skipped instead, so one bad entry never costs the rest of the feed.
"""

import html
import json
import re
from calendar import timegm
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime

import feedparser

from app.integrations.http import Fetcher, FetchError
from app.integrations.links import SkipEntry, checked_url

EXCERPT_CHARS = 300
TITLE_CHARS = 500
_TAG = re.compile(r"<[^>]+>")
_SPACES = re.compile(r"\s+")


@dataclass
class CollectedItem:
    url: str
    title: str
    external_id: str | None = None
    excerpt: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    tags: list[str] = field(default_factory=list)
    # None means "the source does not provide it" (different from 0).
    score: int | None = None
    comment_count: int | None = None
    view_count: int | None = None


@dataclass
class Batch:
    """What one adapter run produced: usable items and why the others were skipped."""

    items: list[CollectedItem] = field(default_factory=list)
    skipped: Counter = field(default_factory=Counter)  # reason -> count


@dataclass(frozen=True)
class SourceConfig:
    adapter: str
    feed_url: str | None
    options: dict
    max_items: int


def plain_text(value: str | None, limit: int | None = None) -> str | None:
    """HTML or entity-encoded text -> one line of plain text, optionally shortened."""
    if not value:
        return None
    text = _SPACES.sub(" ", html.unescape(_TAG.sub(" ", value))).strip()
    if limit and len(text) > limit:
        cut = text[:limit].rsplit(" ", 1)[0] if " " in text[:limit] else text[:limit]
        text = cut.rstrip(" ,.;:") + "…"
    return text or None


# An unreadable date or metric is treated as "not provided", not as a broken entry.


def _from_epoch(seconds) -> datetime | None:
    if isinstance(seconds, bool) or not isinstance(seconds, int | float):
        return None
    try:
        return datetime.fromtimestamp(seconds, UTC).replace(tzinfo=None)
    except (OverflowError, OSError, ValueError):
        return None


def _from_iso(value) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(UTC).replace(tzinfo=None)
    return parsed


def _count(value) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _text(value, limit: int | None = None) -> str | None:
    return plain_text(value, limit) if isinstance(value, str) else None


def _tags(values) -> list[str]:
    if isinstance(values, str):
        values = values.split(",")
    if not isinstance(values, list):
        return []
    return [t.strip() for t in values if isinstance(t, str) and t.strip()]


def _json(data: bytes, where: str, shape: type):
    try:
        body = json.loads(data)
    except ValueError as exc:
        raise FetchError(f"{where} returned invalid JSON") from exc
    if not isinstance(body, shape):
        raise FetchError(f"{where} returned an unexpected response")
    return body


# --- per-entry checks shared by every adapter ----------------------------------------------


def checked_title(value) -> str:
    title = _text(value)
    if not title:
        raise SkipEntry("no title")
    return title[:TITLE_CHARS]


def _external_id(value) -> str:
    if value is None or isinstance(value, bool) or str(value).strip() == "":
        raise SkipEntry("no id")
    return str(value)[:255]


def _batch(entries: Iterable, convert: Callable[[dict], CollectedItem], limit=None) -> Batch:
    batch = Batch()
    for entry in entries:
        try:
            if not isinstance(entry, dict):
                raise SkipEntry("malformed entry")
            batch.items.append(convert(entry))
        except SkipEntry as skip:
            batch.skipped[str(skip)] += 1
        except (KeyError, TypeError, ValueError, AttributeError):
            batch.skipped["malformed entry"] += 1
        if limit is not None and len(batch.items) == limit:
            break
    return batch


# --- RSS / Atom ---------------------------------------------------------------------------


def _feed_item(entry: dict) -> CollectedItem:
    published = entry.get("published_parsed") or entry.get("updated_parsed")
    entry_id = entry.get("id")
    return CollectedItem(
        url=checked_url(entry.get("link")),
        title=checked_title(entry.get("title")),
        external_id=str(entry_id)[:255] if entry_id else None,
        excerpt=_text(entry.get("summary"), EXCERPT_CHARS),
        author=_text(entry.get("author"), 200),
        published_at=_from_epoch(timegm(published)) if published else None,
        tags=_tags([t.get("term") for t in entry.get("tags", []) if isinstance(t, dict)]),
    )


def parse_feed(data: bytes, limit: int) -> Batch:
    feed = feedparser.parse(data)
    if not feed.entries and (feed.bozo or not feed.version):
        reason = type(feed.get("bozo_exception")).__name__ if feed.bozo else "no feed found"
        raise FetchError(f"not a readable RSS/Atom feed ({reason})")
    return _batch(feed.entries, _feed_item, limit)


def collect_rss(fetcher: Fetcher, source: SourceConfig) -> Batch:
    return parse_feed(fetcher.get(source.feed_url), source.max_items)


# --- Dev.to (https://developers.forem.com/api) -----------------------------------------------

DEVTO_ARTICLES = "https://dev.to/api/articles"


def _devto_item(article: dict) -> CollectedItem:
    user = article.get("user")
    return CollectedItem(
        url=checked_url(article.get("url")),
        title=checked_title(article.get("title")),
        external_id=_external_id(article.get("id")),
        excerpt=_text(article.get("description"), EXCERPT_CHARS),
        author=_text(user.get("name"), 200) if isinstance(user, dict) else None,
        published_at=_from_iso(article.get("published_at")),
        tags=_tags(article.get("tag_list")),
        score=_count(article.get("public_reactions_count")),
        comment_count=_count(article.get("comments_count")),
    )


def collect_devto(fetcher: Fetcher, source: SourceConfig) -> Batch:
    """Latest articles plus, when top_days is set, the most popular ones of that period."""
    base = {"per_page": source.max_items}
    if tag := source.options.get("tag"):
        base["tag"] = tag
    requests = [base]
    if top_days := source.options.get("top_days"):
        requests.append(base | {"top": top_days})

    merged = Batch()
    items: dict[str, CollectedItem] = {}
    for params in requests:
        batch = _batch(_json(fetcher.get(DEVTO_ARTICLES, params), "Dev.to", list), _devto_item)
        merged.skipped.update(batch.skipped)
        for item in batch.items:
            items[item.external_id] = item
    merged.items = list(items.values())
    return merged


# --- Hacker News (https://hn.algolia.com/api) -----------------------------------------------

HN_SEARCH = "https://hn.algolia.com/api/v1/search"
HN_ITEM = "https://news.ycombinator.com/item?id="


def _hn_item(hit: dict) -> CollectedItem:
    object_id = _external_id(hit.get("objectID"))
    title = checked_title(hit.get("title"))
    # Ask HN / text posts have no external link; use the discussion page.
    url = hit.get("url") or f"{HN_ITEM}{object_id}"
    return CollectedItem(
        url=checked_url(url),
        title=title,
        external_id=object_id,
        excerpt=_text(hit.get("story_text"), EXCERPT_CHARS),
        author=_text(hit.get("author"), 200),
        published_at=_from_epoch(hit.get("created_at_i")),
        tags=[],
        score=_count(hit.get("points")),
        comment_count=_count(hit.get("num_comments")),
    )


def collect_hackernews(fetcher: Fetcher, source: SourceConfig) -> Batch:
    params = {"tags": source.options.get("tags", "front_page"), "hitsPerPage": source.max_items}
    body = _json(fetcher.get(HN_SEARCH, params), "Hacker News", dict)
    hits = body.get("hits", [])
    if not isinstance(hits, list):
        raise FetchError("Hacker News returned an unexpected response")
    return _batch(hits, _hn_item)


# --- Stack Overflow (https://api.stackexchange.com/docs) ------------------------------------

SE_QUESTIONS = "https://api.stackexchange.com/2.3/questions"


def _se_item(question: dict) -> CollectedItem:
    owner = question.get("owner")
    return CollectedItem(
        url=checked_url(question.get("link")),
        # Stack Exchange returns titles HTML-encoded.
        title=checked_title(question.get("title")),
        external_id=_external_id(question.get("question_id")),
        author=_text(owner.get("display_name"), 200) if isinstance(owner, dict) else None,
        published_at=_from_epoch(question.get("creation_date")),
        tags=_tags(question.get("tags")),
        score=_signed(question.get("score")),
        # For Q&A sources the "comments" column holds the number of answers.
        comment_count=_count(question.get("answer_count")),
        view_count=_count(question.get("view_count")),
    )


def _signed(value) -> int | None:
    """Stack Overflow scores can be negative."""
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def collect_stackoverflow(fetcher: Fetcher, source: SourceConfig, key: str | None = None) -> Batch:
    options = source.options
    params = {
        "site": options.get("site", "stackoverflow"),
        "sort": options.get("sort", "hot"),
        "order": "desc",
        "pagesize": source.max_items,
    }
    if tagged := options.get("tagged"):
        params["tagged"] = tagged
    if key:
        params["key"] = key
    body = _json(fetcher.get(SE_QUESTIONS, params), "Stack Exchange", dict)
    if "error_id" in body:
        raise FetchError(f"Stack Exchange error {body['error_id']}: {body.get('error_name')}")
    questions = body.get("items", [])
    if not isinstance(questions, list):
        raise FetchError("Stack Exchange returned an unexpected response")
    return _batch(questions, _se_item)


Adapter = Callable[[Fetcher, SourceConfig], Batch]


def adapters(stackexchange_key: str | None = None) -> dict[str, Adapter]:
    return {
        "rss": collect_rss,
        "devto": collect_devto,
        "hackernews": collect_hackernews,
        "stackoverflow": lambda fetcher, source: collect_stackoverflow(
            fetcher, source, stackexchange_key
        ),
    }
