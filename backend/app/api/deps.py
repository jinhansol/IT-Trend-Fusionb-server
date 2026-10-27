from collections.abc import Iterator

from fastapi import Request
from sqlalchemy.orm import Session


def get_db(request: Request) -> Iterator[Session]:
    """One session per request. Read endpoints never commit; write use cases
    open their own transaction with ``with db.begin():``."""
    session: Session = request.app.state.session_factory()
    try:
        yield session
    finally:
        session.close()
