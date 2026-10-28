"""Learner progress: activity confirmation, quiz grading, unit completion, rewards.

Completion rule (D02): every required activity confirmed AND the unit quiz passed,
in any order. Each write use case is one transaction that first locks the learner's
progress row for the unit (SELECT ... FOR UPDATE), so concurrent requests for the
same unit run one after another; the XP ledger's unique key is the last guard.

Write transactions run at READ COMMITTED: under MariaDB's default REPEATABLE READ,
plain reads made after the lock would still see the snapshot taken before it and
miss rows a concurrent transaction committed while we waited.
"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager

from sqlalchemy import exists, func, select
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings
from app.core.errors import AppError
from app.db.types import utc_now
from app.models.learning import LearningActivity, LearningTrack, LearningUnit
from app.models.progress import UserActivityRecord, UserUnitProgress
from app.models.quiz import Quiz, QuizAttempt, QuizAttemptAnswer, QuizQuestion
from app.models.user import User
from app.schemas.progress import (
    ActivityConfirmResponse,
    ContinueUnit,
    GrantedRewardOut,
    MeSummary,
    QuestionFeedback,
    QuizProgress,
    QuizResult,
    QuizSubmission,
    TrackProgressOut,
    UnitProgressDetail,
    UnitProgressOut,
    XpStatus,
)
from app.services import rewards
from app.services.learning_catalog import TrackNotFound, UnitNotFound

PUBLISHED = "published"
UNIT_COMPLETED = "unit_completed"
# MariaDB: deadlock / lock wait timeout. Safe to retry the whole transaction.
_RETRYABLE_ERRORS = (1213, 1205)
_MAX_ATTEMPTS = 3


class ActivityNotFound(AppError):
    status_code = 404
    code = "ACTIVITY_NOT_FOUND"

    def __init__(self) -> None:
        super().__init__("Activity not found")


class QuizNotFound(AppError):
    status_code = 404
    code = "QUIZ_NOT_FOUND"

    def __init__(self) -> None:
        super().__init__("Quiz not found")


class QuizRetired(AppError):
    status_code = 409
    code = "QUIZ_RETIRED"

    def __init__(self) -> None:
        super().__init__("This quiz has been updated. Reload to get the new version.")


class SubmissionIdReused(AppError):
    status_code = 409
    code = "SUBMISSION_ID_REUSED"

    def __init__(self) -> None:
        super().__init__("client_submission_id was already used for another quiz")


class InvalidAnswer(AppError):
    status_code = 422
    code = "INVALID_ANSWER"


# --- helpers ----------------------------------------------------------------------------


def _with_retry[T](operation: Callable[[], T]) -> T:
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            return operation()
        except OperationalError as exc:
            code = getattr(exc.orig, "args", (None,))[0]
            if code not in _RETRYABLE_ERRORS or attempt == _MAX_ATTEMPTS:
                raise
    raise AssertionError("unreachable")


@contextmanager
def _write_transaction(db: Session) -> Iterator[None]:
    with db.begin():
        db.connection(execution_options={"isolation_level": "READ COMMITTED"})
        yield


def _published_scope():
    return (LearningUnit.status == PUBLISHED, LearningTrack.status == PUBLISHED)


def _lock_progress(db: Session, user_id: int, unit_id: int) -> UserUnitProgress:
    now = utc_now()
    insert = mysql_insert(UserUnitProgress).values(
        user_id=user_id, unit_id=unit_id, started_at=now, last_activity_at=now
    )
    db.execute(insert.on_duplicate_key_update(user_id=insert.inserted.user_id))
    return db.scalars(
        select(UserUnitProgress)
        .where(UserUnitProgress.user_id == user_id, UserUnitProgress.unit_id == unit_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).one()


def _required_activity_ids(db: Session, unit_id: int) -> list[int]:
    return list(
        db.scalars(
            select(LearningActivity.id).where(
                LearningActivity.unit_id == unit_id,
                LearningActivity.status == PUBLISHED,
                LearningActivity.is_required.is_(True),
            )
        )
    )


def _confirmed_count(db: Session, user_id: int, activity_ids: list[int]) -> int:
    if not activity_ids:
        return 0
    return db.scalar(
        select(func.count()).where(
            UserActivityRecord.user_id == user_id,
            UserActivityRecord.activity_id.in_(activity_ids),
        )
    )


def _has_quiz(db: Session, unit_id: int) -> bool:
    return db.scalar(select(exists().where(Quiz.unit_id == unit_id, Quiz.status == PUBLISHED)))


def _evaluate(
    db: Session, settings: Settings, user_id: int, unit: LearningUnit, progress: UserUnitProgress
) -> list[rewards.GrantedReward]:
    """Apply the completion rule. completed_at is set once and never cleared."""
    now = utc_now()
    required = _required_activity_ids(db, unit.id)
    activities_ok = _confirmed_count(db, user_id, required) >= len(required)
    if activities_ok and progress.activities_completed_at is None:
        progress.activities_completed_at = now

    granted = []
    if progress.completed_at is None and activities_ok and progress.quiz_passed_at is not None:
        progress.completed_at = now
        reward = rewards.grant_once(
            db,
            settings,
            user_id=user_id,
            amount=settings.xp_per_unit_completion,
            reason=UNIT_COMPLETED,
            source_type="unit",
            source_id=unit.id,
            idempotency_key=f"{UNIT_COMPLETED}:{unit.id}",
        )
        if reward is not None:
            granted.append(reward)
    progress.last_activity_at = now
    db.flush()
    return granted


def _progress_out(
    db: Session, user_id: int, unit: LearningUnit, progress: UserUnitProgress | None
) -> UnitProgressOut:
    required = _required_activity_ids(db, unit.id)
    if progress is None:
        state = "not_started"
    elif progress.completed_at is not None:
        state = "completed"
    else:
        state = "in_progress"
    return UnitProgressOut(
        unit_slug=unit.slug,
        state=state,
        activities_done=_confirmed_count(db, user_id, required),
        activities_required=len(required),
        quiz_passed=bool(progress and progress.quiz_passed_at),
        has_quiz=_has_quiz(db, unit.id),
        completed_at=progress.completed_at if progress else None,
    )


def xp_status(db: Session, settings: Settings, user_id: int) -> XpStatus:
    info = rewards.level_info(rewards.total_xp(db, user_id), settings)
    return XpStatus(
        total=info.total_xp,
        level=info.level,
        xp_into_level=info.xp_into_level,
        xp_for_next_level=info.xp_for_next_level,
    )


def _granted_out(granted: list[rewards.GrantedReward]) -> list[GrantedRewardOut]:
    return [GrantedRewardOut(amount=g.amount, reason=g.reason) for g in granted]


# --- write use cases --------------------------------------------------------------------


def confirm_activity(
    db: Session, settings: Settings, user: User, activity_id: int
) -> ActivityConfirmResponse:
    return _with_retry(lambda: _confirm_activity(db, settings, user, activity_id))


def _confirm_activity(
    db: Session, settings: Settings, user: User, activity_id: int
) -> ActivityConfirmResponse:
    with _write_transaction(db):
        row = db.execute(
            select(LearningActivity, LearningUnit)
            .join(LearningUnit, LearningUnit.id == LearningActivity.unit_id)
            .join(LearningTrack, LearningTrack.id == LearningUnit.track_id)
            .where(LearningActivity.id == activity_id, LearningActivity.status == PUBLISHED)
            .where(*_published_scope())
        ).first()
        if row is None:
            raise ActivityNotFound()
        activity, unit = row

        progress = _lock_progress(db, user.id, unit.id)
        record = db.get(UserActivityRecord, (user.id, activity.id))
        if record is None:
            record = UserActivityRecord(
                user_id=user.id,
                activity_id=activity.id,
                confirmation_type=activity.confirmation_type,
                confirmed_at=utc_now(),
            )
            db.add(record)
            db.flush()
        granted = _evaluate(db, settings, user.id, unit, progress)
        response = ActivityConfirmResponse(
            activity_id=activity.id,
            confirmed_at=record.confirmed_at,
            progress=_progress_out(db, user.id, unit, progress),
            granted_rewards=_granted_out(granted),
            xp=xp_status(db, settings, user.id),
        )
    return response


def submit_quiz(
    db: Session, settings: Settings, user: User, quiz_id: int, submission: QuizSubmission
) -> QuizResult:
    return _with_retry(lambda: _submit_quiz(db, settings, user, quiz_id, submission))


def _load_questions(db: Session, quiz_id: int) -> list[QuizQuestion]:
    return list(
        db.scalars(
            select(QuizQuestion)
            .where(QuizQuestion.quiz_id == quiz_id)
            .options(selectinload(QuizQuestion.choices))
            .order_by(QuizQuestion.position)
        )
    )


def _validated_choices(
    questions: list[QuizQuestion], submission: QuizSubmission
) -> dict[int, set[int]]:
    by_id = {q.id: q for q in questions}
    chosen: dict[int, set[int]] = {}
    for answer in submission.answers:
        question = by_id.get(answer.question_id)
        if question is None:
            raise InvalidAnswer(f"Question {answer.question_id} is not part of this quiz")
        if question.id in chosen:
            raise InvalidAnswer(f"Question {question.id} was answered twice")
        picked = set(answer.choice_ids)
        if len(picked) != len(answer.choice_ids):
            raise InvalidAnswer(f"Question {question.id} has a repeated choice")
        if not picked <= {c.id for c in question.choices}:
            raise InvalidAnswer(f"Question {question.id} has a choice from another question")
        if question.type == "single" and len(picked) != 1:
            raise InvalidAnswer(f"Question {question.id} takes exactly one choice")
        if question.type == "multiple" and not picked:
            raise InvalidAnswer(f"Question {question.id} needs at least one choice")
        chosen[question.id] = picked
    return chosen


def _correct_ids(question: QuizQuestion) -> set[int]:
    return {c.id for c in question.choices if c.is_correct}


def _submit_quiz(
    db: Session, settings: Settings, user: User, quiz_id: int, submission: QuizSubmission
) -> QuizResult:
    with _write_transaction(db):
        row = db.execute(
            select(Quiz, LearningUnit)
            .join(LearningUnit, LearningUnit.id == Quiz.unit_id)
            .join(LearningTrack, LearningTrack.id == LearningUnit.track_id)
            .where(Quiz.id == quiz_id)
            .where(*_published_scope())
        ).first()
        if row is None:
            raise QuizNotFound()
        quiz, unit = row

        progress = _lock_progress(db, user.id, unit.id)
        attempt = db.scalar(
            select(QuizAttempt).where(
                QuizAttempt.user_id == user.id,
                QuizAttempt.client_submission_id == submission.client_submission_id,
            )
        )
        granted: list[rewards.GrantedReward] = []
        if attempt is not None:
            # A retry of a submission we already graded: return the same result.
            if attempt.quiz_id != quiz.id:
                raise SubmissionIdReused()
            questions = _load_questions(db, quiz.id)
            chosen = _stored_choices(db, attempt.id)
        else:
            if quiz.status != PUBLISHED:
                raise QuizRetired()
            questions = _load_questions(db, quiz.id)
            chosen = _validated_choices(questions, submission)
            score = sum(1 for q in questions if chosen.get(q.id) == _correct_ids(q))
            max_score = len(questions)
            percent = score * 100 // max_score
            attempt = QuizAttempt(
                user_id=user.id,
                quiz_id=quiz.id,
                client_submission_id=submission.client_submission_id,
                score=score,
                max_score=max_score,
                score_percent=percent,
                passed=percent >= quiz.pass_score_percent,
                submitted_at=utc_now(),
            )
            db.add(attempt)
            db.flush()
            db.add_all(
                QuizAttemptAnswer(attempt_id=attempt.id, question_id=qid, choice_id=cid)
                for qid, picked in chosen.items()
                for cid in picked
            )
            if attempt.passed and progress.quiz_passed_at is None:
                progress.quiz_passed_at = utc_now()
                progress.passed_attempt_id = attempt.id
            granted = _evaluate(db, settings, user.id, unit, progress)

        revealed = progress.quiz_passed_at is not None
        result = QuizResult(
            attempt_id=attempt.id,
            score=attempt.score,
            max_score=attempt.max_score,
            score_percent=attempt.score_percent,
            passed=attempt.passed,
            pass_score_percent=quiz.pass_score_percent,
            answers_revealed=revealed,
            feedback=[
                QuestionFeedback(
                    question_id=q.id,
                    correct=chosen.get(q.id) == _correct_ids(q),
                    correct_choice_ids=sorted(_correct_ids(q)) if revealed else None,
                    explanation=q.explanation if revealed else None,
                )
                for q in questions
            ],
            progress=_progress_out(db, user.id, unit, progress),
            granted_rewards=_granted_out(granted),
            xp=xp_status(db, settings, user.id),
        )
    return result


def _stored_choices(db: Session, attempt_id: int) -> dict[int, set[int]]:
    chosen: dict[int, set[int]] = {}
    for answer in db.scalars(
        select(QuizAttemptAnswer).where(QuizAttemptAnswer.attempt_id == attempt_id)
    ):
        chosen.setdefault(answer.question_id, set()).add(answer.choice_id)
    return chosen


# --- read models ------------------------------------------------------------------------


def _published_track(db: Session, track_slug: str) -> LearningTrack:
    track = db.scalar(
        select(LearningTrack).where(
            LearningTrack.slug == track_slug, LearningTrack.status == PUBLISHED
        )
    )
    if track is None:
        raise TrackNotFound()
    return track


def _published_units(db: Session, track_id: int) -> list[LearningUnit]:
    return list(
        db.scalars(
            select(LearningUnit)
            .where(LearningUnit.track_id == track_id, LearningUnit.status == PUBLISHED)
            .order_by(LearningUnit.position)
        )
    )


def _progress_rows(db: Session, user_id: int, unit_ids: list[int]) -> dict[int, UserUnitProgress]:
    if not unit_ids:
        return {}
    return {
        p.unit_id: p
        for p in db.scalars(
            select(UserUnitProgress).where(
                UserUnitProgress.user_id == user_id, UserUnitProgress.unit_id.in_(unit_ids)
            )
        )
    }


def track_progress(db: Session, user: User, track_slug: str) -> TrackProgressOut:
    track = _published_track(db, track_slug)
    units = _published_units(db, track.id)
    rows = _progress_rows(db, user.id, [u.id for u in units])
    outs = [_progress_out(db, user.id, u, rows.get(u.id)) for u in units]
    return TrackProgressOut(
        track_slug=track.slug,
        completed_units=sum(o.state == "completed" for o in outs),
        total_units=len(outs),
        units=outs,
    )


def unit_progress(db: Session, user: User, track_slug: str, unit_slug: str) -> UnitProgressDetail:
    track = _published_track(db, track_slug)
    unit = next((u for u in _published_units(db, track.id) if u.slug == unit_slug), None)
    if unit is None:
        raise UnitNotFound()
    progress = _progress_rows(db, user.id, [unit.id]).get(unit.id)
    confirmed = list(
        db.scalars(
            select(UserActivityRecord.activity_id)
            .join(LearningActivity, LearningActivity.id == UserActivityRecord.activity_id)
            .where(UserActivityRecord.user_id == user.id, LearningActivity.unit_id == unit.id)
        )
    )
    attempts, best = db.execute(
        select(func.count(QuizAttempt.id), func.max(QuizAttempt.score_percent))
        .join(Quiz, Quiz.id == QuizAttempt.quiz_id)
        .where(QuizAttempt.user_id == user.id, Quiz.unit_id == unit.id)
    ).one()
    return UnitProgressDetail(
        progress=_progress_out(db, user.id, unit, progress),
        confirmed_activity_ids=sorted(confirmed),
        quiz=QuizProgress(
            passed=bool(progress and progress.quiz_passed_at),
            attempts=attempts,
            best_score_percent=best,
        ),
    )


def summary(db: Session, settings: Settings, user: User) -> MeSummary:
    visible = (
        select(UserUnitProgress, LearningUnit, LearningTrack)
        .join(LearningUnit, LearningUnit.id == UserUnitProgress.unit_id)
        .join(LearningTrack, LearningTrack.id == LearningUnit.track_id)
        .where(UserUnitProgress.user_id == user.id)
        .where(*_published_scope())
    )
    rows = db.execute(visible.order_by(UserUnitProgress.last_activity_at.desc())).all()
    completed = [r for r in rows if r[0].completed_at is not None]
    in_progress = [r for r in rows if r[0].completed_at is None]

    continue_unit = None
    if in_progress:
        progress, unit, track = in_progress[0]
        out = _progress_out(db, user.id, unit, progress)
        continue_unit = ContinueUnit(
            track_slug=track.slug,
            track_title=track.title,
            unit_slug=unit.slug,
            unit_title=unit.title,
            activities_done=out.activities_done,
            activities_required=out.activities_required,
            quiz_passed=out.quiz_passed,
        )
    return MeSummary(
        xp=xp_status(db, settings, user.id),
        completed_units=len(completed),
        in_progress_units=len(in_progress),
        passed_quizzes=sum(1 for r in rows if r[0].quiz_passed_at is not None),
        continue_unit=continue_unit,
    )
