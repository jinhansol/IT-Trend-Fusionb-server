"""Column types shared by all models (MariaDB conventions from the design doc)."""

from datetime import UTC, datetime

from sqlalchemy.dialects.mysql import BIGINT, DATETIME

# Every PK/FK uses the same type so foreign keys never mismatch.
BigId = BIGINT(unsigned=True)
# Microsecond precision, stored as naive UTC (sessions run with time_zone '+00:00').
UtcDateTime = DATETIME(fsp=6)


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
