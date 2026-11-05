"""Collector and AI job command line. Runs separately from the web app.

    uv run python -m app.jobs collect                    every active, terms-approved source
    uv run python -m app.jobs collect --source bloter    one or more sources (same rule)
    uv run python -m app.jobs collect --dry-run          fetch and parse only, save nothing
    uv run python -m app.jobs diagnose [--source SLUG]   read-only feed check from sources.yaml
    uv run python -m app.jobs trial MANIFEST [--dry-run] a manual 48-hour trial (app/jobs/trial.py)
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

collect saves only sources that are active and whose options.terms is approved; any
other source is reported as "refused" without a request or a database write. --dry-run
and diagnose write nothing and may read paused or unverified sources. Every RSS request
of collect, --dry-run and diagnose is preceded by a robots.txt check (app/integrations/
robots.py). diagnose needs no database: it reads content/sources.yaml.
"""

import argparse
import shutil
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import text as sql

from app.content_loader.taxonomy import read_sources
from app.core.config import get_settings
from app.db.session import create_db_engine, create_session_factory
from app.db.types import utc_now
from app.integrations.gemini import GeminiNotConfigured, gemini_client
from app.integrations.http import FetchError, HttpFetcher
from app.integrations.robots import RobotsPolicy
from app.integrations.sources import adapters
from app.jobs import trial as trial_mod
from app.jobs.article_bodies import WEBDEV_HOSTS, finished_ids, webdev_bodies
from app.jobs.diagnose import diagnose
from app.jobs.runner import Collector, UnknownSource
from app.jobs.schedule import GROUPS, SCHEDULE_FILE, check_sources, crontab, load_schedule
from app.jobs.summarize import require_general_database, summarize_contents
from app.services.experiment_policy import POLICY_PREFIX as POLICY
from app.services.experiment_policy import PolicyError, is_experiment
from app.summaries.policy import Budget

SOURCES_FILE = Path(__file__).resolve().parents[2] / "content" / "sources.yaml"


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
    check = commands.add_parser("diagnose", help="read-only feed check (no database)")
    picked = check.add_mutually_exclusive_group()
    picked.add_argument("--source", action="append", dest="sources", metavar="SLUG")
    picked.add_argument("--group", choices=GROUPS)
    check.add_argument("--sources-file", type=Path, default=SOURCES_FILE, help=argparse.SUPPRESS)
    check.add_argument("--schedule", type=Path, default=SCHEDULE_FILE, help=argparse.SUPPRESS)
    trial = commands.add_parser("trial", help="manual trial: one notice page and one Atom entry")
    trial.add_argument("manifest", type=Path)
    trial.add_argument("--dry-run", action="store_true", help="fetch and parse, no database")
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
    if args.command == "diagnose":
        return _diagnose(args, settings)
    if args.command == "trial":
        return _trial(args, settings)
    if args.command == "collect-report":
        return _report(settings, args.days)
    if args.command != "collect":
        return _model_job(args, settings)
    key = settings.stackexchange_key.get_secret_value() if settings.stackexchange_key else None
    engine = create_db_engine(settings)
    fetcher = HttpFetcher(settings)
    try:
        collector = Collector(engine, fetcher, adapters(key), RobotsPolicy(fetcher))
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
    refused = sum(r.status == "refused" for r in results)
    blocked = sum(r.status == "refused" and str(r.error).startswith(POLICY) for r in results)
    print(
        f"database: {settings.database_name} — {len(results)} sources, {failed} failed"
        + (f", {refused} refused" if refused else "")
        + (f" (group {args.group})" if args.group else "")
        + (" (dry run, nothing saved)" if args.dry_run else "")
    )
    return 1 if failed or blocked else 0


def _diagnose(args, settings) -> int:
    """Read-only: sources.yaml + robots.txt + one request per feed; no database."""
    listed = read_sources(args.sources_file).sources
    if args.sources:
        unknown = set(args.sources) - {s.slug for s in listed}
        if unknown:
            print(f"unknown source: {', '.join(sorted(unknown))}", file=sys.stderr)
            return 2
        listed = [s for s in listed if s.slug in args.sources]
    elif args.group:
        listed = [s for s in listed if (s.kind == "news") == (args.group == "news")]
    # Experiment sources are checked against the database actually connected; general
    # ones never open a database connection.
    engine = create_db_engine(settings) if any(is_experiment(s) for s in listed) else None
    fetcher = HttpFetcher(settings)
    try:
        reports = diagnose(listed, fetcher, load_schedule(args.schedule), engine=engine)
    finally:
        fetcher.close()
        if engine is not None:
            engine.dispose()
    for report in reports:
        print(report.line(), flush=True)
        for title in report.titles:
            print(f"    · {title}")
    failed = sum(r.outcome == "failed" for r in reports)
    blocked = sum(r.outcome == "not requested" for r in reports)
    print(
        f"diagnose — {len(reports)} sources, {failed} failed, {blocked} not requested "
        "(read-only, nothing saved)"
    )
    refused = sum(str(r.detail or "").startswith(POLICY) for r in reports)
    return 1 if failed or refused else 0


def _trial(args, settings) -> int:
    """Manifest and window first, then the database, then the network (trial.py)."""
    try:
        manifest = trial_mod.read_manifest(args.manifest)
        trial_mod.check_window(manifest, datetime.now(UTC))
    except trial_mod.TrialRefused as exc:
        print(f"Refused: {exc}; nothing was requested or saved", file=sys.stderr)
        return 2
    engine = None if args.dry_run else create_db_engine(settings)
    fetcher = HttpFetcher(settings, allowed_hosts=trial_mod.input_hosts(manifest), max_attempts=1)
    try:
        report = trial_mod.run(
            manifest,
            fetcher,
            engine=engine,
            sessions=create_session_factory(engine) if engine else None,
            dry_run=args.dry_run,
        )
    except trial_mod.TrialRefused as exc:
        print(f"Refused: {exc}", file=sys.stderr)
        return 2
    except FetchError as exc:
        print(f"Failed: {exc}; nothing was saved", file=sys.stderr)
        return 1
    finally:
        fetcher.close()
        if engine is not None:
            engine.dispose()
    for index, (item, collected) in enumerate(report.items):
        stored = report.stored[index] if report.stored else None
        outcome = f"new {stored.inserted}, updated {stored.updated}" if stored else "dry run"
        print(f"{item.source.slug:<24} {item.kind:<12} {collected.url} — {outcome}")
    print(f"trial {manifest.trial} — {report.requests} requests, expires {manifest.expires_at}")
    return 0


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
    # Before any body file is read or a model client exists: never in devhub_experiment.
    engine = create_db_engine(settings)
    try:
        require_general_database(engine)
    except PolicyError as exc:
        engine.dispose()
        print(f"Refused: {exc}; nothing was read, sent or saved", file=sys.stderr)
        return 2
    bodies = {}
    for spec in getattr(args, "body", []):
        url, sep, path = spec.partition("=")
        if not sep or not Path(path).is_file():
            engine.dispose()
            print(f"--body expects URL=FILE with an existing file: {spec}", file=sys.stderr)
            return 2
        form = "markdown" if path.endswith(".md") else "html"
        bodies[url] = (form, Path(path).read_text(encoding="utf-8"))
    try:
        client = gemini_client(settings)
    except GeminiNotConfigured as exc:
        engine.dispose()
        print(f"{exc}; nothing was sent or saved", file=sys.stderr)
        return 2

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
