"""Save collected items: insert new ones, refresh metrics of known ones, tag once.

The caller owns the transaction.
"""

import hashlib
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.types import utc_now
from app.integrations.sources import CollectedItem
from app.models.content import Content, ContentSource, ContentTechnology
from app.services.tagging import Tagger

# Tracking parameters that make one article look like many.
_TRACKING_PREFIXES = ("utm_", "fbclid", "gclid", "ref_src")


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not k.lower().startswith(_TRACKING_PREFIXES)
    ]
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), parts.path or "/", urlencode(query), "")
    )


def url_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()


@dataclass
class StoreResult:
    inserted: int = 0
    updated: int = 0


def _tag(db: Session, content: Content, tagger: Tagger) -> None:
    db.execute(
        delete(ContentTechnology).where(
            ContentTechnology.content_id == content.id, ContentTechnology.method == "rule"
        )
    )
    for tech_id in sorted(tagger.match(content.title, content.excerpt, content.source_tags)):
        db.add(ContentTechnology(content_id=content.id, technology_id=tech_id, method="rule"))


def store_items(
    db: Session, source: ContentSource, items: list[CollectedItem], tagger: Tagger
) -> StoreResult:
    result = StoreResult()
    by_hash: dict[str, CollectedItem] = {}
    for item in items:
        url = normalize_url(item.url)
        # A feed can list the same link twice; keep the first.
        by_hash.setdefault(url_hash(url), item)
        item.url = url

    existing = (
        {
            c.url_hash: c
            for c in db.scalars(
                select(Content).where(
                    Content.source_id == source.id, Content.url_hash.in_(list(by_hash))
                )
            )
        }
        if by_hash
        else {}
    )

    now = utc_now()
    for digest, item in by_hash.items():
        values = {
            "url": item.url[:2048],
            "title": item.title[:500],
            "external_id": item.external_id,
            "excerpt": item.excerpt,
            "author": (item.author or None) and item.author[:200],
            "source_tags": [t[:64] for t in item.tags[:20]],
            "score": item.score,
            "comment_count": item.comment_count,
            "view_count": item.view_count,
            "published_at": item.published_at,
        }
        content = existing.get(digest)
        if content is None:
            content = Content(
                source_id=source.id,
                url_hash=digest,
                summary_status="pending",
                collected_at=now,
                **values,
            )
            db.add(content)
            db.flush()
            _tag(db, content, tagger)
            result.inserted += 1
            continue

        retag = (content.title, content.excerpt, content.source_tags) != (
            values["title"],
            values["excerpt"],
            values["source_tags"],
        )
        changed = False
        for name, value in values.items():
            # A feed that stops sending a date or a metric does not erase what we have.
            if value is None and name in ("published_at", "score", "comment_count", "view_count"):
                continue
            if getattr(content, name) != value:
                setattr(content, name, value)
                changed = True
        if changed:
            result.updated += 1
        if retag:
            db.flush()
            _tag(db, content, tagger)
    db.flush()
    return result
