from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, PlainSerializer

# Stored as naive UTC; sent with an explicit "Z" so browsers show local time correctly.
UtcTime = Annotated[
    datetime,
    PlainSerializer(
        lambda value: value.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z"),
        return_type=str,
    ),
]


class TechnologyRef(BaseModel):
    slug: str
    name: str


class SourceRef(BaseModel):
    slug: str
    name: str


class TranslationRef(BaseModel):
    """Korean AI translation of title and excerpt (News only). The originals stay in
    title/excerpt; the card falls back to them when this is null."""

    language: str = "ko"
    title: str
    excerpt: str | None


class ContentItem(BaseModel):
    id: int
    title: str
    url: str
    excerpt: str | None
    author: str | None
    source: SourceRef
    published_at: UtcTime | None
    collected_at: UtcTime
    # None: the source does not provide the metric. For Q&A sources comment_count is
    # the number of answers.
    score: int | None
    comment_count: int | None
    view_count: int | None
    technologies: list[TechnologyRef]
    translation: TranslationRef | None = None


class ContentPage(BaseModel):
    items: list[ContentItem]
    page: int
    size: int
    total: int


class ChannelSource(BaseModel):
    slug: str
    name: str


class DevChannel(BaseModel):
    slug: str
    name: str
    kind: Literal["news", "blog", "community", "qna"]
    # Feed-only channels have no score, so they cannot be sorted by popularity.
    has_metrics: bool
    sources: list[ChannelSource]


class DevChannelList(BaseModel):
    items: list[DevChannel]


class CountItem(BaseModel):
    slug: str
    name: str
    count: int


class DailyCount(BaseModel):
    date: str  # YYYY-MM-DD (UTC)
    total: int
    counts: dict[str, int]  # top technologies only


class TrendReport(BaseModel):
    scope: Literal["news", "dev"]
    days: int
    total: int
    fields: list[CountItem]
    technologies: list[CountItem]
    daily: list[DailyCount]
    daily_technologies: list[TechnologyRef]


class SourceStatus(BaseModel):
    slug: str
    name: str
    channel: str | None
    last_success_at: UtcTime | None
    last_run_status: str | None
    stale: bool


class FeedStatus(BaseModel):
    scope: Literal["news", "dev"]
    last_updated_at: UtcTime | None
    stale: bool
    sources: list[SourceStatus]
