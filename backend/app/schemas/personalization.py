from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

SkillLevel = Literal["learning", "used", "confident"]
TechSlug = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=64)]

INTEREST_LIMIT = 20
SKILL_LIMIT = 30


def _unique(values: list[str], label: str) -> None:
    duplicates = sorted({v for v in values if values.count(v) > 1})
    if duplicates:
        raise ValueError(f"duplicate {label}: {', '.join(duplicates)}")


class InterestsUpdate(BaseModel):
    """Full replacement of the user's interests (idempotent)."""

    model_config = ConfigDict(extra="forbid")

    technologies: list[TechSlug] = Field(max_length=INTEREST_LIMIT)

    @model_validator(mode="after")
    def _no_duplicates(self) -> "InterestsUpdate":
        _unique(self.technologies, "technology")
        return self


class SkillIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    technology: TechSlug
    level: SkillLevel


class SkillsUpdate(BaseModel):
    """Full replacement of the user's self-rated skills (idempotent)."""

    model_config = ConfigDict(extra="forbid")

    skills: list[SkillIn] = Field(max_length=SKILL_LIMIT)

    @model_validator(mode="after")
    def _no_duplicates(self) -> "SkillsUpdate":
        _unique([s.technology for s in self.skills], "technology")
        return self


class InterestOut(BaseModel):
    slug: str
    name: str
    kind: str
    # False once the technology is retired: kept until the user removes it, never
    # used for recommendations, and it cannot be newly selected.
    available: bool


class SkillOut(InterestOut):
    # The user's own rating, not a verified proficiency.
    level: SkillLevel


class Limits(BaseModel):
    interests: int = INTEREST_LIMIT
    skills: int = SKILL_LIMIT


class PersonalizationOut(BaseModel):
    enabled: bool
    # off: switch OFF (data kept, never used) · empty: ON without usable data ·
    # ready: ON with data a future recommendation feature (P5) may use.
    profile_status: Literal["off", "empty", "ready"]
    interests: list[InterestOut]
    skills: list[SkillOut]
    limits: Limits = Limits()
