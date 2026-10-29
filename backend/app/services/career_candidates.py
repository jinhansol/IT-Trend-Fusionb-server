"""Roles a user saved while exploring careers (P3).

Writes only user_career_candidates. Saving or removing a candidate never creates or
changes a learning goal, never turns personalization on and never touches learning
progress or XP. The count limit holds under concurrent requests: each write first
locks the user's row, so one user's writes run one after another.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.career import CareerRole, UserCareerCandidate
from app.models.user import User
from app.schemas.career import CandidateList, CandidateOut, RoleRef
from app.services.career_catalog import CareerRoleNotFound, published_role
from app.services.transactions import lock_user, with_retry, write_transaction

CANDIDATE_LIMIT = 10


class CandidateLimitReached(AppError):
    status_code = 409
    code = "CANDIDATE_LIMIT"

    def __init__(self) -> None:
        super().__init__(f"You can save up to {CANDIDATE_LIMIT} career candidates")


def _out(candidate: UserCareerCandidate, role: CareerRole) -> CandidateOut:
    return CandidateOut(
        role=RoleRef(slug=role.slug, name=role.name, available=role.status == "published"),
        note=candidate.note,
        saved_at=candidate.created_at,
    )


def list_candidates(db: Session, user: User) -> CandidateList:
    rows = db.execute(
        select(UserCareerCandidate, CareerRole)
        .join(CareerRole, CareerRole.id == UserCareerCandidate.role_id)
        .where(UserCareerCandidate.user_id == user.id)
        .order_by(UserCareerCandidate.created_at, CareerRole.position)
    ).all()
    return CandidateList(items=[_out(c, r) for c, r in rows], limit=CANDIDATE_LIMIT)


def save_candidate(db: Session, user: User, role_slug: str, note: str | None) -> CandidateOut:
    return with_retry(lambda: _save(db, user, role_slug, note))


def _save(db: Session, user: User, role_slug: str, note: str | None) -> CandidateOut:
    with write_transaction(db):
        lock_user(db, user.id)
        role = published_role(db, role_slug)  # retired roles cannot be newly saved
        candidate = db.get(UserCareerCandidate, (user.id, role.id))
        if candidate is None:
            count = db.scalar(
                select(func.count())
                .select_from(UserCareerCandidate)
                .where(UserCareerCandidate.user_id == user.id)
            )
            if count >= CANDIDATE_LIMIT:
                raise CandidateLimitReached()
            candidate = UserCareerCandidate(user_id=user.id, role_id=role.id, note=note)
            db.add(candidate)
        else:
            candidate.note = note
        db.flush()
        return _out(candidate, role)


def remove_candidate(db: Session, user: User, role_slug: str) -> None:
    """Idempotent. Works for retired roles too, so old saves can be cleaned up."""

    def remove() -> None:
        with write_transaction(db):
            role_id = db.scalar(select(CareerRole.id).where(CareerRole.slug == role_slug))
            if role_id is None:
                raise CareerRoleNotFound()
            candidate = db.get(UserCareerCandidate, (user.id, role_id))
            if candidate is not None:
                db.delete(candidate)

    with_retry(remove)
