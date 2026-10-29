from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, model_validator

from app.schemas.content import UtcTime
from app.schemas.learning import TrackRef

GoalStatus = Literal["active", "achieved", "archived"]
SlugRef = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=64)]
GoalTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class GoalCreate(BaseModel):
    """A goal the user writes. At most one target (role, technology or track); none
    makes a free-form goal."""

    title: GoalTitle
    role: SlugRef | None = None
    technology: SlugRef | None = None
    track: SlugRef | None = None
    target_date: date | None = None

    @model_validator(mode="after")
    def _one_target(self) -> "GoalCreate":
        if sum(v is not None for v in (self.role, self.technology, self.track)) > 1:
            raise ValueError("choose at most one of role, technology and track")
        return self


class GoalUpdate(BaseModel):
    """Only the fields sent are changed. target_date null clears it."""

    title: GoalTitle | None = None
    target_date: date | None = None
    status: GoalStatus | None = None

    @model_validator(mode="after")
    def _no_null_title_or_status(self) -> "GoalUpdate":
        for name in ("title", "status"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


class GoalTarget(BaseModel):
    kind: Literal["role", "technology", "track"]
    slug: str
    name: str
    # False once the target is retired: the goal is kept, its learning links are not shown.
    available: bool


class GoalUnit(BaseModel):
    """A published unit linked to the goal's target, with the user's own progress.
    A fixed list for the chosen target (catalog order), not a recommendation."""

    track: TrackRef
    slug: str
    position: int
    title: str
    state: Literal["not_started", "in_progress", "completed"]


class GoalOut(BaseModel):
    id: int
    title: str
    status: GoalStatus
    target_date: date | None
    achieved_at: UtcTime | None
    created_at: UtcTime
    target: GoalTarget | None
    units: list[GoalUnit]


class GoalList(BaseModel):
    items: list[GoalOut]
    active_limit: int = Field(description="Maximum number of active goals")
