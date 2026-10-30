"""Technology taxonomy and collector sources, managed as files.

    content/technologies.yaml   technologies and the words that identify them
    content/sources.yaml        where the collector reads news, posts and questions

Same rules as learning content: validated completely first, idempotent upsert by
slug, and rows missing from the file are retired instead of deleted.
"""

from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import Field, StringConstraints, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content_loader.loader import LoadReport, _assign
from app.content_loader.schema import (
    ContentError,
    Slug,
    _read_yaml,
    _require_unique,
    _Strict,
    _validate,
)
from app.models.content import ContentSource, Technology, TechnologyAlias

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Alias = Annotated[
    str, StringConstraints(strip_whitespace=True, to_lower=True, min_length=1, max_length=100)
]


def _http_url(value: str | None) -> str | None:
    if value is None:
        return None
    parts = urlsplit(value)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise ValueError("must be an absolute http(s) URL")
    return value


# --- technologies -------------------------------------------------------------------------


class TechnologyDef(_Strict):
    slug: Slug
    name: Name
    kind: Literal["language", "framework", "library", "tool", "platform", "field"]
    # Matched in titles, descriptions and source tags (whole words only).
    aliases: list[Alias] = Field(default_factory=list)
    # Matched only against a source's own tags: words like "go" that are too common
    # in ordinary text.
    tag_aliases: list[Alias] = Field(default_factory=list)


class TechnologiesFile(_Strict):
    technologies: list[TechnologyDef] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique(self) -> "TechnologiesFile":
        _require_unique([t.slug for t in self.technologies], "technology slug")
        _require_unique(
            [a for t in self.technologies for a in (*t.aliases, *t.tag_aliases)], "alias"
        )
        return self


def read_technologies(path: Path) -> TechnologiesFile:
    return _validate(TechnologiesFile, _read_yaml(path), path)


def apply_technologies(db: Session, content: TechnologiesFile) -> LoadReport:
    report = LoadReport(track="technologies", kind="file")
    existing = {t.slug: t for t in db.scalars(select(Technology))}
    wanted: dict[str, tuple[Technology, bool]] = {}

    for tech_def in content.technologies:
        values = {"name": tech_def.name, "kind": tech_def.kind, "status": "published"}
        tech = existing.get(tech_def.slug)
        if tech is None:
            tech = Technology(slug=tech_def.slug, **values)
            db.add(tech)
            report.created.append(tech_def.slug)
        elif _assign(tech, values):
            report.updated.append(tech_def.slug)
        wanted.update({a: (tech, False) for a in tech_def.aliases})
        wanted.update({a: (tech, True) for a in tech_def.tag_aliases})

    listed = {t.slug for t in content.technologies}
    for slug, tech in existing.items():
        if slug not in listed and tech.status != "retired":
            tech.status = "retired"
            report.retired.append(slug)
    db.flush()

    # Aliases are keyed by the alias text, so one can move to another technology.
    current = {a.alias: a for a in db.scalars(select(TechnologyAlias))}
    for alias, row in current.items():
        if alias not in wanted:
            db.delete(row)
            report.updated.append(f"alias '{alias}' removed")
    for alias, (tech, tag_only) in wanted.items():
        row = current.get(alias)
        if row is None:
            db.add(TechnologyAlias(alias=alias, technology_id=tech.id, tag_only=tag_only))
            if tech.slug not in report.created:
                report.updated.append(f"alias '{alias}' added")
        elif _assign(row, {"technology_id": tech.id, "tag_only": tag_only}):
            report.updated.append(f"alias '{alias}' changed")
    db.flush()
    return report


# --- sources ------------------------------------------------------------------------------


class DevtoOptions(_Strict):
    tag: Slug | None = None
    # Dev.to "top" articles of the last N days; omitted means the latest articles.
    top_days: int | None = Field(default=None, ge=1, le=30)


class HackerNewsOptions(_Strict):
    # Algolia tags: front_page, story, ask_hn, show_hn.
    tags: Literal["front_page", "story", "ask_hn", "show_hn"] = "front_page"


class StackOverflowOptions(_Strict):
    site: Literal["stackoverflow"] = "stackoverflow"
    sort: Literal["hot", "activity", "votes", "week"] = "hot"
    tagged: Annotated[str, StringConstraints(max_length=100)] | None = None


_OPTIONS = {
    "rss": None,
    "devto": DevtoOptions,
    "hackernews": HackerNewsOptions,
    "stackoverflow": StackOverflowOptions,
}


class SourceDef(_Strict):
    slug: Slug
    name: Name
    kind: Literal["news", "blog", "community", "qna"]
    adapter: Literal["rss", "devto", "hackernews", "stackoverflow"]
    site_url: str = Field(max_length=2048)
    feed_url: str | None = Field(default=None, max_length=2048)
    language: Literal["ko", "en"]
    options: dict = Field(default_factory=dict)
    max_items: int = Field(default=30, ge=1, le=100)
    # Dev screen tab. Required for everything except news.
    channel: Slug | None = None
    channel_name: Name | None = None
    status: Literal["active", "paused"] = "active"
    # Korean AI translation of title/excerpt; set only once the source's terms allow it.
    ai_translation: bool = False

    @field_validator("site_url", "feed_url")
    @classmethod
    def _urls(cls, value: str | None) -> str | None:
        return _http_url(value)

    @model_validator(mode="after")
    def _adapter_settings(self) -> "SourceDef":
        if (self.kind == "news") != (self.channel is None):
            raise ValueError("news sources have no channel; every other source needs one")
        if (self.channel is None) != (self.channel_name is None):
            raise ValueError("channel and channel_name go together")
        if self.adapter == "rss" and self.feed_url is None:
            raise ValueError("rss sources need a feed_url")
        if self.ai_translation and (self.kind != "news" or self.language != "en"):
            raise ValueError("ai_translation is only for English news sources")
        model = _OPTIONS[self.adapter]
        if model is None:
            if self.options:
                raise ValueError("rss sources take no options")
        else:
            # Store the options with defaults filled in, so the collector reads one shape.
            self.options = model.model_validate(self.options).model_dump(exclude_none=True)
        return self


class SourcesFile(_Strict):
    sources: list[SourceDef] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique(self) -> "SourcesFile":
        _require_unique([s.slug for s in self.sources], "source slug")
        channels: dict[str, tuple[str | None, bool]] = {}
        for source in self.sources:
            if source.channel is None:
                continue
            shape = (source.channel_name, source.adapter == "rss")
            if channels.setdefault(source.channel, shape) != shape:
                raise ValueError(
                    f"channel '{source.channel}': sources must share the name and must all "
                    "have metrics (API) or all be feeds (rss)"
                )
        return self


def read_sources(path: Path) -> SourcesFile:
    return _validate(SourcesFile, _read_yaml(path), path)


def apply_sources(db: Session, content: SourcesFile) -> LoadReport:
    report = LoadReport(track="sources", kind="file")
    existing = {s.slug: s for s in db.scalars(select(ContentSource))}
    for position, source_def in enumerate(content.sources, start=1):
        values = source_def.model_dump(exclude={"slug"}) | {"position": position}
        source = existing.get(source_def.slug)
        if source is None:
            db.add(ContentSource(slug=source_def.slug, **values))
            report.created.append(source_def.slug)
        elif _assign(source, values):
            report.updated.append(source_def.slug)

    listed = {s.slug for s in content.sources}
    for slug, source in existing.items():
        if slug not in listed and source.status != "retired":
            source.status = "retired"
            report.retired.append(slug)
    db.flush()
    return report


__all__ = [
    "ContentError",
    "SourcesFile",
    "TechnologiesFile",
    "apply_sources",
    "apply_technologies",
    "read_sources",
    "read_technologies",
]
