"""Engine and session factories.

``create_engine`` does not open a connection; the first query does. The app
builds the engine inside ``create_app`` so importing modules stays side-effect free.
Schema is managed by Alembic only (no ``create_all`` here or in the app).
"""

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings


def create_db_engine(settings: Settings) -> Engine:
    url = settings.parsed_database_url()
    if "charset" not in url.query:
        url = url.update_query_dict({"charset": "utf8mb4"})

    engine = create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=settings.db_pool_recycle_seconds,
    )

    @event.listens_for(engine, "connect")
    def _set_session_defaults(dbapi_connection, _connection_record) -> None:
        # Store and compare timestamps in UTC regardless of the server's zone.
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("SET time_zone = '+00:00'")
        finally:
            cursor.close()

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
