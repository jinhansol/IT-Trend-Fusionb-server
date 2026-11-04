"""Summarize News and Dev items with the E1 summarizer, once per article text.

Only items whose source has ai_summary on, with approved terms, are touched; experiment
sources never are, and nothing runs at all against devhub_experiment (checked before
any body is read, any model client is used or anything is written). The article
body comes from `bodies`, supplied by the caller (HTML or Markdown); the feed excerpt is never
summarized, so an item without a body is left alone. A stored done or skipped result
for the same input hash is kept without a model call; a failure is retried on later
runs up to MAX_ATTEMPTS. Each item is saved in its own transaction; contents rows are
never changed.
"""

from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import Engine, select
from sqlalchemy.orm import selectinload, sessionmaker

from app.db.types import utc_now
from app.integrations.llm import LLMClient
from app.models.content import Content, ContentSource, ContentSummary
from app.services.experiment_policy import (
    PolicyError,
    engine_is_experiment,
    is_experiment_connection,
)
from app.services.source_terms import ai_summary_allowed, allows_ai_summary
from app.summaries.policy import Budget
from app.summaries.prompts import PROMPT_VERSIONS
from app.summaries.summarizer import Summarizer, SummaryInput

MAX_ATTEMPTS = 3
Body = tuple[str, str]  # ("html" | "markdown", text)
BodyProvider = Callable[[Content], Body | None]


@dataclass
class SummarizeResult:
    done: int = 0
    failed: int = 0
    skipped: int = 0  # insufficient input, refused, invalid input
    kept: int = 0  # a stored result for the same text was kept
    no_body: int = 0
    calls: int = 0
    stopped: str | None = None  # budget_exhausted | circuit_open


def summary_kind(source: ContentSource) -> str:
    return "news" if source.kind == "news" else "dev"


def require_general_database(engine: Engine) -> None:
    """AI summaries are refused in the experiment database (A1); PolicyError otherwise."""
    if engine_is_experiment(engine):
        raise PolicyError("summaries_refused_in_experiment_database")
    try:
        with engine.connect() as connection:
            experiment = is_experiment_connection(connection)
    except PolicyError:
        raise
    except Exception:
        raise PolicyError("database_unverified") from None
    if experiment:
        raise PolicyError("summaries_refused_in_experiment_database")


def summarize_contents(
    engine: Engine, client: LLMClient, bodies: BodyProvider, budget: Budget | None = None
) -> SummarizeResult:
    require_general_database(engine)
    budget = budget or Budget()
    summarizer = Summarizer(client, budget)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    result = SummarizeResult()
    with sessions() as db:
        items = list(
            db.scalars(
                select(Content)
                .join(ContentSource, ContentSource.id == Content.source_id)
                .where(
                    ai_summary_allowed(),
                    ContentSource.kind.in_(("news", "blog")),
                    ContentSource.status != "retired",
                )
                .order_by(Content.sort_at.desc(), Content.id.desc())
                .options(selectinload(Content.source))
            )
        )
        existing = {
            s.content_id: s
            for s in db.scalars(
                select(ContentSummary).where(ContentSummary.content_id.in_([i.id for i in items]))
            )
        }

    for item in items:
        if not allows_ai_summary(item.source):  # experiment rows never reach a body or model
            continue
        body = bodies(item)
        if body is None:
            result.no_body += 1
            continue
        form, text = body
        kind = summary_kind(item.source)
        request = SummaryInput(
            kind=kind,
            url=item.url,
            title=item.title,
            html=text if form == "html" else None,
            markdown=text if form == "markdown" else None,
        )
        digest = summarizer.input_hash_of(request)
        previous = existing.get(item.id)
        same_text = previous is not None and digest is not None and previous.input_hash == digest
        if same_text and (
            previous.status in ("done", "skipped") or previous.attempts >= MAX_ATTEMPTS
        ):
            result.kept += 1
            continue

        calls_before = budget.calls
        outcome = summarizer.summarize(request)
        result.calls += budget.calls - calls_before
        if outcome.skip_reason in ("budget_exhausted", "circuit_open"):
            result.stopped = outcome.skip_reason
            break

        with sessions.begin() as db:
            row = db.get(ContentSummary, item.id)
            if row is None:
                row = ContentSummary(content_id=item.id, attempts=0)
                db.add(row)
            if not same_text:
                row.attempts = 0  # a new text gets a fresh set of attempts
            row.kind = kind
            row.status = outcome.status
            row.payload = outcome.payload
            row.partial_input = outcome.partial_input
            row.input_hash = outcome.input_hash or digest
            row.prompt_version = PROMPT_VERSIONS[kind]
            row.model = outcome.model
            row.skip_reason = outcome.skip_reason
            row.error_code = outcome.error_code
            row.attempts += 1  # runs that tried this text
            row.updated_at = utc_now()
        if outcome.status == "done":
            result.done += 1
        elif outcome.status == "failed":
            result.failed += 1
        else:
            result.skipped += 1
    return result
