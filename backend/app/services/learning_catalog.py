"""Read-only queries over the learning catalog. Only published rows are visible."""

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.learning import LearningActivity, LearningTrack, LearningUnit
from app.schemas.learning import (
    ActivityOut,
    TrackDetail,
    TrackListResponse,
    TrackRef,
    TrackSummary,
    UnitDetail,
    UnitRef,
    UnitSummary,
)

PUBLISHED = "published"


class TrackNotFound(AppError):
    status_code = 404
    code = "TRACK_NOT_FOUND"

    def __init__(self) -> None:
        super().__init__("Track not found")


class UnitNotFound(AppError):
    status_code = 404
    code = "UNIT_NOT_FOUND"

    def __init__(self) -> None:
        super().__init__("Unit not found")


def list_tracks(db: Session) -> TrackListResponse:
    unit_count = func.count(LearningUnit.id)
    rows = db.execute(
        select(LearningTrack, unit_count)
        .outerjoin(
            LearningUnit,
            and_(LearningUnit.track_id == LearningTrack.id, LearningUnit.status == PUBLISHED),
        )
        .where(LearningTrack.status == PUBLISHED)
        .group_by(LearningTrack.id)
        .order_by(LearningTrack.position, LearningTrack.slug)
    ).all()
    return TrackListResponse(
        items=[
            TrackSummary(
                slug=track.slug, title=track.title, description=track.description, unit_count=count
            )
            for track, count in rows
        ]
    )


def _published_track(db: Session, track_slug: str) -> LearningTrack:
    track = db.scalar(
        select(LearningTrack).where(
            LearningTrack.slug == track_slug, LearningTrack.status == PUBLISHED
        )
    )
    if track is None:
        raise TrackNotFound()
    return track


def _published_units(db: Session, track: LearningTrack) -> list[LearningUnit]:
    return list(
        db.scalars(
            select(LearningUnit)
            .where(LearningUnit.track_id == track.id, LearningUnit.status == PUBLISHED)
            .order_by(LearningUnit.position)
        )
    )


def get_track(db: Session, track_slug: str) -> TrackDetail:
    track = _published_track(db, track_slug)
    units = _published_units(db, track)
    activity_counts = dict(
        db.execute(
            select(LearningActivity.unit_id, func.count(LearningActivity.id))
            .where(
                LearningActivity.unit_id.in_([u.id for u in units] or [0]),
                LearningActivity.status == PUBLISHED,
            )
            .group_by(LearningActivity.unit_id)
        ).all()
    )
    return TrackDetail(
        slug=track.slug,
        title=track.title,
        description=track.description,
        units=[
            UnitSummary(
                slug=u.slug,
                position=u.position,
                title=u.title,
                summary=u.summary,
                estimated_minutes=u.estimated_minutes,
                activity_count=activity_counts.get(u.id, 0),
            )
            for u in units
        ],
    )


def get_unit(db: Session, track_slug: str, unit_slug: str) -> UnitDetail:
    track = _published_track(db, track_slug)
    units = _published_units(db, track)
    index = next((i for i, u in enumerate(units) if u.slug == unit_slug), None)
    if index is None:
        raise UnitNotFound()
    unit = units[index]

    activities = db.scalars(
        select(LearningActivity)
        .where(LearningActivity.unit_id == unit.id, LearningActivity.status == PUBLISHED)
        .order_by(LearningActivity.position)
    )

    def ref(position: int) -> UnitRef | None:
        if 0 <= position < len(units):
            return UnitRef(slug=units[position].slug, title=units[position].title)
        return None

    return UnitDetail(
        slug=unit.slug,
        position=unit.position,
        title=unit.title,
        summary=unit.summary,
        estimated_minutes=unit.estimated_minutes,
        track=TrackRef(slug=track.slug, title=track.title),
        activities=[
            ActivityOut(
                id=a.id,
                slug=a.slug,
                position=a.position,
                kind=a.kind,
                title=a.title,
                url=a.url,
                body_md=a.body_md,
                is_required=a.is_required,
            )
            for a in activities
        ],
        prev=ref(index - 1),
        next=ref(index + 1),
    )
