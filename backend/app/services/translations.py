"""Korean AI translations of English news: which ones may be shown.

The translation job writes content_translations; the web app only reads them. A
translation is shown only while its source still allows translation and the item's
title and excerpt are still the text it was made from (same input hash).
"""

import hashlib
import unicodedata

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import Content, ContentTranslation

PROMPT_VERSION = "translate-ko-e1.1"


def input_hash(title: str, excerpt: str | None) -> str:
    material = "\n".join(
        [
            PROMPT_VERSION,
            unicodedata.normalize("NFC", title),
            unicodedata.normalize("NFC", excerpt or ""),
        ]
    )
    return hashlib.sha256(material.encode()).hexdigest()


def shown_translations(db: Session, rows: list[Content]) -> dict[int, ContentTranslation]:
    allowed = {row.id: row for row in rows if row.source.ai_translation}
    if not allowed:
        return {}
    found = db.scalars(
        select(ContentTranslation).where(
            ContentTranslation.content_id.in_(list(allowed)), ContentTranslation.status == "done"
        )
    )
    return {
        t.content_id: t
        for t in found
        if t.input_hash == input_hash(allowed[t.content_id].title, allowed[t.content_id].excerpt)
    }
