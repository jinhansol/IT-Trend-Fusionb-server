# routers/career_router.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import os, json
from openai import OpenAI

from database.mariadb import SessionLocal
from database.models import UserProfile
from core.security import get_current_user

from services.db_service import get_recent_career_jobs
from services.career_service import (
    get_weekly_tech_trends,
    get_user_skills,
    get_recommended_jobs,
    get_jobs_paged,
)

router = APIRouter(prefix="/api/career", tags=["Career"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =======================================================
# 🔓 Public Dashboard
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
# 🔐 Personalized Dashboard
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


# =======================================================
# ⭐ 신규 API: AI 기반 학습 추천 생성
# =======================================================
@router.get("/learning")
def ai_learning_recommendation(db: Session = Depends(get_db)):
    try:
        trends = get_weekly_tech_trends(db)
        top = trends[:5] if trends else []

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        prompt = f"""
        당신은 IT 취업 코치입니다.

        아래는 최근 8주간 기술 트렌드입니다:
        {top}

        이 데이터를 기반으로 학습 추천 3개를 만들어서
        JSON 배열로 출력하세요.

        형식:
        [
          {{
            "title": "강의/학습명",
            "tag": "추천 또는 핫",
            "desc": "설명",
            "link": "https://example.com"
          }}
        ]

        JSON만 출력하세요.
        """

        response = client.responses.create(
            model="gpt-4o-mini",
            input=prompt,
        )

        raw = response.output_text.strip()
        raw = raw.replace("```json", "").replace("```", "")
        data = json.loads(raw)

        return {"learning": data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =======================================================
# ⭐ 페이징 API (기존 유지)
# =======================================================
@router.get("/jobs")
def jobs_paged(
    page: int = Query(1, ge=1),
    size: int = Query(6, ge=1),
    db: Session = Depends(get_db),
):
    try:
        return get_jobs_paged(db, page, size)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
