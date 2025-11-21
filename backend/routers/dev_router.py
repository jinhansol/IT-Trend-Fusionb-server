# backend/routers/dev_router.py
# flake8: noqa

from fastapi import APIRouter, Depends
from core.security import get_current_user
from sqlalchemy.orm import Session

from database.mariadb import SessionLocal
from database.models import UserProfile

from services.dev_service import (
    fetch_github_trending,
    fetch_velog_popular_tags,
    fetch_velog_trending_posts,
    fetch_github_repo_updates,
)

router = APIRouter(prefix="/api/dev", tags=["DevDashboard"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ===========================================================
# PUBLIC
# ===========================================================
@router.get("/public")
def public_dev_feed(lang: str = "", since: str = "daily"):
    github = fetch_github_trending(language=lang, since=since)
    velog_trending = fetch_velog_trending_posts()
    velog_tags = fetch_velog_popular_tags()

    return {
        "mode": "public",
        "github_trending": github,
        "velog_trending": velog_trending,
        "velog_tags": velog_tags,
    }


# ===========================================================
# PERSONAL
# ===========================================================
@router.get("/personal")
def personal_dev_feed(
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    if not current_user.tech_stack:
        return {"mode": "public"}

    tech_list = current_user.tech_stack
    github_updates = []

    for tech in tech_list:
        repo = f"{tech}/{tech}"
        info = fetch_github_repo_updates(repo)
        if info:
            github_updates.append(info)

    return {
        "mode": "personal",
        "tech_stack": tech_list,
        "github_updates": github_updates,
        "velog_recommended": [],
    }
