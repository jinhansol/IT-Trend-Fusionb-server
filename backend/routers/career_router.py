# routers/career_router.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database.mariadb import SessionLocal
from database.models import UserProfile, CareerJob
from core.security import get_current_user

from services.career_service import (
    get_weekly_tech_trends,
    get_recommended_jobs,
    get_user_skills,
)

router = APIRouter(prefix="/api/career", tags=["Career"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ======================
# 🔓 비로그인 Career Dashboard
# ======================
@router.get("/public")
def public_dashboard(db: Session = Depends(get_db)):
    try:
        trends = get_weekly_tech_trends(db)
        jobs = (
            db.query(CareerJob)
            .order_by(CareerJob.posted_date.desc())
            .limit(20)
            .all()
        )

        return {
            "mode": "public",
            "trends": trends,
            "jobs": jobs,
            "user_skills": [],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ======================
# 🔐 로그인 Career Dashboard
# ======================
@router.get("/dashboard")
def personalized_dashboard(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
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
