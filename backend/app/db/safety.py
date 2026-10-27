"""Guards that confirm which database a connection actually points at."""

from sqlalchemy import Engine, text

from app.core.config import TEST_DATABASE_SUFFIX


class UnsafeDatabaseError(RuntimeError):
    pass


def connected_database_name(engine: Engine) -> str:
    with engine.connect() as connection:
        return connection.execute(text("SELECT DATABASE()")).scalar_one() or ""


def assert_test_database(engine: Engine, expected_name: str) -> str:
    """Raise unless the live connection uses ``expected_name`` and it is a test database.

    Tests call this before running migrations or touching data.
    """
    actual = connected_database_name(engine)
    if actual != expected_name or not actual.endswith(TEST_DATABASE_SUFFIX):
        raise UnsafeDatabaseError(
            f"Refusing to run against database {actual!r} "
            f"(expected {expected_name!r} ending with {TEST_DATABASE_SUFFIX!r})"
        )
    return actual
