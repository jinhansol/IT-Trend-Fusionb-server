"""Load content files into the database configured by DATABASE_URL.

    uv run python -m app.content_loader load content/python [content/other ...] [--dry-run]
    uv run python -m app.content_loader technologies content/technologies.yaml [--dry-run]
    uv run python -m app.content_loader sources content/sources.yaml [--dry-run]

All given files are validated first; then everything is written in one
transaction. --dry-run prints the changes and rolls back.
"""

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

from sqlalchemy.orm import Session

from app.content_loader.loader import LoadReport, apply_track
from app.content_loader.schema import ContentError, read_track_directory
from app.content_loader.taxonomy import (
    apply_sources,
    apply_technologies,
    read_sources,
    read_technologies,
)
from app.core.config import get_settings
from app.db.session import create_db_engine, create_session_factory


def _parse(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m app.content_loader")
    commands = parser.add_subparsers(dest="command", required=True)
    load = commands.add_parser("load", help="validate and upsert track directories")
    load.add_argument("paths", nargs="+", type=Path)
    for name, help_text in (
        ("technologies", "validate and upsert the technology taxonomy file"),
        ("sources", "validate and upsert the collector sources file"),
    ):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("paths", nargs=1, type=Path)
    for command in commands.choices.values():
        command.add_argument("--dry-run", action="store_true", help="show changes without saving")
    return parser.parse_args(argv)


def _plan(args: argparse.Namespace) -> list[Callable[[Session], LoadReport]]:
    """Read and validate every file before touching the database."""
    if args.command == "load":
        tracks = [read_track_directory(path) for path in args.paths]
        return [lambda db, track=track: apply_track(db, track) for track in tracks]
    if args.command == "technologies":
        technologies = read_technologies(args.paths[0])
        return [lambda db: apply_technologies(db, technologies)]
    sources = read_sources(args.paths[0])
    return [lambda db: apply_sources(db, sources)]


def main(argv: list[str] | None = None) -> int:
    args = _parse(argv)
    try:
        steps = _plan(args)
    except ContentError as exc:
        print(f"Content error: {exc}", file=sys.stderr)
        return 1

    settings = get_settings()
    engine = create_db_engine(settings)
    session = create_session_factory(engine)()
    try:
        reports = [step(session) for step in steps]
        if args.dry_run:
            session.rollback()
        else:
            session.commit()
    except ContentError as exc:
        # Problems that need the database to detect (e.g. unknown technologies).
        session.rollback()
        print(f"Content error: {exc}", file=sys.stderr)
        return 1
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        engine.dispose()

    for report in reports:
        print(report.summary())
    print(
        f"database: {settings.database_name}"
        + (" (dry run, nothing saved)" if args.dry_run else "")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
