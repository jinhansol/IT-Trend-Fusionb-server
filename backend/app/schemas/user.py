from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, StrictBool, model_validator

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
    personalization_enabled turns personalization ON or OFF explicitly (P4); turning
    it OFF keeps the user's interests and skills. It cannot be null."""

    model_config = ConfigDict(extra="forbid")

    learner_type: LearnerType | None = None
    personalization_enabled: StrictBool | None = None

    @model_validator(mode="after")
    def _switch_not_null(self) -> "SettingsUpdate":
        if (
            "personalization_enabled" in self.model_fields_set
            and self.personalization_enabled is None
        ):
            raise ValueError("personalization_enabled must be true or false")
        return self


class MeResponse(UserPublic):
    settings: UserSettingsOut
