# routers/dev_router.py
# flake8: noqa

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.security import get_current_user_optional
from database.mariadb import SessionLocal
from database.models import UserProfile

from services.dev_service import (
    build_public_feed,
    build_personal_feed,
    fetch_github_trending,
    fetch_velog_by_tag_html,
    fetch_velog_trending_html,
)

router = APIRouter(prefix="/api/dev", tags=["Dev"])


# -------------------------------------------------------
# DB 세션
# -------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -------------------------------------------------------
# 🔥 통합 Dev Feed (자동 분기)
# -------------------------------------------------------
@router.get("/")
def dev_feed(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user_optional),
):
    """
    로그인 O → Personal
    로그인 X → Public
    """

    # 로그인 X
    if current_user is None:
        return build_public_feed()

    # 로그인 O
    try:
        return build_personal_feed(current_user, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"개인화 피드 오류: {e}")


# -------------------------------------------------------
# Public feed (직접 접근)
# -------------------------------------------------------
@router.get("/public")
def dev_public():
    return build_public_feed()


# -------------------------------------------------------
# GitHub Trending
# -------------------------------------------------------
@router.get("/github")
def github_trending(language: str = "", since: str = "daily"):
    try:
        return {"results": fetch_github_trending(language, since)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GitHub Trending 오류: {e}")


# -------------------------------------------------------
# Velog by Tag
# -------------------------------------------------------
@router.get("/velog/tag")
def velog_by_tag(tag: str):
    try:
        return {"results": fetch_velog_by_tag_html(tag)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Velog 태그 오류: {e}")


# -------------------------------------------------------
# Velog Trending
# -------------------------------------------------------
@router.get("/velog/trending")
def velog_trending():
    try:
        return {"results": fetch_velog_trending_html()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Velog Trending 오류: {e}")


# -------------------------------------------------------
# Health check
# -------------------------------------------------------
@router.get("/health")
def dev_health():
    return {"status": "ok"}
