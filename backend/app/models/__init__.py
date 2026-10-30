"""ORM models. Import every model module here so Alembic autogenerate sees it."""

from app.models.career import CareerRole, CareerRoleTechnology, UserCareerCandidate
from app.models.content import (
    Content,
    ContentSource,
    ContentSummary,
    ContentTechnology,
    ContentTranslation,
    JobRun,
    Technology,
    TechnologyAlias,
)
from app.models.goals import LearningGoal
from app.models.learning import (
    LearningActivity,
    LearningTrack,
    LearningUnit,
    LearningUnitTechnology,
)
from app.models.personalization import UserInterest, UserSkill
from app.models.progress import UserActivityRecord, UserUnitProgress, XpLedgerEntry
from app.models.quiz import Quiz, QuizAttempt, QuizAttemptAnswer, QuizChoice, QuizQuestion
from app.models.user import RefreshToken, User, UserSettings

__all__ = [
    "CareerRole",
    "CareerRoleTechnology",
    "Content",
    "ContentSource",
    "ContentSummary",
    "ContentTechnology",
    "ContentTranslation",
    "JobRun",
    "LearningActivity",
    "LearningGoal",
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
    "UserCareerCandidate",
    "UserInterest",
    "UserSettings",
    "UserSkill",
    "UserUnitProgress",
    "XpLedgerEntry",
]
