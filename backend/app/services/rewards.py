"""XP ledger and level calculation.

Total XP is the sum of the ledger; the level is computed from it and never stored,
so the level curve can change without migrating data.
"""

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.progress import XpLedgerEntry

ER_DUP_ENTRY = 1062


@dataclass(frozen=True)
class LevelInfo:
    level: int
    total_xp: int
    xp_into_level: int
    xp_for_next_level: int


@dataclass(frozen=True)
class GrantedReward:
    amount: int
    reason: str
    source_type: str
    source_id: int


def level_info(total_xp: int, settings: Settings) -> LevelInfo:
    """Level 1 starts at 0 XP. Reaching level 2 takes level_base_xp; every later
    level needs level_step_xp more than the previous one (100, 150, 200, ...)."""
    level, remaining, needed = 1, total_xp, settings.level_base_xp
    while remaining >= needed:
        remaining -= needed
        level += 1
        needed += settings.level_step_xp
    return LevelInfo(level, total_xp, remaining, needed)


def total_xp(db: Session, user_id: int) -> int:
    return db.scalar(
        select(func.coalesce(func.sum(XpLedgerEntry.amount), 0)).where(
            XpLedgerEntry.user_id == user_id
        )
    )


def grant_once(
    db: Session,
    settings: Settings,
    *,
    user_id: int,
    amount: int,
    reason: str,
    source_type: str,
    source_id: int,
    idempotency_key: str,
) -> GrantedReward | None:
    """Add a ledger entry unless this (user, idempotency_key) was already granted.

    Runs in a savepoint so a duplicate only undoes this insert, not the caller's
    transaction. Returns None when nothing was granted.
    """
    try:
        with db.begin_nested():
            db.add(
                XpLedgerEntry(
                    user_id=user_id,
                    amount=amount,
                    reason=reason,
                    source_type=source_type,
                    source_id=source_id,
                    idempotency_key=idempotency_key,
                    policy_version=settings.xp_policy_version,
                )
            )
    except IntegrityError as exc:
        if getattr(exc.orig, "args", (None,))[0] != ER_DUP_ENTRY:
            raise  # only "already granted" is expected here
        return None
    return GrantedReward(amount, reason, source_type, source_id)
