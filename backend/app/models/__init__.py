"""ORM models. Import every model module here so Alembic autogenerate sees it."""

from app.models.learning import LearningActivity, LearningTrack, LearningUnit
from app.models.progress import UserActivityRecord, UserUnitProgress, XpLedgerEntry
from app.models.quiz import Quiz, QuizAttempt, QuizAttemptAnswer, QuizChoice, QuizQuestion
from app.models.user import RefreshToken, User, UserSettings

__all__ = [
    "LearningActivity",
    "LearningTrack",
    "LearningUnit",
    "Quiz",
    "QuizAttempt",
    "QuizAttemptAnswer",
    "QuizChoice",
    "QuizQuestion",
    "RefreshToken",
    "User",
    "UserActivityRecord",
    "UserSettings",
    "UserUnitProgress",
    "XpLedgerEntry",
]
