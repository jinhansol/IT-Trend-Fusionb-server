"""Upsert validated track content into the catalog tables.

Idempotent: loading the same files twice changes nothing. Units and activities
missing from the files are retired (never deleted) and lose their position.
The caller owns the transaction.
"""

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content_loader.schema import ActivityDef, TrackContent, UnitDef
from app.models.learning import LearningActivity, LearningTrack, LearningUnit

RETIRED = "retired"


@dataclass
class LoadReport:
    track: str
    created: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    retired: list[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.created or self.updated or self.retired)

    def summary(self) -> str:
        lines = [
            f"track '{self.track}': {len(self.created)} created, "
            f"{len(self.updated)} updated, {len(self.retired)} retired"
        ]
        for label, names in (("+", self.created), ("~", self.updated), ("-", self.retired)):
            lines.extend(f"  {label} {name}" for name in names)
        return "\n".join(lines)


def _assign(row, values: dict) -> bool:
    """Set attributes; return True if anything changed."""
    changed = False
    for name, value in values.items():
        if getattr(row, name) != value:
            setattr(row, name, value)
            changed = True
    return changed


def _track_values(content: TrackContent) -> dict:
    track = content.track
    return {
        "title": track.title,
        "description": track.description,
        "position": track.position,
        "status": track.status,
    }


def _unit_values(unit: UnitDef) -> dict:
    return {
        "position": unit.position,
        "title": unit.title,
        "summary": unit.summary,
        "estimated_minutes": unit.estimated_minutes,
        "status": unit.status,
    }


def _activity_values(activity: ActivityDef, position: int) -> dict:
    return {
        "position": position,
        "kind": activity.kind,
        "title": activity.title,
        "url": activity.url,
        "body_md": activity.body_md,
        "is_required": activity.required,
        "status": activity.status,
    }


def _park_moving_rows(db: Session, rows: dict, targets: dict) -> None:
    """Give rows whose position will change a unique temporary position, so the new
    order can be applied without tripping the (parent, position) unique constraint.
    Rows that keep their position are not touched (no UPDATE, updated_at unchanged)."""
    for slug, row in rows.items():
        if row.position is not None and targets.get(slug) != row.position:
            row.position = -row.id
    db.flush()


def apply_track(db: Session, content: TrackContent) -> LoadReport:
    report = LoadReport(track=content.track.slug)

    track = db.scalar(select(LearningTrack).where(LearningTrack.slug == content.track.slug))
    if track is None:
        track = LearningTrack(slug=content.track.slug, **_track_values(content))
        db.add(track)
        db.flush()
        report.created.append(f"track {track.slug}")
    elif _assign(track, _track_values(content)):
        report.updated.append(f"track {track.slug}")

    existing_units = {
        u.slug: u for u in db.scalars(select(LearningUnit).where(LearningUnit.track_id == track.id))
    }
    unit_snapshot = {slug: _unit_snapshot(u) for slug, u in existing_units.items()}
    _park_moving_rows(db, existing_units, {u.slug: u.position for u in content.units})

    wanted = {u.slug for u in content.units}
    for slug, unit in existing_units.items():
        if slug not in wanted and unit.status != RETIRED:
            unit.status, unit.position = RETIRED, None
            report.retired.append(f"unit {slug}")

    for unit_def in content.units:
        unit = existing_units.get(unit_def.slug)
        values = _unit_values(unit_def)
        if unit is None:
            unit = LearningUnit(track_id=track.id, slug=unit_def.slug, **values)
            db.add(unit)
            db.flush()
            report.created.append(f"unit {unit_def.slug}")
        else:
            _assign(unit, values)
            # Compare with the state before positions were parked.
            if unit_snapshot[unit_def.slug] != _unit_snapshot(unit):
                report.updated.append(f"unit {unit_def.slug}")
        _apply_activities(db, unit, unit_def, report)

    db.flush()
    return report


def _apply_activities(
    db: Session, unit: LearningUnit, unit_def: UnitDef, report: LoadReport
) -> None:
    existing = {
        a.slug: a
        for a in db.scalars(select(LearningActivity).where(LearningActivity.unit_id == unit.id))
    }
    snapshot = {slug: _activity_snapshot(a) for slug, a in existing.items()}
    _park_moving_rows(db, existing, {a.slug: i for i, a in enumerate(unit_def.activities, start=1)})

    wanted = {a.slug for a in unit_def.activities}
    for slug, activity in existing.items():
        if slug not in wanted and activity.status != RETIRED:
            activity.status, activity.position = RETIRED, None
            report.retired.append(f"activity {unit_def.slug}/{slug}")

    for position, activity_def in enumerate(unit_def.activities, start=1):
        values = _activity_values(activity_def, position)
        activity = existing.get(activity_def.slug)
        if activity is None:
            db.add(LearningActivity(unit_id=unit.id, slug=activity_def.slug, **values))
            report.created.append(f"activity {unit_def.slug}/{activity_def.slug}")
            continue
        _assign(activity, values)
        if snapshot[activity_def.slug] != _activity_snapshot(activity):
            report.updated.append(f"activity {unit_def.slug}/{activity_def.slug}")
    db.flush()


def _activity_snapshot(activity: LearningActivity) -> tuple:
    return (
        activity.position,
        activity.kind,
        activity.title,
        activity.url,
        activity.body_md,
        activity.is_required,
        activity.status,
    )


def _unit_snapshot(unit: LearningUnit) -> tuple:
    return (unit.position, unit.title, unit.summary, unit.estimated_minutes, unit.status)
