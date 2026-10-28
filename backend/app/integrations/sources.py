"""Source adapters: turn an RSS feed or a public API response into CollectedItems.

Each adapter takes a Fetcher, so tests run on stored sample responses and never
reach the network. Adapters only parse; saving and tagging happen in app.jobs.
"""

import html
import json
import re
from calendar import timegm
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

import feedparser

from app.integrations.http import Fetcher, FetchError

EXCERPT_CHARS = 300
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


def _from_epoch(seconds: int | float | None) -> datetime | None:
    if seconds is None:
        return None
    return datetime.fromtimestamp(seconds, UTC).replace(tzinfo=None)


def _from_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(UTC).replace(tzinfo=None)
    return parsed


def _json(data: bytes, where: str):
    try:
        return json.loads(data)
    except ValueError as exc:
        raise FetchError(f"{where} returned invalid JSON") from exc


# --- RSS / Atom ---------------------------------------------------------------------------


def parse_feed(data: bytes, limit: int) -> list[CollectedItem]:
    feed = feedparser.parse(data)
    if not feed.entries and (feed.bozo or not feed.version):
        reason = type(feed.get("bozo_exception")).__name__ if feed.bozo else "no feed found"
        raise FetchError(f"not a readable RSS/Atom feed ({reason})")
    items = []
    for entry in feed.entries:
        url = (entry.get("link") or "").strip()
        title = plain_text(entry.get("title"))
        if not url.startswith(("http://", "https://")) or not title:
            continue
        published = entry.get("published_parsed") or entry.get("updated_parsed")
        items.append(
            CollectedItem(
                url=url,
                title=title[:500],
                external_id=(entry.get("id") or None) and str(entry.get("id"))[:255],
                excerpt=plain_text(entry.get("summary"), EXCERPT_CHARS),
                author=plain_text(entry.get("author"), 200),
                published_at=_from_epoch(timegm(published)) if published else None,
                tags=[t.get("term") for t in entry.get("tags", []) if t.get("term")],
            )
        )
        if len(items) == limit:
            break
    return items


def collect_rss(fetcher: Fetcher, source: SourceConfig) -> list[CollectedItem]:
    return parse_feed(fetcher.get(source.feed_url), source.max_items)


# --- Dev.to (https://developers.forem.com/api) -----------------------------------------------

DEVTO_ARTICLES = "https://dev.to/api/articles"


def _devto_item(article: dict) -> CollectedItem:
    tags = article.get("tag_list") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",")]
    return CollectedItem(
        url=article["url"],
        title=plain_text(article["title"])[:500],
        external_id=str(article["id"]),
        excerpt=plain_text(article.get("description"), EXCERPT_CHARS),
        author=(article.get("user") or {}).get("name"),
        published_at=_from_iso(article.get("published_at")),
        tags=tags,
        score=article.get("public_reactions_count"),
        comment_count=article.get("comments_count"),
    )


def collect_devto(fetcher: Fetcher, source: SourceConfig) -> list[CollectedItem]:
    """Latest articles plus, when top_days is set, the most popular ones of that period."""
    base = {"per_page": source.max_items}
    if tag := source.options.get("tag"):
        base["tag"] = tag
    requests = [base]
    if top_days := source.options.get("top_days"):
        requests.append(base | {"top": top_days})

    items: dict[str, CollectedItem] = {}
    for params in requests:
        for article in _json(fetcher.get(DEVTO_ARTICLES, params), "Dev.to"):
            item = _devto_item(article)
            items[item.external_id] = item
    return list(items.values())


# --- Hacker News (https://hn.algolia.com/api) -----------------------------------------------

HN_SEARCH = "https://hn.algolia.com/api/v1/search"
HN_ITEM = "https://news.ycombinator.com/item?id="


def collect_hackernews(fetcher: Fetcher, source: SourceConfig) -> list[CollectedItem]:
    params = {"tags": source.options.get("tags", "front_page"), "hitsPerPage": source.max_items}
    items = []
    for hit in _json(fetcher.get(HN_SEARCH, params), "Hacker News").get("hits", []):
        title = plain_text(hit.get("title"))
        if not title:
            continue
        # Ask HN / text posts have no external link; use the discussion page.
        url = hit.get("url") or f"{HN_ITEM}{hit['objectID']}"
        items.append(
            CollectedItem(
                url=url,
                title=title[:500],
                external_id=str(hit["objectID"]),
                excerpt=plain_text(hit.get("story_text"), EXCERPT_CHARS),
                author=hit.get("author"),
                published_at=_from_epoch(hit.get("created_at_i")),
                tags=[],
                score=hit.get("points"),
                comment_count=hit.get("num_comments"),
            )
        )
    return items


# --- Stack Overflow (https://api.stackexchange.com/docs) ------------------------------------

SE_QUESTIONS = "https://api.stackexchange.com/2.3/questions"


def collect_stackoverflow(
    fetcher: Fetcher, source: SourceConfig, key: str | None = None
) -> list[CollectedItem]:
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
    body = _json(fetcher.get(SE_QUESTIONS, params), "Stack Exchange")
    if "error_id" in body:
        raise FetchError(f"Stack Exchange error {body['error_id']}: {body.get('error_name')}")
    items = []
    for question in body.get("items", []):
        items.append(
            CollectedItem(
                url=question["link"],
                # Stack Exchange returns titles HTML-encoded.
                title=plain_text(question["title"])[:500],
                external_id=str(question["question_id"]),
                author=plain_text((question.get("owner") or {}).get("display_name"), 200),
                published_at=_from_epoch(question.get("creation_date")),
                tags=question.get("tags", []),
                score=question.get("score"),
                # For Q&A sources the "comments" column holds the number of answers.
                comment_count=question.get("answer_count"),
                view_count=question.get("view_count"),
            )
        )
    return items


Adapter = Callable[[Fetcher, SourceConfig], list[CollectedItem]]


def adapters(stackexchange_key: str | None = None) -> dict[str, Adapter]:
    return {
        "rss": collect_rss,
        "devto": collect_devto,
        "hackernews": collect_hackernews,
        "stackoverflow": lambda fetcher, source: collect_stackoverflow(
            fetcher, source, stackexchange_key
        ),
    }
