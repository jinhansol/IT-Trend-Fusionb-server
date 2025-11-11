# routers/career_router.py
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from database.mariadb import SessionLocal
from database.models import UserProfile, CareerJob
from core.security import get_current_user

router = APIRouter(prefix="/api/career", tags=["Career"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("")
def personalized_career(
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    ✅ 커리어 피드 — role_type(직무) 기반 채용 정보 추천
    """
    role = current_user.role_type or "개발자"
    print(f"💼 [Career] {current_user.username} ({role})의 맞춤 채용 추천")

    try:
        results = (
            db.query(CareerJob)
            .filter(CareerJob.title.ilike(f"%{role}%"))
            .order_by(CareerJob.posted_date.desc())
            .limit(10)
            .all()
        )
        return {"user": current_user.username, "role_type": role, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"커리어 데이터 로드 오류: {e}")
