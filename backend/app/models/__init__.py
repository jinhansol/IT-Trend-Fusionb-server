"""ORM models. Import every model module here so Alembic autogenerate sees it."""

from app.models.content import (
    Content,
    ContentSource,
    ContentTechnology,
    JobRun,
    Technology,
    TechnologyAlias,
)
from app.models.learning import (
    LearningActivity,
    LearningTrack,
    LearningUnit,
    LearningUnitTechnology,
)
from app.models.progress import UserActivityRecord, UserUnitProgress, XpLedgerEntry
from app.models.quiz import Quiz, QuizAttempt, QuizAttemptAnswer, QuizChoice, QuizQuestion
from app.models.user import RefreshToken, User, UserSettings

__all__ = [
    "Content",
    "ContentSource",
    "ContentTechnology",
    "JobRun",
    "LearningActivity",
    "LearningTrack",
    "LearningUnit",
    "LearningUnitTechnology",
    "Quiz",
    "QuizAttempt",
    "QuizAttemptAnswer",
    "QuizChoice",
    "QuizQuestion",
    "RefreshToken",
    "Technology",
    "TechnologyAlias",
    "User",
    "UserActivityRecord",
    "UserSettings",
    "UserUnitProgress",
    "XpLedgerEntry",
]
