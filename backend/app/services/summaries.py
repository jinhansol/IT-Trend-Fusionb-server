"""E1 AI summaries the web app may show. The summary job writes content_summaries; the
web app only reads them.

A summary is shown on a card when the card's source allows summaries, the summary is
done, and it was made for the same article: for News the whole URL group shares one
summary (same url_hash), so a change of representative row keeps it.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import Content, ContentSource, ContentSummary


def shown_summaries(db: Session, rows: list[Content], kind: str) -> dict[int, ContentSummary]:
    hashes = {row.url_hash for row in rows if row.source.ai_summary}
    if not hashes:
        return {}
    found = db.execute(
        select(Content.url_hash, ContentSummary)
        .join(Content, Content.id == ContentSummary.content_id)
        .join(ContentSource, ContentSource.id == Content.source_id)
        .where(
            Content.url_hash.in_(hashes),
            ContentSummary.status == "done",
            ContentSummary.kind == kind,
            ContentSource.ai_summary.is_(True),
        )
        .order_by(ContentSummary.updated_at.desc())
    )
    by_hash: dict[str, ContentSummary] = {}
    for url_hash, summary in found:
        by_hash.setdefault(url_hash, summary)
    return {
        row.id: by_hash[row.url_hash]
        for row in rows
        if row.source.ai_summary and row.url_hash in by_hash
    }
