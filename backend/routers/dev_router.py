# routers/dev_router.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from database.mariadb import SessionLocal
from database.models import UserProfile, TechTrend
from core.security import get_current_user

router = APIRouter(prefix="/api/dev", tags=["Dev Dashboard"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("")
def personalized_dev_dashboard(
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    ✅ 개발자 대시보드 — 사용자 기술스택 기반 트렌드 추천
    """
    tech_stack = current_user.tech_stack or ["Python", "React"]
    print(f"🧠 [DevDashboard] {current_user.username}님의 기술스택: {tech_stack}")

    try:
        results = (
            db.query(TechTrend)
            .filter(or_(*[TechTrend.keyword.ilike(f"%{tech}%") for tech in tech_stack]))
            .order_by(TechTrend.fetched_at.desc())
            .limit(10)
            .all()
        )
        return {"user": current_user.username, "tech_stack": tech_stack, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dev 트렌드 로드 오류: {e}")
