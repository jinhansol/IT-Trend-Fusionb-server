"""Run the collector for each source, one source at a time.

- A MariaDB named lock per source (GET_LOCK, no wait) makes a second concurrent run
  of the same source record "skipped" instead of collecting twice.
- Every run is recorded in job_runs, so "failed" and "nothing new" are different.
- One failing source never stops the others.
- Fetching happens outside any transaction; saving is one transaction per source.
"""

from dataclasses import dataclass, field

from sqlalchemy import Engine, select, text
from sqlalchemy.orm import sessionmaker

from app.db.types import utc_now
from app.integrations.http import Fetcher
from app.integrations.sources import Adapter, CollectedItem, SourceConfig
from app.jobs.store import store_items
from app.models.content import ContentSource, JobRun
from app.services.tagging import load_tagger

JOB_NAME = "collect"
MAX_ERROR_CHARS = 1000


class UnknownSource(ValueError):
    pass


@dataclass
class SourceResult:
    slug: str
    status: str  # succeeded | failed | skipped | dry-run
    fetched: int = 0
    inserted: int = 0
    updated: int = 0
    error: str | None = None
    sample_titles: list[str] = field(default_factory=list)

    def line(self) -> str:
        counts = f"fetched {self.fetched}, new {self.inserted}, updated {self.updated}"
        detail = f" — {self.error}" if self.error else ""
        return f"{self.slug:<16} {self.status:<9} {counts}{detail}"


def _lock_name(source: ContentSource) -> str:
    return f"devhub:collect:{source.id}"  # MariaDB lock names are at most 64 chars


def _config(source: ContentSource) -> SourceConfig:
    return SourceConfig(
        adapter=source.adapter,
        feed_url=source.feed_url,
        options=dict(source.options or {}),
        max_items=source.max_items,
    )


def _error_text(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}"[:MAX_ERROR_CHARS]


class Collector:
    def __init__(self, engine: Engine, fetcher: Fetcher, adapters: dict[str, Adapter]) -> None:
        self._engine = engine
        self._sessions = sessionmaker(bind=engine, expire_on_commit=False)
        self._fetcher = fetcher
        self._adapters = adapters

    def sources(self, slugs: list[str] | None = None) -> list[ContentSource]:
        with self._sessions() as db:
            query = select(ContentSource).order_by(ContentSource.position)
            if slugs:
                rows = list(db.scalars(query.where(ContentSource.slug.in_(slugs))))
                missing = set(slugs) - {s.slug for s in rows}
                if missing:
                    raise UnknownSource(f"unknown source: {', '.join(sorted(missing))}")
                return rows
            return list(db.scalars(query.where(ContentSource.status == "active")))

    def fetch(self, source: ContentSource) -> list[CollectedItem]:
        return self._adapters[source.adapter](self._fetcher, _config(source))

    def dry_run(self, source: ContentSource) -> SourceResult:
        """Fetch and parse only. Nothing is written, not even a job_runs row."""
        try:
            items = self.fetch(source)
        except Exception as exc:  # report any adapter failure
            return SourceResult(source.slug, "failed", error=_error_text(exc))
        return SourceResult(
            source.slug, "dry-run", fetched=len(items), sample_titles=[i.title for i in items[:3]]
        )

    def run(self, source: ContentSource) -> SourceResult:
        with self._engine.connect() as lock:
            acquired = lock.scalar(text("SELECT GET_LOCK(:name, 0)"), {"name": _lock_name(source)})
            if acquired != 1:
                self._record(source, "skipped", error="another run of this source is in progress")
                return SourceResult(source.slug, "skipped", error="already running")
            try:
                return self._run_locked(source)
            finally:
                lock.execute(text("SELECT RELEASE_LOCK(:name)"), {"name": _lock_name(source)})
                lock.commit()

    def _record(self, source: ContentSource, status: str, error: str | None = None) -> None:
        now = utc_now()
        with self._sessions.begin() as db:
            db.add(
                JobRun(
                    job_name=JOB_NAME,
                    source_id=source.id,
                    status=status,
                    started_at=now,
                    finished_at=now,
                    error_summary=error,
                )
            )

    def _run_locked(self, source: ContentSource) -> SourceResult:
        with self._sessions.begin() as db:
            job = JobRun(job_name=JOB_NAME, source_id=source.id, status="running")
            db.add(job)
        result = SourceResult(source.slug, "running")
        try:
            items = self.fetch(source)
            result.fetched = len(items)
            with self._sessions.begin() as db:
                db_source = db.get(ContentSource, source.id)
                stored = store_items(db, db_source, items, load_tagger(db))
            result.inserted, result.updated = stored.inserted, stored.updated
            result.status = "succeeded"
        except Exception as exc:  # a source failure is recorded, not raised
            result.status, result.error = "failed", _error_text(exc)

        with self._sessions.begin() as db:
            row = db.get(JobRun, job.id)
            row.status = result.status
            row.finished_at = utc_now()
            row.fetched_count = result.fetched
            row.inserted_count = result.inserted
            row.updated_count = result.updated
            row.failed_count = 1 if result.status == "failed" else 0
            row.error_summary = result.error
        return result
