# routers/home_router.py

from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from datetime import datetime, timedelta

from database.mariadb import SessionLocal
from database.models import NewsFeed, UserProfile
from core.security import get_current_user
from services.news_service import save_news_to_db
from services.home_service import serialize_news, build_charts

router = APIRouter(prefix="/api/home", tags=["Home"])


# -------------------------
# DB 연결
# -------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 최근 7일 필터
def last_7_days():
    return datetime.utcnow() - timedelta(days=7)


# ============================================================
# 🔓 PUBLIC 홈 (최근 7일 뉴스 + 차트)
# ============================================================
@router.get("/public")
def public_home(
    keyword: str = Query(None),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
):

    if background_tasks:
        background_tasks.add_task(save_news_to_db, "IT")

    seven_days = last_7_days()

    try:
        # -----------------------------
        # 🔍 검색 모드
        # -----------------------------
        if keyword:
            items = (
                db.query(NewsFeed)
                .filter(
                    and_(
                        NewsFeed.published_at >= seven_days,
                        or_(
                            NewsFeed.title.ilike(f"%{keyword}%"),
                            NewsFeed.summary.ilike(f"%{keyword}%"),
                        )
                    )
                )
                .order_by(NewsFeed.published_at.desc())
                .limit(50)
                .all()
            )

            charts = build_charts(items)

            return {
                "mode": "public-search",
                "keyword": keyword,
                "news": [serialize_news(n) for n in items],
                "charts": charts,
            }

        # -----------------------------
        # 📰 기본 모드 (홈 8개)
        # -----------------------------
        google_news = (
            db.query(NewsFeed)
            .filter(
                NewsFeed.source == "Google News",
                NewsFeed.published_at >= seven_days,
            )
            .order_by(NewsFeed.published_at.desc())
            .limit(4)
            .all()
        )

        naver_news = (
            db.query(NewsFeed)
            .filter(
                NewsFeed.source == "Naver News",
                NewsFeed.published_at >= seven_days,
            )
            .order_by(NewsFeed.published_at.desc())
            .limit(4)
            .all()
        )

        combined = google_news + naver_news

        # -----------------------------
        # 📊 차트용 전체 데이터 (최근 7일 1000개)
        # -----------------------------
        chart_items = (
            db.query(NewsFeed)
            .filter(NewsFeed.published_at >= seven_days)
            .order_by(NewsFeed.published_at.desc())
            .limit(1000)
            .all()
        )

        charts = build_charts(chart_items)

        return {
            "mode": "public",
            "keyword": "ALL",
            "news": [serialize_news(n) for n in combined],
            "charts": charts,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"공개 홈 오류: {e}")


# ============================================================
# 🔐 PERSONALIZED 홈 (관심사 기반 + 최근 7일 차트)
# ============================================================
@router.get("/feed")
def personalized_home(
    keyword: str = Query(None),
    current_user: UserProfile = Depends(get_current_user),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
):

    interests = current_user.interest_topics or ["IT", "AI", "기술"]
    seven_days = last_7_days()

    if background_tasks:
        for kw in interests:
            background_tasks.add_task(save_news_to_db, kw)

    try:
        # -----------------------------
        # 🔍 검색 모드
        # -----------------------------
        if keyword:
            items = (
                db.query(NewsFeed)
                .filter(
                    and_(
                        NewsFeed.published_at >= seven_days,
                        or_(
                            NewsFeed.title.ilike(f"%{keyword}%"),
                            NewsFeed.summary.ilike(f"%{keyword}%"),
                        )
                    )
                )
                .order_by(NewsFeed.published_at.desc())
                .limit(50)
                .all()
            )

            charts = build_charts(items)

            return {
                "mode": "personalized-search",
                "keyword": keyword,
                "news": [serialize_news(n) for n in items],
                "charts": charts,
            }

        # -----------------------------
        # 👤 관심사 기반 최신 뉴스 8개
        # -----------------------------
        filters = or_(*[NewsFeed.title.ilike(f"%{kw}%") for kw in interests])

        news_items = (
            db.query(NewsFeed)
            .filter(and_(filters, NewsFeed.published_at >= seven_days))
            .order_by(NewsFeed.published_at.desc())
            .limit(8)
            .all()
        )

        # -----------------------------
        # 📊 차트용 전체 7일 데이터
        # -----------------------------
        chart_items = (
            db.query(NewsFeed)
            .filter(
                and_(
                    filters,
                    NewsFeed.published_at >= seven_days,
                )
            )
            .order_by(NewsFeed.published_at.desc())
            .limit(1000)
            .all()
        )

        charts = build_charts(chart_items)

        return {
            "mode": "personalized",
            "interests": interests,
            "news": [serialize_news(n) for n in news_items],
            "charts": charts,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"개인화 홈 오류: {e}")
