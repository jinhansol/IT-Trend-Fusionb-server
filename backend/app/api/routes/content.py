from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_settings
from app.core.config import Settings
from app.schemas.content import ContentPage, DevChannelList, FeedStatus, TrendReport
from app.services import content_feed

# Public, read-only. Collection runs in the separate job (python -m app.jobs), never here.
router = APIRouter(prefix="/api", tags=["content"])

Page = Query(1, ge=1, le=1000)
Size = Query(12, ge=1, le=50)
Days = Query(7, ge=1, le=30)
Tech = Query(None, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=64)
Scope = Literal["news", "dev"]


@router.get("/news", response_model=ContentPage)
def list_news(
    page: int = Page, size: int = Size, tech: str | None = Tech, db: Session = Depends(get_db)
) -> ContentPage:
    return content_feed.list_news(db, page, size, tech)


@router.get("/dev/channels", response_model=DevChannelList)
def list_channels(db: Session = Depends(get_db)) -> DevChannelList:
    return content_feed.list_channels(db)


@router.get("/dev/channels/{channel}/posts", response_model=ContentPage)
def list_channel_posts(
    channel: str,
    sort: Literal["latest", "popular"] = "latest",
    days: int = Days,
    page: int = Page,
    size: int = Size,
    tech: str | None = Tech,
    db: Session = Depends(get_db),
) -> ContentPage:
    return content_feed.list_channel_posts(db, channel, sort, days, page, size, tech)


@router.get("/trends", response_model=TrendReport)
def trends(scope: Scope = "news", days: int = Days, db: Session = Depends(get_db)) -> TrendReport:
    return content_feed.trends(db, scope, days)


@router.get("/feed-status", response_model=FeedStatus)
def feed_status(
    scope: Scope = "news",
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> FeedStatus:
    return content_feed.feed_status(db, settings, scope)
