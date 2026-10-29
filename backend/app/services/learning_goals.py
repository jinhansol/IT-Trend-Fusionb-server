"""Learning goals the user writes themself (P3; A-plan v0.2, C-1).

Career growth data: saved with personalization ON or OFF, never written by career
exploration, never cleared by a personalization reset. This service writes only
learning_goals; it reads learning progress to show where the user stands but never
changes progress or XP, and achieving a goal grants nothing.

Achieving is manual. achieved_at is set when a goal becomes achieved and cleared
when it leaves that state (re-achieving records a new time); a CHECK constraint
keeps the two consistent. At most ACTIVE_GOAL_LIMIT goals are active at once,
exact under concurrent requests (each write locks the user's row first).
"""

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.types import utc_now
from app.models.career import CareerRole, CareerRoleTechnology
from app.models.content import Technology
from app.models.goals import LearningGoal
from app.models.learning import LearningTrack, LearningUnit, LearningUnitTechnology
from app.models.progress import UserUnitProgress
from app.models.user import User
from app.schemas.goals import GoalCreate, GoalList, GoalOut, GoalTarget, GoalUnit, GoalUpdate
from app.schemas.learning import TrackRef
from app.services.career_catalog import CareerRoleNotFound
from app.services.learning_catalog import TechnologyNotFound, TrackNotFound
from app.services.transactions import lock_user, with_retry, write_transaction

ACTIVE_GOAL_LIMIT = 5
PUBLISHED = "published"
ACTIVE = "active"
ACHIEVED = "achieved"


class GoalNotFound(AppError):
    status_code = 404
    code = "GOAL_NOT_FOUND"

    def __init__(self) -> None:
        super().__init__("Goal not found")


class ActiveGoalLimitReached(AppError):
    status_code = 409
    code = "GOAL_LIMIT"

    def __init__(self) -> None:
        super().__init__(f"You can have up to {ACTIVE_GOAL_LIMIT} active goals")


# --- reading ------------------------------------------------------------------------------


def _target(db: Session, goal: LearningGoal) -> tuple[GoalTarget | None, list[LearningUnit]]:
    """The goal's target and the published units linked to it (catalog order)."""
    units_query = (
        select(LearningUnit)
        .join(LearningTrack, LearningTrack.id == LearningUnit.track_id)
        .where(LearningUnit.status == PUBLISHED, LearningTrack.status == PUBLISHED)
        .order_by(LearningTrack.position, LearningUnit.position)
    )
    if goal.role_id is not None:
        role = db.get(CareerRole, goal.role_id)
        available = role.status == PUBLISHED
        target = GoalTarget(kind="role", slug=role.slug, name=role.name, available=available)
        core = (
            select(CareerRoleTechnology.technology_id)
            .join(Technology, Technology.id == CareerRoleTechnology.technology_id)
            .where(
                CareerRoleTechnology.role_id == role.id,
                CareerRoleTechnology.importance == "core",
                Technology.status == PUBLISHED,
            )
        )
        linked = select(LearningUnitTechnology.unit_id).where(
            LearningUnitTechnology.technology_id.in_(core)
        )
    elif goal.technology_id is not None:
        tech = db.get(Technology, goal.technology_id)
        available = tech.status == PUBLISHED
        target = GoalTarget(kind="technology", slug=tech.slug, name=tech.name, available=available)
        linked = select(LearningUnitTechnology.unit_id).where(
            LearningUnitTechnology.technology_id == tech.id
        )
    elif goal.track_id is not None:
        track = db.get(LearningTrack, goal.track_id)
        available = track.status == PUBLISHED
        target = GoalTarget(kind="track", slug=track.slug, name=track.title, available=available)
        linked = select(LearningUnit.id).where(LearningUnit.track_id == track.id)
    else:
        return None, []
    if not available:
        return target, []
    return target, list(db.scalars(units_query.where(LearningUnit.id.in_(linked))))


def _goal_out(db: Session, goal: LearningGoal) -> GoalOut:
    target, units = _target(db, goal)
    tracks = (
        {
            t.id: t
            for t in db.scalars(
                select(LearningTrack).where(LearningTrack.id.in_({u.track_id for u in units}))
            )
        }
        if units
        else {}
    )
    progress = (
        {
            p.unit_id: p
            for p in db.scalars(
                select(UserUnitProgress).where(
                    UserUnitProgress.user_id == goal.user_id,
                    UserUnitProgress.unit_id.in_([u.id for u in units]),
                )
            )
        }
        if units
        else {}
    )

    def state(unit_id: int) -> str:
        row = progress.get(unit_id)
        if row is None:
            return "not_started"
        return "completed" if row.completed_at is not None else "in_progress"

    return GoalOut(
        id=goal.id,
        title=goal.title,
        status=goal.status,
        target_date=goal.target_date,
        achieved_at=goal.achieved_at,
        created_at=goal.created_at,
        target=target,
        units=[
            GoalUnit(
                track=TrackRef(slug=tracks[u.track_id].slug, title=tracks[u.track_id].title),
                slug=u.slug,
                position=u.position,
                title=u.title,
                state=state(u.id),
            )
            for u in units
        ],
    )


def list_goals(db: Session, user: User, status: str | None = None) -> GoalList:
    query = select(LearningGoal).where(LearningGoal.user_id == user.id)
    if status is not None:
        query = query.where(LearningGoal.status == status)
    order = case({ACTIVE: 0, ACHIEVED: 1}, value=LearningGoal.status, else_=2)
    goals = db.scalars(query.order_by(order, LearningGoal.created_at, LearningGoal.id))
    return GoalList(items=[_goal_out(db, g) for g in goals], active_limit=ACTIVE_GOAL_LIMIT)


# --- writing ------------------------------------------------------------------------------


def _active_count(db: Session, user_id: int) -> int:
    return db.scalar(
        select(func.count())
        .select_from(LearningGoal)
        .where(LearningGoal.user_id == user_id, LearningGoal.status == ACTIVE)
    )


def _resolve_target(db: Session, body: GoalCreate) -> dict:
    """Only published targets can be chosen for a new goal."""
    if body.role is not None:
        role_id = db.scalar(
            select(CareerRole.id).where(
                CareerRole.slug == body.role, CareerRole.status == PUBLISHED
            )
        )
        if role_id is None:
            raise CareerRoleNotFound()
        return {"role_id": role_id}
    if body.technology is not None:
        tech_id = db.scalar(
            select(Technology.id).where(
                Technology.slug == body.technology, Technology.status == PUBLISHED
            )
        )
        if tech_id is None:
            raise TechnologyNotFound()
        return {"technology_id": tech_id}
    if body.track is not None:
        track_id = db.scalar(
            select(LearningTrack.id).where(
                LearningTrack.slug == body.track, LearningTrack.status == PUBLISHED
            )
        )
        if track_id is None:
            raise TrackNotFound()
        return {"track_id": track_id}
    return {}


def create_goal(db: Session, user: User, body: GoalCreate) -> GoalOut:
    def create() -> GoalOut:
        with write_transaction(db):
            lock_user(db, user.id)
            target = _resolve_target(db, body)
            if _active_count(db, user.id) >= ACTIVE_GOAL_LIMIT:
                raise ActiveGoalLimitReached()
            goal = LearningGoal(
                user_id=user.id,
                title=body.title,
                status=ACTIVE,
                target_date=body.target_date,
                **target,
            )
            db.add(goal)
            db.flush()
            return _goal_out(db, goal)

    return with_retry(create)


def _own_goal(db: Session, user: User, goal_id: int) -> LearningGoal:
    goal = db.scalar(
        select(LearningGoal).where(LearningGoal.id == goal_id, LearningGoal.user_id == user.id)
    )
    if goal is None:  # also for other users' goals: never reveal that an id exists
        raise GoalNotFound()
    return goal


def update_goal(db: Session, user: User, goal_id: int, body: GoalUpdate) -> GoalOut:
    def update() -> GoalOut:
        with write_transaction(db):
            lock_user(db, user.id)
            goal = _own_goal(db, user, goal_id)
            fields = body.model_fields_set
            if "title" in fields:
                goal.title = body.title
            if "target_date" in fields:
                goal.target_date = body.target_date
            if "status" in fields and body.status != goal.status:
                if body.status == ACTIVE and _active_count(db, user.id) >= ACTIVE_GOAL_LIMIT:
                    raise ActiveGoalLimitReached()
                # Leaving "achieved" clears the time; achieving again records a new one.
                goal.achieved_at = utc_now() if body.status == ACHIEVED else None
                goal.status = body.status
            db.flush()
            return _goal_out(db, goal)

    return with_retry(update)


def delete_goal(db: Session, user: User, goal_id: int) -> None:
    def delete() -> None:
        with write_transaction(db):
            lock_user(db, user.id)
            db.delete(_own_goal(db, user, goal_id))

    with_retry(delete)
