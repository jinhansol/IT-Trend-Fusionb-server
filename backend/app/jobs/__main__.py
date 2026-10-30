"""Collector and AI job command line. Runs separately from the web app.

    uv run python -m app.jobs collect                    every active source
    uv run python -m app.jobs collect --source devto     one or more sources
    uv run python -m app.jobs collect --dry-run          fetch and parse only, save nothing
    uv run python -m app.jobs translate --max-calls 4    Korean titles for English news
    uv run python -m app.jobs summarize --body URL=FILE  summaries of bodies held locally

translate and summarize call Gemini (GEMINI_API_KEY, GEMINI_MODEL) for sources that have
ai_translation / ai_summary on, at most --max-calls requests per run. summarize never
downloads articles: each body is a local HTML or Markdown file given for its stored URL.
Exit status is 1 when any source or item failed, 2 for a usage or setup error.
"""

import argparse
import sys
from pathlib import Path

from app.core.config import get_settings
from app.db.session import create_db_engine
from app.integrations.gemini import GeminiNotConfigured, gemini_client
from app.integrations.http import HttpFetcher
from app.integrations.sources import adapters
from app.jobs.runner import Collector, UnknownSource
from app.jobs.summarize import summarize_contents
from app.jobs.translate import translate_news
from app.summaries.policy import Budget


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.jobs")
    commands = parser.add_subparsers(dest="command", required=True)
    collect = commands.add_parser("collect", help="collect content from the configured sources")
    collect.add_argument("--source", action="append", dest="sources", metavar="SLUG")
    collect.add_argument("--dry-run", action="store_true", help="fetch and parse, save nothing")
    for name, text in (("translate", "translate English news"), ("summarize", "summarize")):
        job = commands.add_parser(name, help=f"{text} with Gemini")
        job.add_argument("--max-calls", type=int, default=4, metavar="N")
        if name == "summarize":
            job.add_argument("--body", action="append", default=[], metavar="URL=FILE")
    args = parser.parse_args(argv)

    settings = get_settings()
    if args.command != "collect":
        return _model_job(args, settings)
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
    try:
        if args.command == "translate":
            result = translate_news(engine, client, budget)
        else:
            result = summarize_contents(engine, client, lambda item: bodies.get(item.url), budget)
    finally:
        engine.dispose()
    print(f"database: {settings.database_name} — model {client.model} — {result}")
    if client.last_error:
        print(f"last error: {client.last_error}", file=sys.stderr)
    return 1 if result.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
