from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_settings
from app.core.config import Settings
from app.models.user import User
from app.schemas.progress import (
    ActivityConfirmResponse,
    MeSummary,
    QuizResult,
    QuizSubmission,
    TrackProgressOut,
    UnitProgressDetail,
)
from app.services import learning_progress

# Personal learning data. The user always comes from the access token; no user id
# is ever accepted from the path or body.
router = APIRouter(prefix="/api/me", tags=["me"])


@router.get("/summary", response_model=MeSummary)
def read_summary(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MeSummary:
    return learning_progress.summary(db, settings, user)


@router.get("/tracks/{track_slug}/progress", response_model=TrackProgressOut)
def read_track_progress(
    track_slug: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> TrackProgressOut:
    return learning_progress.track_progress(db, user, track_slug)


@router.get("/tracks/{track_slug}/units/{unit_slug}/progress", response_model=UnitProgressDetail)
def read_unit_progress(
    track_slug: str,
    unit_slug: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UnitProgressDetail:
    return learning_progress.unit_progress(db, user, track_slug, unit_slug)


@router.post("/activities/{activity_id}/confirm", response_model=ActivityConfirmResponse)
def confirm_activity(
    activity_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ActivityConfirmResponse:
    return learning_progress.confirm_activity(db, settings, user, activity_id)


@router.post("/quizzes/{quiz_id}/attempts", response_model=QuizResult)
def submit_quiz(
    quiz_id: int,
    submission: QuizSubmission,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> QuizResult:
    return learning_progress.submit_quiz(db, settings, user, quiz_id, submission)
