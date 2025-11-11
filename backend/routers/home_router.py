# routers/home_router.py
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from database.mariadb import SessionLocal
from database.models import UserProfile, NewsFeed
from core.security import get_current_user

router = APIRouter(prefix="/api/home", tags=["Home"])

# ✅ DB 의존성
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("")
def personalized_home(
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    ✅ 홈 피드 — 사용자 관심 키워드 기반 뉴스 추천
    """
    interests = current_user.interest_topics or ["IT", "AI", "개발"]
    print(f"🔎 [Home] {current_user.username}님의 관심사: {interests}")

    try:
        results = (
            db.query(NewsFeed)
            .filter(or_(*[NewsFeed.title.ilike(f"%{kw}%") for kw in interests]))
            .order_by(NewsFeed.published_at.desc())
            .limit(10)
            .all()
        )
        return {"user": current_user.username, "interests": interests, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"홈 피드 로드 오류: {e}")
