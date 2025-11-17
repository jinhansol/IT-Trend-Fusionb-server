# routers/career_router.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.mariadb import SessionLocal
from database.models import UserProfile, CareerJob
from core.security import get_current_user  # ✅ NameError 방지

from services.db_service import get_recent_career_jobs
from services.career_service import (
    get_weekly_tech_trends,
    get_user_skills,
    get_recommended_jobs,
)

router = APIRouter(prefix="/api/career", tags=["Career"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =======================================================
# 🔓 비로그인 Career Dashboard
# =======================================================
@router.get("/public")
def public_dashboard(db: Session = Depends(get_db)):
    try:
        trends = get_weekly_tech_trends(db)
        jobs = get_recent_career_jobs(db)

        return {
            "mode": "public",
            "trends": trends,
            "jobs": jobs,
            "user_skills": [],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =======================================================
# 🔐 로그인 Career Dashboard
# =======================================================
@router.get("/dashboard")
def personalized_dashboard(
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        user_skills = get_user_skills(current_user)
        trends = get_weekly_tech_trends(db)
        jobs = get_recommended_jobs(db, user_skills)

        return {
            "mode": "personalized",
            "user_skills": user_skills,
            "trends": trends,
            "jobs": jobs,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
