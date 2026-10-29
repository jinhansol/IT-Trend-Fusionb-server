from pydantic import BaseModel

from app.schemas.content import TechnologyRef


class TrackSummary(BaseModel):
    slug: str
    title: str
    description: str | None
    unit_count: int


class TrackListResponse(BaseModel):
    items: list[TrackSummary]


class UnitSummary(BaseModel):
    slug: str
    position: int
    title: str
    summary: str | None
    estimated_minutes: int | None
    activity_count: int


class TrackDetail(BaseModel):
    slug: str
    title: str
    description: str | None
    units: list[UnitSummary]


class TrackRef(BaseModel):
    slug: str
    title: str


class UnitRef(BaseModel):
    slug: str
    title: str


class ActivityOut(BaseModel):
    id: int
    slug: str
    position: int
    kind: str
    title: str
    url: str | None
    body_md: str | None
    is_required: bool


class UnitQuizSummary(BaseModel):
    id: int
    question_count: int
    pass_score_percent: int


class UnitDetail(BaseModel):
    slug: str
    position: int
    title: str
    summary: str | None
    estimated_minutes: int | None
    track: TrackRef
    activities: list[ActivityOut]
    prev: UnitRef | None
    next: UnitRef | None
    # None when the unit has no quiz yet (it can be studied but not completed).
    quiz: UnitQuizSummary | None = None
    # Technologies the unit teaches, as written in its content file (P2).
    technologies: list[TechnologyRef] = []


class TechnologyUnit(BaseModel):
    track: TrackRef
    slug: str
    position: int
    title: str
    summary: str | None
    estimated_minutes: int | None


class TechnologyUnits(BaseModel):
    """Published units that teach a technology: a technology-level link, not a
    statement that a specific article or post is about the unit's topic."""

    technology: TechnologyRef
    units: list[TechnologyUnit]


class TechnologyItem(BaseModel):
    slug: str
    name: str
    kind: str


class TechnologyList(BaseModel):
    """Every published technology, for pickers (group by kind, search by name)."""

    items: list[TechnologyItem]
