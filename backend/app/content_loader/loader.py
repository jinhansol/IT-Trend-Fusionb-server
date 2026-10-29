"""Upsert validated track content into the catalog tables.

Idempotent: loading the same files twice changes nothing. Units and activities
missing from the files are retired (never deleted) and lose their position.
Quizzes are versioned: an attempted version is never edited; a changed quiz
becomes a new version and the old one is retired.
The caller owns the transaction.
"""

import hashlib
import json
from dataclasses import dataclass, field

from sqlalchemy import delete, exists, func, select
from sqlalchemy.orm import Session

from app.content_loader.schema import ActivityDef, ContentError, QuizDef, TrackContent, UnitDef
from app.models.content import Technology
from app.models.learning import (
    LearningActivity,
    LearningTrack,
    LearningUnit,
    LearningUnitTechnology,
)
from app.models.quiz import Quiz, QuizAttempt, QuizChoice, QuizQuestion

RETIRED = "retired"


@dataclass
class LoadReport:
    track: str
    created: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    retired: list[str] = field(default_factory=list)
    kind: str = "track"

    @property
    def changed(self) -> bool:
        return bool(self.created or self.updated or self.retired)

    def summary(self) -> str:
        lines = [
            f"{self.kind} '{self.track}': {len(self.created)} created, "
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


def _technology_ids(db: Session, content: TrackContent) -> dict[str, int]:
    """Resolve every technology slug the units reference, before anything is written.
    Technologies must be loaded first (content/technologies.yaml) and published."""
    wanted = {slug for unit in content.units for slug in unit.technologies}
    if not wanted:
        return {}
    found = dict(
        db.execute(
            select(Technology.slug, Technology.id).where(
                Technology.slug.in_(wanted), Technology.status == "published"
            )
        ).all()
    )
    problems = [
        f"unit '{unit.slug}': {', '.join(sorted(set(unit.technologies) - set(found)))}"
        for unit in content.units
        if set(unit.technologies) - set(found)
    ]
    if problems:
        raise ContentError(
            f"track '{content.track.slug}' references unknown or retired technologies "
            f"({'; '.join(problems)}). Load content/technologies.yaml first."
        )
    return found


def apply_track(db: Session, content: TrackContent) -> LoadReport:
    report = LoadReport(track=content.track.slug)
    technology_ids = _technology_ids(db, content)

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
        _apply_quiz(db, unit, unit_def.quiz, report)
        _apply_unit_technologies(db, unit, unit_def, technology_ids, report)

    db.flush()
    return report


def _apply_unit_technologies(
    db: Session,
    unit: LearningUnit,
    unit_def: UnitDef,
    technology_ids: dict[str, int],
    report: LoadReport,
) -> None:
    """Make the unit's technology links match the file exactly."""
    wanted = {technology_ids[slug] for slug in unit_def.technologies}
    current = set(
        db.scalars(
            select(LearningUnitTechnology.technology_id).where(
                LearningUnitTechnology.unit_id == unit.id
            )
        )
    )
    if wanted == current:
        return
    if current - wanted:
        db.execute(
            delete(LearningUnitTechnology).where(
                LearningUnitTechnology.unit_id == unit.id,
                LearningUnitTechnology.technology_id.in_(current - wanted),
            )
        )
    db.add_all(
        LearningUnitTechnology(unit_id=unit.id, technology_id=tech_id)
        for tech_id in sorted(wanted - current)
    )
    report.updated.append(f"unit {unit_def.slug} technologies")


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


def _quiz_hash(quiz_def: QuizDef) -> str:
    canonical = json.dumps(quiz_def.model_dump(), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


def _apply_quiz(
    db: Session, unit: LearningUnit, quiz_def: QuizDef | None, report: LoadReport
) -> None:
    current = db.scalar(
        select(Quiz).where(Quiz.unit_id == unit.id, Quiz.status == "published").with_for_update()
    )
    label = f"quiz {unit.slug}"

    if quiz_def is None:
        if current is not None:
            current.status = RETIRED
            db.flush()
            report.retired.append(f"{label} v{current.version}")
        return

    content_hash = _quiz_hash(quiz_def)
    if current is not None and current.content_hash == content_hash:
        return

    attempted = current is not None and db.scalar(
        select(exists().where(QuizAttempt.quiz_id == current.id))
    )
    if current is not None and not attempted:
        # Nobody has answered this version yet: edit it in place.
        question_ids = select(QuizQuestion.id).where(QuizQuestion.quiz_id == current.id)
        db.execute(delete(QuizChoice).where(QuizChoice.question_id.in_(question_ids)))
        db.execute(delete(QuizQuestion).where(QuizQuestion.quiz_id == current.id))
        current.pass_score_percent = quiz_def.pass_score_percent
        current.content_hash = content_hash
        _insert_questions(db, current, quiz_def)
        report.updated.append(f"{label} v{current.version}")
        return

    if current is not None:
        current.status = RETIRED  # frees the one-published-quiz-per-unit slot
        db.flush()
        report.retired.append(f"{label} v{current.version}")

    latest = db.scalar(select(func.max(Quiz.version)).where(Quiz.unit_id == unit.id)) or 0
    quiz = Quiz(
        unit_id=unit.id,
        version=latest + 1,
        status="published",
        pass_score_percent=quiz_def.pass_score_percent,
        content_hash=content_hash,
    )
    db.add(quiz)
    db.flush()
    _insert_questions(db, quiz, quiz_def)
    report.created.append(f"{label} v{quiz.version}")


def _insert_questions(db: Session, quiz: Quiz, quiz_def: QuizDef) -> None:
    for position, question_def in enumerate(quiz_def.questions, start=1):
        question = QuizQuestion(
            quiz_id=quiz.id,
            key=question_def.key,
            position=position,
            type=question_def.type,
            prompt=question_def.prompt,
            explanation=question_def.explanation,
        )
        db.add(question)
        db.flush()
        db.add_all(
            QuizChoice(
                question_id=question.id,
                key=choice.key,
                position=choice_position,
                label=choice.label,
                is_correct=choice.correct,
            )
            for choice_position, choice in enumerate(question_def.choices, start=1)
        )
    db.flush()
