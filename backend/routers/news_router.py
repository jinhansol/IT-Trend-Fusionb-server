# backend/routers/news_router.py
# flake8: noqa

from fastapi import APIRouter, Query
from sqlalchemy.orm import Session

from database.mariadb import SessionLocal
from database.models import NewsFeed
from services.news_service import run_news_pipeline

router = APIRouter(prefix="/api/news", tags=["News"])


# -----------------------------
# 1️⃣ 최신 뉴스 가져오기
# -----------------------------
@router.get("/latest")
def get_latest_news(limit: int = Query(10, description="가져올 뉴스 개수")):
    db: Session = SessionLocal()

    try:
        news = (
            db.query(NewsFeed)
            .order_by(NewsFeed.published_at.desc())
            .limit(limit)
            .all()
        )

        result = []
        for item in news:
            result.append({
                "id": item.id,
                "title": item.title,
                "summary": item.summary,
                "category": item.category,
                "keywords": item.keywords,
                "source": item.source,
                "url": item.url,
                "published_at": item.published_at,
            })

        return {"status": "success", "count": len(result), "news": result}

    finally:
        db.close()


# -----------------------------
# 2️⃣ 강제로 뉴스 크롤링 실행
# -----------------------------
@router.post("/refresh")
def refresh_news():
    print("🛰️ [API] 강제 뉴스 크롤링 실행")
    run_news_pipeline()
    return {"status": "success", "message": "뉴스 최신 데이터 수집 완료"}
