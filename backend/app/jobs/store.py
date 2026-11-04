"""Save collected items: insert new ones, refresh metrics of known ones, tag once.

The feed description (excerpt) is stored only for sources allowed to show it
(options.excerpt); it is used as tagging input unless options.tagging_excerpt is false
(experiment sources: only when it is true). Before anything is written, the session's
own connection is checked: experiment sources need their policy (metadata_store) and
devhub_experiment, and keep only the fields it allows; general sources are refused there.

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
from app.services import experiment_policy as ep
from app.services.source_terms import collect_refusal, shows_excerpt, tags_with_excerpt
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


def _tag(db: Session, content: Content, tagger: Tagger, excerpt: str | None) -> None:
    """Replace the item's rule tags. The collector owns only method "rule": a tag set
    another way (e.g. "manual") is never deleted or overwritten, and a rule match for
    that same technology is skipped, since (content_id, technology_id) is the key."""
    db.execute(
        delete(ContentTechnology).where(
            ContentTechnology.content_id == content.id, ContentTechnology.method == "rule"
        )
    )
    kept = set(
        db.scalars(
            select(ContentTechnology.technology_id).where(
                ContentTechnology.content_id == content.id
            )
        )
    )
    for tech_id in sorted(tagger.match(content.title, excerpt, content.source_tags) - kept):
        db.add(ContentTechnology(content_id=content.id, technology_id=tech_id, method="rule"))


def _guard(db: Session, source: ContentSource, items: list[CollectedItem]) -> list:
    """The write boundary: checked on this session's connection, without autoflush.
    Experiment sources are rechecked here as they are now (the collector passes the row
    it read again after the request): still active, terms still approved, policy."""
    with db.no_autoflush:
        if ep.is_experiment(source):
            if collect_refusal(source) is not None:
                code = "source_not_active" if source.status != "active" else "terms_not_approved"
                raise ep.PolicyError(code, source.slug)
            grant = ep.require(source, "metadata_store")
            ep.check_connection(db.connection(), experiment=True)
            return ep.project(items, grant)
        ep.check_connection(db.connection(), experiment=False)
    return items


def store_items(
    db: Session, source: ContentSource, items: list[CollectedItem], tagger: Tagger
) -> StoreResult:
    items = _guard(db, source, items)
    result = StoreResult()
    keep_excerpt = shows_excerpt(source)
    tag_excerpt = tags_with_excerpt(source)
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
            # The feed description is kept only when the source's terms allow showing it;
            # otherwise it is used for tagging and dropped.
            "excerpt": item.excerpt if keep_excerpt else None,
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
            _tag(db, content, tagger, item.excerpt if tag_excerpt else None)
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
            _tag(db, content, tagger, item.excerpt if tag_excerpt else None)
    db.flush()
    return result
