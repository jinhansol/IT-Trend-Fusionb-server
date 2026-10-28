from datetime import datetime

from pydantic import BaseModel, ConfigDict


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


class MeResponse(UserPublic):
    settings: UserSettingsOut
