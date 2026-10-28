from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

UnitState = Literal["not_started", "in_progress", "completed"]


class XpStatus(BaseModel):
    total: int
    level: int
    xp_into_level: int
    xp_for_next_level: int


class GrantedRewardOut(BaseModel):
    amount: int
    reason: str


class UnitProgressOut(BaseModel):
    unit_slug: str
    state: UnitState
    activities_done: int
    activities_required: int
    quiz_passed: bool
    has_quiz: bool
    completed_at: datetime | None


class ContinueUnit(BaseModel):
    track_slug: str
    track_title: str
    unit_slug: str
    unit_title: str
    activities_done: int
    activities_required: int
    quiz_passed: bool


class MeSummary(BaseModel):
    xp: XpStatus
    completed_units: int
    in_progress_units: int
    passed_quizzes: int
    continue_unit: ContinueUnit | None


class TrackProgressOut(BaseModel):
    track_slug: str
    completed_units: int
    total_units: int
    units: list[UnitProgressOut]


class QuizProgress(BaseModel):
    passed: bool
    attempts: int
    best_score_percent: int | None


class UnitProgressDetail(BaseModel):
    progress: UnitProgressOut
    confirmed_activity_ids: list[int]
    quiz: QuizProgress


class ActivityConfirmResponse(BaseModel):
    activity_id: int
    confirmed_at: datetime
    progress: UnitProgressOut
    granted_rewards: list[GrantedRewardOut]
    xp: XpStatus


# --- quiz -------------------------------------------------------------------------------


class QuizChoiceOut(BaseModel):
    id: int
    label: str


class QuizQuestionOut(BaseModel):
    id: int
    position: int
    type: Literal["single", "multiple"]
    prompt: str
    choices: list[QuizChoiceOut]


class QuizOut(BaseModel):
    """Public quiz. Never contains correct answers or explanations."""

    id: int
    version: int
    pass_score_percent: int
    questions: list[QuizQuestionOut]


class AnswerIn(BaseModel):
    question_id: int
    choice_ids: list[int] = Field(max_length=8)


class QuizSubmission(BaseModel):
    client_submission_id: str = Field(
        pattern=r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
    )
    answers: list[AnswerIn] = Field(max_length=30)


class QuestionFeedback(BaseModel):
    question_id: int
    correct: bool
    # Revealed only once the learner has passed this unit's quiz.
    correct_choice_ids: list[int] | None = None
    explanation: str | None = None


class QuizResult(BaseModel):
    attempt_id: int
    score: int
    max_score: int
    score_percent: int
    passed: bool
    pass_score_percent: int
    answers_revealed: bool
    feedback: list[QuestionFeedback]
    progress: UnitProgressOut
    granted_rewards: list[GrantedRewardOut]
    xp: XpStatus
