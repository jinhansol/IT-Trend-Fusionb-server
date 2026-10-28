"""Read models for Home (news) and Dev (posts and questions). Read-only.

Lists are ordered by publish time (collection time when a feed gives none).
Retired sources are hidden; paused sources keep showing what was collected.
"""

from datetime import timedelta

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings
from app.core.errors import AppError
from app.db.types import utc_now
from app.models.content import Content, ContentSource, ContentTechnology, JobRun, Technology
from app.schemas.content import (
    ChannelSource,
    ContentItem,
    ContentPage,
    CountItem,
    DailyCount,
    DevChannel,
    DevChannelList,
    FeedStatus,
    SourceRef,
    SourceStatus,
    TechnologyRef,
    TrendReport,
)

TOP_TECHNOLOGIES = 10
DAILY_TECHNOLOGIES = 5


class ChannelNotFound(AppError):
    status_code = 404
    code = "CHANNEL_NOT_FOUND"

    def __init__(self) -> None:
        super().__init__("Channel not found")


class SortNotSupported(AppError):
    status_code = 422
    code = "SORT_NOT_SUPPORTED"

    def __init__(self) -> None:
        super().__init__("This channel has no popularity metric; use sort=latest")


def _visible_sources(scope: str):
    condition = ContentSource.status != "retired"
    if scope == "news":
        return condition & (ContentSource.kind == "news")
    return condition & (ContentSource.kind != "news")


def _item(content: Content) -> ContentItem:
    return ContentItem(
        id=content.id,
        title=content.title,
        url=content.url,
        excerpt=content.excerpt,
        author=content.author,
        source=SourceRef(slug=content.source.slug, name=content.source.name),
        published_at=content.published_at,
        collected_at=content.collected_at,
        score=content.score,
        comment_count=content.comment_count,
        view_count=content.view_count,
        technologies=sorted(
            (
                TechnologyRef(slug=link.technology.slug, name=link.technology.name)
                for link in content.technologies
                if link.technology.status == "published"
            ),
            key=lambda t: t.name.lower(),
        ),
    )


def _page(db: Session, query: Select, order_by, page: int, size: int) -> ContentPage:
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.scalars(
        query.options(
            selectinload(Content.source),
            selectinload(Content.technologies).selectinload(ContentTechnology.technology),
        )
        .order_by(*order_by)
        .limit(size)
        .offset((page - 1) * size)
    )
    return ContentPage(items=[_item(c) for c in rows], page=page, size=size, total=total)


def _with_technology(query: Select, tech: str | None) -> Select:
    if tech is None:
        return query
    return query.where(
        select(ContentTechnology.content_id)
        .join(Technology, Technology.id == ContentTechnology.technology_id)
        .where(ContentTechnology.content_id == Content.id, Technology.slug == tech)
        .exists()
    )


def list_news(db: Session, page: int, size: int, tech: str | None) -> ContentPage:
    query = select(Content).join(ContentSource).where(_visible_sources("news"))
    return _page(
        db, _with_technology(query, tech), (Content.sort_at.desc(), Content.id.desc()), page, size
    )


def list_channels(db: Session) -> DevChannelList:
    channels: dict[str, DevChannel] = {}
    for source in db.scalars(
        select(ContentSource).where(_visible_sources("dev")).order_by(ContentSource.position)
    ):
        channel = channels.get(source.channel)
        if channel is None:
            channel = channels[source.channel] = DevChannel(
                slug=source.channel,
                name=source.channel_name,
                kind=source.kind,
                has_metrics=source.adapter != "rss",
                sources=[],
            )
        channel.sources.append(ChannelSource(slug=source.slug, name=source.name))
    return DevChannelList(items=list(channels.values()))


def list_channel_posts(
    db: Session, channel: str, sort: str, days: int, page: int, size: int, tech: str | None
) -> ContentPage:
    sources = list(
        db.scalars(
            select(ContentSource).where(_visible_sources("dev"), ContentSource.channel == channel)
        )
    )
    if not sources:
        raise ChannelNotFound()
    query = select(Content).where(Content.source_id.in_([s.id for s in sources]))
    query = _with_technology(query, tech)
    if sort == "popular":
        if all(s.adapter == "rss" for s in sources):
            raise SortNotSupported()
        query = query.where(Content.sort_at >= utc_now() - timedelta(days=days))
        order = (Content.score.desc(), Content.sort_at.desc(), Content.id.desc())
    else:
        order = (Content.sort_at.desc(), Content.id.desc())
    return _page(db, query, order, page, size)


def trends(db: Session, scope: str, days: int) -> TrendReport:
    since = utc_now() - timedelta(days=days)
    in_scope = (
        select(Content.id)
        .join(ContentSource)
        .where(_visible_sources(scope), Content.sort_at >= since)
    )
    total = db.scalar(select(func.count()).select_from(in_scope.subquery()))

    counts = db.execute(
        select(Technology.slug, Technology.name, Technology.kind, func.count())
        .join(ContentTechnology, ContentTechnology.technology_id == Technology.id)
        .where(ContentTechnology.content_id.in_(in_scope), Technology.status == "published")
        .group_by(Technology.id)
        .order_by(func.count().desc(), Technology.name)
    ).all()
    fields = [CountItem(slug=s, name=n, count=c) for s, n, kind, c in counts if kind == "field"]
    techs = [CountItem(slug=s, name=n, count=c) for s, n, kind, c in counts if kind != "field"]
    top = techs[:DAILY_TECHNOLOGIES]

    day = func.date(Content.sort_at)
    per_day = dict(
        db.execute(select(day, func.count()).where(Content.id.in_(in_scope)).group_by(day)).all()
    )
    per_day_tech: dict[str, dict[str, int]] = {}
    if top:
        for date, slug, count in db.execute(
            select(day, Technology.slug, func.count())
            .join(ContentTechnology, ContentTechnology.content_id == Content.id)
            .join(Technology, Technology.id == ContentTechnology.technology_id)
            .where(Content.id.in_(in_scope), Technology.slug.in_([t.slug for t in top]))
            .group_by(day, Technology.slug)
        ):
            per_day_tech.setdefault(str(date), {})[slug] = count

    today = utc_now().date()
    daily = []
    for offset in range(days - 1, -1, -1):
        date = today - timedelta(days=offset)
        counts_for_day = per_day_tech.get(str(date), {})
        daily.append(
            DailyCount(
                date=str(date),
                total=per_day.get(date, 0),
                counts={t.slug: counts_for_day.get(t.slug, 0) for t in top},
            )
        )
    return TrendReport(
        scope=scope,
        days=days,
        total=total,
        fields=fields,
        technologies=techs[:TOP_TECHNOLOGIES],
        daily=daily,
        daily_technologies=[TechnologyRef(slug=t.slug, name=t.name) for t in top],
    )


def feed_status(db: Session, settings: Settings, scope: str) -> FeedStatus:
    sources = list(
        db.scalars(
            select(ContentSource)
            .where(_visible_sources(scope), ContentSource.status == "active")
            .order_by(ContentSource.position)
        )
    )
    ids = [s.id for s in sources]
    last_success = (
        dict(
            db.execute(
                select(JobRun.source_id, func.max(JobRun.finished_at))
                .where(JobRun.source_id.in_(ids), JobRun.status == "succeeded")
                .group_by(JobRun.source_id)
            ).all()
        )
        if ids
        else {}
    )
    latest_ids = (
        select(func.max(JobRun.id)).where(JobRun.source_id.in_(ids)).group_by(JobRun.source_id)
    )
    last_status = (
        dict(
            db.execute(
                select(JobRun.source_id, JobRun.status).where(JobRun.id.in_(latest_ids))
            ).all()
        )
        if ids
        else {}
    )

    stale_before = utc_now() - timedelta(hours=settings.feed_stale_after_hours)
    statuses = [
        SourceStatus(
            slug=s.slug,
            name=s.name,
            channel=s.channel,
            last_success_at=last_success.get(s.id),
            last_run_status=last_status.get(s.id),
            stale=last_success.get(s.id) is None or last_success[s.id] < stale_before,
        )
        for s in sources
    ]
    successes = [s.last_success_at for s in statuses if s.last_success_at]
    last_updated = max(successes) if successes else None
    return FeedStatus(
        scope=scope,
        last_updated_at=last_updated,
        stale=last_updated is None or last_updated < stale_before,
        sources=statuses,
    )
