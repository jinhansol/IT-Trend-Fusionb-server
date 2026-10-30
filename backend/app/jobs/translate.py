"""Translate English news titles and excerpts into Korean, once per text.

Only items whose source has ai_translation on are touched. An item is translated when
it has no translation yet, when its title or excerpt changed (new input hash), or when
an earlier attempt failed and fewer than MAX_ATTEMPTS were made. Each item is saved in
its own transaction; contents rows are never changed.
"""

from dataclasses import dataclass

from sqlalchemy import Engine, select
from sqlalchemy.orm import selectinload, sessionmaker

from app.db.types import utc_now
from app.integrations.llm import LLMClient
from app.models.content import Content, ContentSource, ContentTranslation
from app.services.translations import PROMPT_VERSION, input_hash
from app.summaries.policy import Budget
from app.summaries.translate import translate

MAX_ATTEMPTS = 3


@dataclass
class TranslateResult:
    done: int = 0
    failed: int = 0
    calls: int = 0
    stopped: str | None = None  # budget_exhausted | circuit_open


def _due(existing: ContentTranslation | None, digest: str) -> bool:
    if existing is None or existing.input_hash != digest:
        return True
    return existing.status == "failed" and existing.attempts < MAX_ATTEMPTS


def translate_news(
    engine: Engine, client: LLMClient, budget: Budget | None = None
) -> TranslateResult:
    budget = budget or Budget()
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    result = TranslateResult()
    with sessions() as db:
        items = list(
            db.scalars(
                select(Content)
                .join(ContentSource, ContentSource.id == Content.source_id)
                .where(
                    ContentSource.kind == "news",
                    ContentSource.language == "en",
                    ContentSource.ai_translation.is_(True),
                    ContentSource.status != "retired",
                )
                .order_by(Content.sort_at.desc(), Content.id.desc())
                .options(selectinload(Content.source))
            )
        )
        existing = {
            t.content_id: t
            for t in db.scalars(
                select(ContentTranslation).where(
                    ContentTranslation.content_id.in_([i.id for i in items])
                )
            )
        }

    for item in items:
        digest = input_hash(item.title, item.excerpt)
        previous = existing.get(item.id)
        if not _due(previous, digest):
            continue
        if budget.circuit_open() or budget.exhausted():
            result.stopped = "circuit_open" if budget.circuit_open() else "budget_exhausted"
            break
        budget.record_call()
        result.calls += 1
        outcome = translate(client, item.title, item.excerpt)
        budget.record_outcome(failed=outcome.status == "failed")

        with sessions.begin() as db:
            row = db.get(ContentTranslation, item.id)
            if row is None:
                row = ContentTranslation(content_id=item.id, attempts=0)
                db.add(row)
            if row.input_hash != digest:
                row.attempts = 0  # a new text gets a fresh set of attempts
            row.input_hash = digest
            row.prompt_version = PROMPT_VERSION
            row.model = client.model
            row.attempts += 1
            row.status = outcome.status
            row.error_code = outcome.error_code
            if outcome.status == "done":
                row.title, row.excerpt = outcome.title, outcome.excerpt
            row.updated_at = utc_now()
        if outcome.status == "done":
            result.done += 1
        else:
            result.failed += 1
    return result
