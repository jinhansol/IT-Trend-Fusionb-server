from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.content import TechnologyRef, UtcTime
from app.schemas.learning import TechnologyUnit

# --- public role catalog -----------------------------------------------------------------


class RoleReference(BaseModel):
    title: str
    url: str


class RoleTechnology(BaseModel):
    slug: str
    name: str
    importance: Literal["core", "related"]
    # Published Career units for this technology (technology-level link, P2).
    units: list[TechnologyUnit]


class CareerRoleSummary(BaseModel):
    slug: str
    name: str
    summary: str
    core_technologies: list[TechnologyRef]
    technology_count: int


class CareerRoleList(BaseModel):
    """Every published role in its fixed file order: the same list for every visitor."""

    items: list[CareerRoleSummary]


class CareerRoleDetail(BaseModel):
    slug: str
    name: str
    summary: str
    description_md: str
    tasks: list[str]
    references: list[RoleReference]
    technologies: list[RoleTechnology]


class RoleRef(BaseModel):
    slug: str
    name: str
    # False once the role is retired: the saved record is kept but the role page is gone.
    available: bool


# --- saved candidates (the user's own records) -------------------------------------------


class CandidateSave(BaseModel):
    note: str | None = Field(default=None, max_length=200)

    @field_validator("note")
    @classmethod
    def _blank_is_none(cls, value: str | None) -> str | None:
        return (value or "").strip() or None


class CandidateOut(BaseModel):
    role: RoleRef
    note: str | None
    saved_at: UtcTime


class CandidateList(BaseModel):
    items: list[CandidateOut]
    limit: int
