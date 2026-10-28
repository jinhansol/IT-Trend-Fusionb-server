"""Collector command line. Runs separately from the web app.

    uv run python -m app.jobs collect                    every active source
    uv run python -m app.jobs collect --source devto     one or more sources
    uv run python -m app.jobs collect --dry-run          fetch and parse only, save nothing

Exit status is 1 when any source failed.
"""

import argparse
import sys

from app.core.config import get_settings
from app.db.session import create_db_engine
from app.integrations.http import HttpFetcher
from app.integrations.sources import adapters
from app.jobs.runner import Collector, UnknownSource


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.jobs")
    commands = parser.add_subparsers(dest="command", required=True)
    collect = commands.add_parser("collect", help="collect content from the configured sources")
    collect.add_argument("--source", action="append", dest="sources", metavar="SLUG")
    collect.add_argument("--dry-run", action="store_true", help="fetch and parse, save nothing")
    args = parser.parse_args(argv)

    settings = get_settings()
    key = settings.stackexchange_key.get_secret_value() if settings.stackexchange_key else None
    engine = create_db_engine(settings)
    fetcher = HttpFetcher(settings)
    try:
        collector = Collector(engine, fetcher, adapters(key))
        try:
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
        + (" (dry run, nothing saved)" if args.dry_run else "")
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
