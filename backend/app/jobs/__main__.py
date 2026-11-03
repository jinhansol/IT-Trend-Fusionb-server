"""Collector and AI job command line. Runs separately from the web app.

    uv run python -m app.jobs collect                    every active source
    uv run python -m app.jobs collect --source bloter    one or more sources
    uv run python -m app.jobs collect --dry-run          fetch and parse only, save nothing
    uv run python -m app.jobs collect --group dev        the scheduled list for a group
    uv run python -m app.jobs crontab                    print the cron lines for the groups
    uv run python -m app.jobs collect-report --days 7    runs and new items per source
    uv run python -m app.jobs summarize --max-calls 1    AI summaries (sources with ai_summary)
    uv run python -m app.jobs summarize --body URL=FILE  summaries of bodies held locally

summarize calls Gemini (GEMINI_API_KEY, GEMINI_MODEL) for sources that have ai_summary on,
at most --max-calls requests per run. Without --body it fetches article pages only for
sources app/jobs/article_bodies.py knows how to check (none registered at present); with
--body it uses the given local HTML or Markdown files and downloads nothing.
--group reads content/collect-schedule.yaml (app/jobs/schedule.py); scheduled runs never
call Gemini. Exit status is 1 when any source or item failed, 2 for a usage or setup error.
"""

import argparse
import shutil
import sys
from datetime import timedelta
from pathlib import Path

from sqlalchemy import text as sql

from app.core.config import get_settings
from app.db.session import create_db_engine
from app.db.types import utc_now
from app.integrations.gemini import GeminiNotConfigured, gemini_client
from app.integrations.http import HttpFetcher
from app.integrations.sources import adapters
from app.jobs.article_bodies import WEBDEV_HOSTS, finished_ids, webdev_bodies
from app.jobs.runner import Collector, UnknownSource
from app.jobs.schedule import GROUPS, SCHEDULE_FILE, check_sources, crontab, load_schedule
from app.jobs.summarize import summarize_contents
from app.summaries.policy import Budget


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.jobs")
    commands = parser.add_subparsers(dest="command", required=True)
    collect = commands.add_parser("collect", help="collect content from the configured sources")
    which = collect.add_mutually_exclusive_group()
    which.add_argument("--source", action="append", dest="sources", metavar="SLUG")
    which.add_argument("--group", choices=GROUPS, help="the scheduled source list of a group")
    collect.add_argument("--dry-run", action="store_true", help="fetch and parse, save nothing")
    collect.add_argument("--schedule", type=Path, default=SCHEDULE_FILE, help=argparse.SUPPRESS)
    cron = commands.add_parser("crontab", help="print the cron lines for scheduled collection")
    cron.add_argument("--backend-dir", type=Path, default=Path(__file__).resolve().parents[2])
    cron.add_argument("--uv", default=shutil.which("uv") or "uv", help="absolute path of uv")
    cron.add_argument("--log-dir", type=Path, default=Path("/var/log/devhub"))
    cron.add_argument("--server-tz", default="UTC", help="the server's time zone (timedatectl)")
    cron.add_argument("--schedule", type=Path, default=SCHEDULE_FILE, help=argparse.SUPPRESS)
    report = commands.add_parser("collect-report", help="runs and new items per source")
    report.add_argument("--days", type=int, default=7)
    job = commands.add_parser("summarize", help="summarize articles with Gemini")
    job.add_argument("--max-calls", type=int, default=4, metavar="N")
    job.add_argument("--body", action="append", default=[], metavar="URL=FILE")
    args = parser.parse_args(argv)

    if args.command == "crontab":
        schedule = load_schedule(args.schedule)
        try:
            lines = crontab(schedule, args.backend_dir, args.uv, args.log_dir, args.server_tz)
        except ValueError as exc:
            print(exc, file=sys.stderr)
            return 2
        print(lines, end="")
        return 0
    settings = get_settings()
    if args.command == "collect-report":
        return _report(settings, args.days)
    if args.command != "collect":
        return _model_job(args, settings)
    key = settings.stackexchange_key.get_secret_value() if settings.stackexchange_key else None
    engine = create_db_engine(settings)
    fetcher = HttpFetcher(settings)
    try:
        collector = Collector(engine, fetcher, adapters(key))
        try:
            if args.group:
                listed = load_schedule(args.schedule).groups[args.group].sources
                sources, skipped = check_sources(
                    args.group, collector.sources(listed) if listed else []
                )
                for reason in skipped:
                    print(f"not collected: {reason}")
            else:
                sources = collector.sources(args.sources)
        except UnknownSource as exc:
            print(exc, file=sys.stderr)
            return 2
        results = []
        for source in sources:
            result = collector.dry_run(source) if args.dry_run else collector.run(source)
            results.append(result)
            print(result.line(), flush=True)
            for title in result.sample_titles:
                print(f"    · {title}")
    finally:
        fetcher.close()
        engine.dispose()

    failed = sum(r.status == "failed" for r in results)
    print(
        f"database: {settings.database_name} — {len(results)} sources, {failed} failed"
        + (f" (group {args.group})" if args.group else "")
        + (" (dry run, nothing saved)" if args.dry_run else "")
    )
    return 1 if failed else 0


_REPORT = sql(
    """
    SELECT s.slug, s.kind,
           COUNT(j.id) AS runs,
           COALESCE(SUM(j.status = 'succeeded'), 0) AS succeeded,
           COALESCE(SUM(j.status = 'failed'), 0) AS failed,
           COALESCE(SUM(j.status = 'skipped'), 0) AS skipped,
           COALESCE(SUM(j.inserted_count), 0) AS inserted,
           COALESCE(SUM(j.updated_count), 0) AS updated,
           COALESCE(SUM(j.fetched_count), 0) - COALESCE(SUM(j.inserted_count), 0) AS seen_again,
           MAX(CASE WHEN j.status = 'succeeded' THEN j.finished_at END) AS last_success,
           (SELECT AVG(TIMESTAMPDIFF(MINUTE, c.published_at, c.collected_at)) / 60
              FROM contents c
             WHERE c.source_id = s.id AND c.published_at IS NOT NULL
               AND c.collected_at >= :since) AS avg_delay_hours
      FROM content_sources s
      JOIN job_runs j ON j.source_id = s.id AND j.job_name = 'collect' AND j.started_at >= :since
     GROUP BY s.id, s.slug, s.kind
     ORDER BY s.position
    """
)


def _report(settings, days: int) -> int:
    """Read-only summary of job_runs and contents over the last `days` days."""
    if days < 1:
        print("--days must be at least 1", file=sys.stderr)
        return 2
    engine = create_db_engine(settings)
    try:
        with engine.connect() as connection:
            rows = connection.execute(_REPORT, {"since": utc_now() - timedelta(days=days)}).all()
    finally:
        engine.dispose()
    print(f"database: {settings.database_name} — last {days} days, {len(rows)} sources ran")
    print(
        "source            kind       runs ok fail skip  new upd seen-again"
        "  last success (UTC)   avg delay h"
    )
    for r in rows:
        delay = "-" if r.avg_delay_hours is None else f"{float(r.avg_delay_hours):.1f}"
        last = r.last_success.strftime("%Y-%m-%d %H:%M") if r.last_success else "-"
        print(
            f"{r.slug:<17} {r.kind:<9} {r.runs:>5} {r.succeeded:>2} {r.failed:>4} {r.skipped:>4}"
            f" {r.inserted:>4} {r.updated:>3} {r.seen_again:>10}  {last:<19} {delay:>11}"
        )
    return 0


def _model_job(args, settings) -> int:
    if args.max_calls < 1:
        print("--max-calls must be at least 1", file=sys.stderr)
        return 2
    bodies = {}
    for spec in getattr(args, "body", []):
        url, sep, path = spec.partition("=")
        if not sep or not Path(path).is_file():
            print(f"--body expects URL=FILE with an existing file: {spec}", file=sys.stderr)
            return 2
        form = "markdown" if path.endswith(".md") else "html"
        bodies[url] = (form, Path(path).read_text(encoding="utf-8"))
    try:
        client = gemini_client(settings)
    except GeminiNotConfigured as exc:
        print(f"{exc}; nothing was sent or saved", file=sys.stderr)
        return 2

    engine = create_db_engine(settings)
    budget = Budget(max_calls=args.max_calls)
    fetcher = None
    try:
        if bodies:
            result = summarize_contents(engine, client, lambda item: bodies.get(item.url), budget)
        else:
            fetcher = HttpFetcher(settings, allowed_hosts=WEBDEV_HOSTS)
            provider = webdev_bodies(fetcher, finished_ids(engine))
            result = summarize_contents(engine, client, provider, budget)
    finally:
        if fetcher is not None:
            fetcher.close()
        engine.dispose()
    print(f"database: {settings.database_name} — model {client.model} — {result}")
    if client.last_error:
        print(f"last error: {client.last_error}", file=sys.stderr)
    return 1 if result.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
