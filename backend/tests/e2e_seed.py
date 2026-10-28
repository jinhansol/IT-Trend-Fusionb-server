"""Seed Home/Dev content for the Playwright E2E run, from the stored sample responses.

    APP_ENV=test DATABASE_URL=...devhub_test uv run python -m tests.e2e_seed

E2E must not depend on external sites, so the real collector runs with the fake
fetcher. Refuses any database whose live name does not end with "_test".
"""

from app.core.config import get_settings
from app.db.safety import assert_test_database
from app.db.session import create_db_engine
from tests.collect_helpers import collect_all, seed_catalog
from tests.integration.test_content_api import shift_dates_to_now


def main() -> None:
    settings = get_settings()
    engine = create_db_engine(settings)
    try:
        name = assert_test_database(engine, settings.database_name)
        seed_catalog(engine)
        results = collect_all(engine)
        shift_dates_to_now(engine)
    finally:
        engine.dispose()
    failed = [slug for slug, r in results.items() if r.status != "succeeded"]
    if failed:
        raise SystemExit(f"seeding failed for: {', '.join(failed)}")
    print(f"database: {name} — seeded {len(results)} sources")


if __name__ == "__main__":
    main()
