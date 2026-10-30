"""Collected content (news, blog posts, Q&A) and the technology taxonomy.

Technologies and sources are managed in YAML files and loaded like learning content.
Contents are written only by the collector jobs; web requests read them.
Metrics a source does not provide stay NULL, so "not provided" differs from 0.
"""

from datetime import datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Computed,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import BigId, UtcDateTime, utc_now
from app.models.learning import _in_list

TECHNOLOGY_KINDS = ("language", "framework", "library", "tool", "platform", "field")
TAXONOMY_STATUSES = ("published", "retired")
SOURCE_KINDS = ("news", "blog", "community", "qna")
SOURCE_ADAPTERS = ("rss", "devto", "hackernews", "stackoverflow")
SOURCE_STATUSES = ("active", "paused", "retired")
SUMMARY_STATUSES = ("pending", "done", "failed", "skipped")
TAG_METHODS = ("rule", "llm", "manual")
JOB_STATUSES = ("running", "succeeded", "failed", "skipped")


class Technology(Base):
    __tablename__ = "technologies"
    __table_args__ = (
        CheckConstraint(_in_list("kind", TECHNOLOGY_KINDS), name="kind_valid"),
        CheckConstraint(_in_list("status", TAXONOMY_STATUSES), name="status_valid"),
    )

    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    kind: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utc_now, onupdate=utc_now)

    aliases: Mapped[list["TechnologyAlias"]] = relationship(
        back_populates="technology", cascade="all, delete-orphan"
    )


class TechnologyAlias(Base):
    """A lower-cased word that marks content as being about a technology.

    tag_only aliases (e.g. "go") are matched against a source's own tags only,
    never against free text, where they would be ordinary words.
    """

    __tablename__ = "technology_aliases"

    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    technology_id: Mapped[int] = mapped_column(
        BigId, ForeignKey("technologies.id", ondelete="CASCADE")
    )
    alias: Mapped[str] = mapped_column(String(100), unique=True)
    tag_only: Mapped[bool] = mapped_column(default=False)

    technology: Mapped[Technology] = relationship(back_populates="aliases")


class ContentSource(Base):
    __tablename__ = "content_sources"
    __table_args__ = (
        CheckConstraint(_in_list("kind", SOURCE_KINDS), name="kind_valid"),
        CheckConstraint(_in_list("adapter", SOURCE_ADAPTERS), name="adapter_valid"),
        CheckConstraint(_in_list("status", SOURCE_STATUSES), name="status_valid"),
    )

    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    kind: Mapped[str] = mapped_column(String(20))
    adapter: Mapped[str] = mapped_column(String(20))
    site_url: Mapped[str] = mapped_column(String(2048))
    feed_url: Mapped[str | None] = mapped_column(String(2048))
    language: Mapped[str] = mapped_column(String(10))
    # Adapter settings such as a Dev.to tag or a Stack Exchange site.
    options: Mapped[dict] = mapped_column(JSON, default=dict)
    max_items: Mapped[int] = mapped_column(Integer, default=30)
    # Dev screen tab this source belongs to (several company blogs share one tab).
    # News sources have no channel.
    channel: Mapped[str | None] = mapped_column(String(64))
    channel_name: Mapped[str | None] = mapped_column(String(100))
    # Order in the sources file; channels are shown in the order they first appear.
    position: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utc_now, onupdate=utc_now)


class Content(Base):
    __tablename__ = "contents"
    __table_args__ = (
        # One row per article per source. The same link from two sources is two rows,
        # because each source carries its own score and comments.
        UniqueConstraint("source_id", "url_hash"),
        CheckConstraint(_in_list("summary_status", SUMMARY_STATUSES), name="summary_valid"),
        Index("ix_contents_sort", "sort_at", "id"),
        Index("ix_contents_source_sort", "source_id", "sort_at", "id"),
    )

    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(
        BigId, ForeignKey("content_sources.id", ondelete="RESTRICT")
    )
    external_id: Mapped[str | None] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(String(2048))
    url_hash: Mapped[str] = mapped_column(CHAR(64))
    title: Mapped[str] = mapped_column(String(500))
    # Short text supplied by the source (feed description). Full articles are not stored.
    excerpt: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    summary_status: Mapped[str] = mapped_column(String(20), default="pending")
    author: Mapped[str | None] = mapped_column(String(200))
    # The source's own tags, used as tagging input.
    source_tags: Mapped[list] = mapped_column(JSON, default=list)
    score: Mapped[int | None] = mapped_column(Integer)
    comment_count: Mapped[int | None] = mapped_column(Integer)
    view_count: Mapped[int | None] = mapped_column(Integer)
    published_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    collected_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utc_now, onupdate=utc_now)
    # Lists sort by publish time, falling back to collection time when a feed has none.
    # MariaDB rejects NOT NULL on generated columns; COALESCE never yields NULL here.
    sort_at: Mapped[datetime] = mapped_column(
        UtcDateTime,
        Computed("COALESCE(published_at, collected_at)", persisted=True),
        nullable=True,
    )

    source: Mapped[ContentSource] = relationship()
    technologies: Mapped[list["ContentTechnology"]] = relationship(
        back_populates="content", cascade="all, delete-orphan"
    )


class ContentTechnology(Base):
    __tablename__ = "content_technologies"
    __table_args__ = (CheckConstraint(_in_list("method", TAG_METHODS), name="method_valid"),)

    content_id: Mapped[int] = mapped_column(
        BigId, ForeignKey("contents.id", ondelete="CASCADE"), primary_key=True
    )
    technology_id: Mapped[int] = mapped_column(
        BigId, ForeignKey("technologies.id", ondelete="RESTRICT"), primary_key=True, index=True
    )
    method: Mapped[str] = mapped_column(String(20))

    content: Mapped[Content] = relationship(back_populates="technologies")
    technology: Mapped[Technology] = relationship()


class JobRun(Base):
    """One collector run for one source. A failed run and a run with 0 new items differ."""

    __tablename__ = "job_runs"
    __table_args__ = (
        CheckConstraint(_in_list("status", JOB_STATUSES), name="status_valid"),
        Index("ix_job_runs_source_started", "source_id", "started_at"),
    )

    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    job_name: Mapped[str] = mapped_column(String(64))
    source_id: Mapped[int | None] = mapped_column(
        BigId, ForeignKey("content_sources.id", ondelete="RESTRICT")
    )
    status: Mapped[str] = mapped_column(String(20))
    started_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utc_now)
    finished_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    fetched_count: Mapped[int] = mapped_column(Integer, default=0)
    inserted_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_count: Mapped[int] = mapped_column(Integer, default=0)
    # Entries skipped because they lacked a usable link or title (reasons in error_summary).
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    error_summary: Mapped[str | None] = mapped_column(String(1000))
