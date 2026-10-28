from pydantic import BaseModel


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
