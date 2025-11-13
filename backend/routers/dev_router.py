# routers/dev_router.py
from fastapi import APIRouter, Depends, Query, HTTPException
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


# ============================
# 🔓 Public Dev Trends
# ============================
@router.get("/public")
def public_dev_trends(
    keyword: str = Query(None),
    db: Session = Depends(get_db)
):
    try:
        query = db.query(TechTrend)

        if keyword:
            query = query.filter(TechTrend.keyword.ilike(f"%{keyword}%"))

        results = (
            query.order_by(TechTrend.fetched_at.desc())
            .limit(20)
            .all()
        )
        return {"mode": "public", "results": results}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dev public 오류: {e}")


# ============================
# 🔐 Personalized Dev Trends
# ============================
@router.get("/trend")
def personalized_dev(
    keyword: str = Query(None),
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        if keyword:
            results = (
                db.query(TechTrend)
                .filter(TechTrend.keyword.ilike(f"%{keyword}%"))
                .order_by(TechTrend.fetched_at.desc())
                .limit(20)
                .all()
            )
            return {"mode": "personalized-search", "results": results}

        stack = current_user.tech_stack or ["Python", "React"]

        results = (
            db.query(TechTrend)
            .filter(or_(*[TechTrend.keyword.ilike(f"%{s}%") for s in stack]))
            .order_by(TechTrend.fetched_at.desc())
            .limit(20)
            .all()
        )

        return {"mode": "personalized", "stack": stack, "results": results}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dev personalized 오류: {e}")
