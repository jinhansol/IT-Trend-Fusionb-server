# backend/routers/home_router.py
# flake8: noqa

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from datetime import datetime, timedelta

from database.mariadb import SessionLocal
from database.models import NewsFeed
from services.home_service import serialize_news, build_charts
from services.news_service import run_news_pipeline

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

# 최근 7일
def last_7_days():
    return datetime.utcnow() - timedelta(days=7)


# ============================================================
# 🔓 PUBLIC 홈
# ============================================================
@router.get("/public")
def public_home(
    keyword: str = Query(None),
    db: Session = Depends(get_db),
):

    # ⭐ DB 0개면 첫 접근에서만 초기 크롤링
    if db.query(NewsFeed).count() == 0:
        print("🟡 DB 비어있음 → 최초 자동 크롤 실행")
        run_news_pipeline()

    seven_days = last_7_days()

    try:
        # 🔍 검색 모드
        if keyword:
            items = (
                db.query(NewsFeed)
                .filter(
                    and_(
                        NewsFeed.created_at >= seven_days,
                        or_(
                            NewsFeed.title.ilike(f"%{keyword}%"),
                            NewsFeed.summary.ilike(f"%{keyword}%"),
                            NewsFeed.keywords.ilike(f"%{keyword}%"),
                        )
                    )
                )
                .order_by(NewsFeed.created_at.desc())
                .limit(50)
                .all()
            )

            return {
                "mode": "public-search",
                "keyword": keyword,
                "news": [serialize_news(n) for n in items],
                "charts": build_charts(items),
            }

        # 📰 기본 모드 → 최신 8개 랜덤
        latest_news = (
            db.query(NewsFeed)
            .filter(NewsFeed.created_at >= seven_days)
            .order_by(func.random())
            .limit(8)
            .all()
        )

        # 📊 차트 데이터
        chart_items = (
            db.query(NewsFeed)
            .filter(NewsFeed.created_at >= seven_days)
            .order_by(NewsFeed.created_at.desc())
            .limit(1000)
            .all()
        )

        return {
            "mode": "public",
            "keyword": "ALL",
            "news": [serialize_news(n) for n in latest_news],
            "charts": build_charts(chart_items),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"공개 홈 오류: {e}")
