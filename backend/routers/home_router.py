# backend/routers/home_router.py
# flake8: noqa

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from datetime import datetime, timedelta

from database.mariadb import SessionLocal
from database.models import NewsFeed
from core.security import get_current_user

# ✅ [수정된 부분] 모든 서비스 함수를 home_service에서 가져옵니다!
from services.home_service import (
    serialize_news, 
    build_charts, 
    run_news_pipeline,          # news_service에서 이사옴
    get_trend_recommendations   # trend_service에서 이사옴
)

router = APIRouter(prefix="/api/home", tags=["Home Dashboard"])


# -------------------------
# 🔌 DB 연결 의존성
# -------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 최근 7일 계산 헬퍼
def last_7_days():
    return datetime.utcnow() - timedelta(days=7)


# ============================================================
# 🔓 1. PUBLIC 홈 (검색 + 랜덤 뉴스 + 차트)
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
        # 🔍 A. 검색 모드
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

        # 📰 B. 기본 모드 → 최신 8개 랜덤
        latest_news = (
            db.query(NewsFeed)
            .filter(NewsFeed.created_at >= seven_days)
            .order_by(func.random())
            .limit(8)
            .all()
        )

        # 📊 C. 차트 데이터 (최근 1000개 기반)
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


# ============================================================
# 🔍 2. 검색 / 개인화 트렌드 (Search & Trend)
# ============================================================
@router.get("/search")
def search_home(keyword: str, db: Session = Depends(get_db)):
    """키워드 검색 결과를 반환 (프론트엔드 API 통일용)"""
    return public_home(keyword=keyword, db=db)


@router.get("/trend/recommend")
async def trend_recommend(current_user=Depends(get_current_user)):
    """
    [Personal] 로그인한 사용자의 관심사 기반 트렌드 추천
    """
    try:
        return await get_trend_recommendations(current_user.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"트렌드 추천 오류: {e}")


# ============================================================
# 📰 3. 뉴스 관리 (News Management)
# ============================================================
@router.get("/news/latest")
def get_latest_news(
    limit: int = Query(10, description="가져올 뉴스 개수"),
    db: Session = Depends(get_db)
):
    """최신 뉴스 단순 목록 조회"""
    try:
        news = (
            db.query(NewsFeed)
            .order_by(NewsFeed.published_at.desc())
            .limit(limit)
            .all()
        )
        return {"status": "success", "count": len(news), "news": [serialize_news(n) for n in news]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/news/refresh")
def refresh_news():
    """강제 뉴스 크롤링 실행 (관리자용)"""
    print("🛰️ [API] 강제 뉴스 크롤링 실행")
    run_news_pipeline()
    return {"status": "success", "message": "뉴스 최신 데이터 수집 완료"}