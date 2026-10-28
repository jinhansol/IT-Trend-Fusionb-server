"""Load learning content into the database configured by DATABASE_URL.

    uv run python -m app.content_loader load content/python [content/other ...] [--dry-run]

All given tracks are validated first; then everything is written in one
transaction. --dry-run prints the changes and rolls back.
"""

import argparse
import sys
from pathlib import Path

from app.content_loader.loader import apply_track
from app.content_loader.schema import ContentError, read_track_directory
from app.core.config import get_settings
from app.db.session import create_db_engine, create_session_factory


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.content_loader")
    commands = parser.add_subparsers(dest="command", required=True)
    load = commands.add_parser("load", help="validate and upsert track directories")
    load.add_argument("directories", nargs="+", type=Path)
    load.add_argument("--dry-run", action="store_true", help="show changes without saving")
    args = parser.parse_args(argv)

    try:
        tracks = [read_track_directory(directory) for directory in args.directories]
    except ContentError as exc:
        print(f"Content error: {exc}", file=sys.stderr)
        return 1

    settings = get_settings()
    engine = create_db_engine(settings)
    session = create_session_factory(engine)()
    try:
        reports = [apply_track(session, track) for track in tracks]
        if args.dry_run:
            session.rollback()
        else:
            session.commit()
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
