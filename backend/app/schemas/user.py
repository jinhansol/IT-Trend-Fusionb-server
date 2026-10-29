from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

LearnerType = Literal["beginner", "developer", "exploring"]


class UserPublic(BaseModel):
    """What clients may see about a user. Never includes hashes or status."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    display_name: str
    role: str
    created_at: datetime


class UserSettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    personalization_enabled: bool
    learner_type: LearnerType | None = None


class SettingsUpdate(BaseModel):
    """PATCH body. Only fields that are sent are changed; null clears learner_type.
    The personalization switch is not settable yet (A-plan v0.2, P1)."""

    model_config = ConfigDict(extra="forbid")

    learner_type: LearnerType | None = None


class MeResponse(UserPublic):
    settings: UserSettingsOut
