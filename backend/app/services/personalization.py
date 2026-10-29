"""Personalization data (A-plan v0.2, P4): interests and self-rated skills.

The only module that reads or writes user_interests and user_skills. It never
touches goals, career candidates, learning progress, XP or the learner type, and no
other service imports it; profile_for_recommendation() is the one interface a
future recommendation feature (P5) may call. Nothing in P4 calls it.

- OFF keeps the data but the recommendation profile is empty.
- ON without data gives an empty profile; ON with data gives a profile built from
  published technologies only.
- Reset deletes this user's interests and skills only; the ON/OFF switch stays.
- Replacements are validated completely before anything is written and run in one
  transaction under the user's row lock, so an invalid request changes nothing and
  concurrent requests apply one after the other.
"""

from dataclasses import dataclass, field

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.content import Technology
from app.models.personalization import UserInterest, UserSkill
from app.models.user import User
from app.schemas.personalization import (
    InterestOut,
    InterestsUpdate,
    PersonalizationOut,
    SkillOut,
    SkillsUpdate,
)
from app.services.transactions import lock_user, with_retry, write_transaction

PUBLISHED = "published"


class InvalidTechnologies(AppError):
    status_code = 422

    def __init__(self, code: str, message: str, slugs: list[str]) -> None:
        super().__init__(message, code=code, details={"technologies": slugs})


@dataclass(frozen=True)
class RecommendationProfile:
    """What a recommendation feature may use. Empty unless personalization is ON."""

    enabled: bool
    interests: list[str] = field(default_factory=list)  # technology slugs
    skills: dict[str, str] = field(default_factory=dict)  # slug -> self-rated level

    @property
    def is_empty(self) -> bool:
        return not self.interests and not self.skills


def _enabled(user: User) -> bool:
    return bool(user.user_settings and user.user_settings.personalization_enabled)


# --- reading ------------------------------------------------------------------------------


def _interest_rows(db: Session, user_id: int):
    return db.execute(
        select(Technology)
        .join(UserInterest, UserInterest.technology_id == Technology.id)
        .where(UserInterest.user_id == user_id)
        .order_by(Technology.name, Technology.slug)
    ).scalars()


def _skill_rows(db: Session, user_id: int):
    return db.execute(
        select(Technology, UserSkill.level)
        .join(UserSkill, UserSkill.technology_id == Technology.id)
        .where(UserSkill.user_id == user_id)
        .order_by(Technology.name, Technology.slug)
    ).all()


def profile_for_recommendation(db: Session, user: User) -> RecommendationProfile:
    """The P5 interface. OFF -> empty; retired technologies are never included."""
    if not _enabled(user):
        return RecommendationProfile(enabled=False)
    return RecommendationProfile(
        enabled=True,
        interests=[t.slug for t in _interest_rows(db, user.id) if t.status == PUBLISHED],
        skills={t.slug: level for t, level in _skill_rows(db, user.id) if t.status == PUBLISHED},
    )


def get_personalization(db: Session, user: User) -> PersonalizationOut:
    """The user's own data, shown whether personalization is ON or OFF."""
    enabled = _enabled(user)
    profile = profile_for_recommendation(db, user)
    status = "off" if not enabled else ("empty" if profile.is_empty else "ready")
    return PersonalizationOut(
        enabled=enabled,
        profile_status=status,
        interests=[
            InterestOut(slug=t.slug, name=t.name, kind=t.kind, available=t.status == PUBLISHED)
            for t in _interest_rows(db, user.id)
        ],
        skills=[
            SkillOut(
                slug=t.slug,
                name=t.name,
                kind=t.kind,
                level=level,
                available=t.status == PUBLISHED,
            )
            for t, level in _skill_rows(db, user.id)
        ],
    )


# --- writing ------------------------------------------------------------------------------


def _resolve(db: Session, slugs: list[str], kept_ids: set[int]) -> dict[str, int]:
    """slug -> technology id. Unknown slugs are rejected; a retired technology is
    accepted only if the user already had it (kept), never as a new selection."""
    if not slugs:
        return {}
    found = {t.slug: t for t in db.scalars(select(Technology).where(Technology.slug.in_(slugs)))}
    unknown = sorted(set(slugs) - set(found))
    if unknown:
        raise InvalidTechnologies("UNKNOWN_TECHNOLOGY", "Unknown technologies", unknown)
    retired = sorted(
        slug for slug, tech in found.items() if tech.status != PUBLISHED and tech.id not in kept_ids
    )
    if retired:
        raise InvalidTechnologies(
            "RETIRED_TECHNOLOGY", "Retired technologies cannot be newly selected", retired
        )
    return {slug: tech.id for slug, tech in found.items()}


def replace_interests(db: Session, user: User, body: InterestsUpdate) -> PersonalizationOut:
    def replace() -> None:
        with write_transaction(db):
            lock_user(db, user.id)
            current = {
                row.technology_id: row
                for row in db.scalars(select(UserInterest).where(UserInterest.user_id == user.id))
            }
            wanted = set(_resolve(db, body.technologies, set(current)).values())
            for technology_id, row in current.items():
                if technology_id not in wanted:
                    db.delete(row)
            for technology_id in wanted - set(current):
                db.add(UserInterest(user_id=user.id, technology_id=technology_id))

    with_retry(replace)
    return get_personalization(db, user)


def replace_skills(db: Session, user: User, body: SkillsUpdate) -> PersonalizationOut:
    def replace() -> None:
        with write_transaction(db):
            lock_user(db, user.id)
            current = {
                row.technology_id: row
                for row in db.scalars(select(UserSkill).where(UserSkill.user_id == user.id))
            }
            ids = _resolve(db, [s.technology for s in body.skills], set(current))
            wanted = {ids[s.technology]: s.level for s in body.skills}
            for technology_id, row in current.items():
                if technology_id not in wanted:
                    db.delete(row)
                elif row.level != wanted[technology_id]:
                    row.level = wanted[technology_id]
            for technology_id, level in wanted.items():
                if technology_id not in current:
                    db.add(UserSkill(user_id=user.id, technology_id=technology_id, level=level))

    with_retry(replace)
    return get_personalization(db, user)


def reset(db: Session, user: User) -> None:
    """Delete this user's interests and skills. Idempotent; the switch is unchanged."""

    def wipe() -> None:
        with write_transaction(db):
            lock_user(db, user.id)
            db.execute(delete(UserInterest).where(UserInterest.user_id == user.id))
            db.execute(delete(UserSkill).where(UserSkill.user_id == user.id))

    with_retry(wipe)
