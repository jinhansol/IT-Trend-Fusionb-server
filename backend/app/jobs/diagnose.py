"""Read-only feed diagnosis: `python -m app.jobs diagnose`.

Reads content/sources.yaml directly (no database connection, nothing written), so it
also works for paused sources and for candidates whose terms are not checked yet.
Each feed is requested only when its robots.txt allows it, once, through the
collector's own HttpFetcher and RSS parser, and reported with the numbers needed to
judge supply and schedule: items in the feed, newest date, items of the last 7 and
30 days, entries without a date, duplicate links after URL normalization, and how
many hours the newest `max_items` entries cover compared with the gap between
scheduled runs (a window shorter than the gap loses articles).
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from app.content_loader.taxonomy import SourceDef
from app.integrations.http import Fetcher, FetchError
from app.integrations.robots import RobotsPolicy, guard_redirects
from app.integrations.sources import parse_feed
from app.jobs.schedule import Schedule
from app.jobs.store import normalize_url, url_hash

FEED_ENTRIES = 1000  # read the whole feed, not just max_items, to measure it
SAFETY = 1.5  # the window should cover the gap between runs with this margin


@dataclass
class FeedReport:
    slug: str
    group: str
    status: str
    terms: str
    outcome: str = "ok"  # ok | not requested | failed
    detail: str | None = None
    items: int = 0
    skipped: int = 0
    no_date: int = 0
    duplicates: int = 0
    with_excerpt: int = 0
    newest: datetime | None = None
    last_7d: int = 0
    last_30d: int = 0
    window_hours: float | None = None
    gap_hours: int | None = None
    titles: list[str] = field(default_factory=list)

    @property
    def schedule_risk(self) -> str:
        if self.window_hours is None or self.gap_hours is None:
            return "-"
        return "risk" if self.window_hours < self.gap_hours * SAFETY else "ok"

    def line(self) -> str:
        head = f"{self.slug:<16} {self.group:<4} {self.status:<6} terms:{self.terms:<10}"
        if self.outcome != "ok":
            return f"{head} {self.outcome} — {self.detail}"
        newest = self.newest.strftime("%Y-%m-%d") if self.newest else "-"
        window = "-" if self.window_hours is None else f"{self.window_hours:.0f}h"
        return (
            f"{head} items {self.items:>3}  newest {newest}  7d {self.last_7d:>3}  "
            f"30d {self.last_30d:>3}  no-date {self.no_date}  dup {self.duplicates}  "
            f"excerpt {self.with_excerpt}/{self.items}  window {window} "
            f"vs every {self.gap_hours}h: {self.schedule_risk}"
            + (f"  ({self.detail})" if self.detail else "")
        )


def group_of(source: SourceDef) -> str:
    return "news" if source.kind == "news" else "dev"


def largest_gap(hours: list[int]) -> int:
    ordered = sorted(hours)
    gaps = [b - a for a, b in zip(ordered, ordered[1:], strict=False)]
    gaps.append(24 - ordered[-1] + ordered[0])
    return max(gaps)


def diagnose(
    sources: list[SourceDef],
    fetcher: Fetcher,
    schedule: Schedule,
    now: datetime | None = None,
) -> list[FeedReport]:
    now = now or datetime.now(UTC).replace(tzinfo=None)
    robots = RobotsPolicy(fetcher)
    reports = []
    for source in sources:
        group = group_of(source)
        report = FeedReport(
            source.slug,
            group,
            source.status,
            source.options.get("terms", "unverified"),
            gap_hours=largest_gap(schedule.groups[group].hours),
        )
        reports.append(report)
        if source.adapter != "rss" or not source.feed_url:
            report.outcome, report.detail = "not requested", "not an RSS source"
            continue
        verdict = robots.check(source.feed_url)
        if not verdict.allowed:
            report.outcome, report.detail = "not requested", verdict.reason
            continue
        try:
            with guard_redirects(fetcher, robots):  # each redirect hop is checked too
                batch = parse_feed(fetcher.get(source.feed_url), FEED_ENTRIES)
        except FetchError as exc:
            report.outcome, report.detail = "failed", str(exc)
            continue
        _measure(report, batch, source.max_items, now)
    return reports


def _measure(report: FeedReport, batch, max_items: int, now: datetime) -> None:
    items = batch.items
    report.items = len(items)
    report.skipped = sum(batch.skipped.values())
    report.no_date = sum(1 for i in items if i.published_at is None)
    hashes = [url_hash(normalize_url(i.url)) for i in items]
    report.duplicates = len(hashes) - len(set(hashes))
    report.with_excerpt = sum(1 for i in items if i.excerpt)
    dates = sorted((i.published_at for i in items if i.published_at), reverse=True)
    if dates:
        report.newest = dates[0]
        report.last_7d = sum(1 for d in dates if now - d < timedelta(days=7))
        report.last_30d = sum(1 for d in dates if now - d < timedelta(days=30))
    # One run keeps the newest max_items entries the feed lists; older ones are lost if
    # they fall out of the feed before the next run.
    collected = dates[:max_items]
    if len(collected) > 1:
        report.window_hours = (collected[0] - collected[-1]).total_seconds() / 3600
    if report.skipped:
        reasons = ", ".join(f"{r} {n}" for r, n in batch.skipped.most_common())
        report.detail = "; ".join(filter(None, [report.detail, f"skipped: {reasons}"]))
    report.titles = [i.title for i in items[:3]]
