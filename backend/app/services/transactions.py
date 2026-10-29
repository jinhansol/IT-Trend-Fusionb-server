"""Write-transaction helpers shared by the services that write user records.

Write transactions run at READ COMMITTED: under MariaDB's default REPEATABLE READ,
plain reads made after a lock would still see the snapshot taken before it and miss
rows a concurrent transaction committed while we waited.
"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager

from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.models.user import User

# MariaDB: deadlock / lock wait timeout. Safe to retry the whole transaction.
_RETRYABLE_ERRORS = (1213, 1205)
_MAX_ATTEMPTS = 3


def with_retry[T](operation: Callable[[], T]) -> T:
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            return operation()
        except OperationalError as exc:
            code = getattr(exc.orig, "args", (None,))[0]
            if code not in _RETRYABLE_ERRORS or attempt == _MAX_ATTEMPTS:
                raise
    raise AssertionError("unreachable")


@contextmanager
def write_transaction(db: Session) -> Iterator[None]:
    with db.begin():
        db.connection(execution_options={"isolation_level": "READ COMMITTED"})
        yield


def lock_user(db: Session, user_id: int) -> None:
    """Serialize one user's writes inside a write transaction, so count limits
    (saved candidates, active goals) stay exact under concurrent requests."""
    db.execute(select(User.id).where(User.id == user_id).with_for_update())
