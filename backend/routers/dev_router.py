# backend/routers/dev_router.py
# flake8: noqa

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.security import get_current_user_optional
from database.mariadb import SessionLocal
from database.models import UserProfile

from services.dev_service import (
    build_public_feed,
    build_personal_feed,
    get_source_feed,
    search_by_tag,
    refresh_all_sources,
    collect_all_tags,
    build_topic_clusters,
    build_issue_stats,
)

# 통합된 스키마 사용 (중요!)
from schemas.dev_schema import (
    DevFeedResponse, 
    SourceFeedResponse,
    TagSearchResponse,
)

router = APIRouter(prefix="/api/dev", tags=["DevDashboard"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -------------------------------------------------------------
# 🔥 자동 Public ↔ Personal Feed
# -------------------------------------------------------------
@router.get("/", response_model=DevFeedResponse)
def dev_feed(
    current_user: UserProfile = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    if current_user is None:
        return build_public_feed(db)
    return build_personal_feed(current_user, db)


# -------------------------------------------------------------
# 🔵 Public Feed
# -------------------------------------------------------------
@router.get("/public", response_model=DevFeedResponse)
def dev_public(db: Session = Depends(get_db)):
    return build_public_feed(db)


# -------------------------------------------------------------
# 🟣 Personal Feed (로그인 안 해도 에러 안 나고 Public 줌)
# -------------------------------------------------------------
@router.get("/personal", response_model=DevFeedResponse)
def dev_personal(
    current_user: UserProfile = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    # 로그인 X → public 반환 (Fallback)
    if current_user is None:
        return build_public_feed(db)

    # 로그인 O → personalized feed
    try:
        return build_personal_feed(current_user, db)
    except Exception as e:
        print(f"Personal Feed Error: {e}")
        # 에러 나면 안전하게 Public 반환
        return build_public_feed(db)


# -------------------------------------------------------------
# 🔍 Source Feed
# -------------------------------------------------------------
@router.get("/source/{source}", response_model=SourceFeedResponse)
def dev_source_feed(
    source: str,
    page: int = 1,
    size: int = 10,
    db: Session = Depends(get_db),
):
    source = source.lower()
    if source not in ["okky", "devto"]:
        raise HTTPException(status_code=400, detail="Invalid Source")

    try:
        items, total = get_source_feed(db, source, page, size)
        return SourceFeedResponse(source=source, total=total, items=items)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------
# 🏷 Tag 검색
# -------------------------------------------------------------
@router.get("/search", response_model=TagSearchResponse)
def dev_search(tag: str, db: Session = Depends(get_db)):
    return search_by_tag(db, tag)


# -------------------------------------------------------------
# 🔄 전체 갱신
# -------------------------------------------------------------
@router.get("/refresh")
def dev_refresh(db: Session = Depends(get_db)):
    return refresh_all_sources(db)


# -------------------------------------------------------------
# 🔖 전체 태그 목록
# -------------------------------------------------------------
@router.get("/tags")
def dev_tags(db: Session = Depends(get_db)):
    tags = collect_all_tags(db)
    return {"tags": tags}


# -------------------------------------------------------------
# ❤️ Health Check
# -------------------------------------------------------------
@router.get("/health")
def dev_health():
    return {"status": "ok", "service": "dev-dashboard"}


# -------------------------------------------------------------
# 🔥 Insight
# -------------------------------------------------------------
@router.get("/insight/topic")
def dev_topic_insight(db: Session = Depends(get_db)):
    return build_topic_clusters(db)

@router.get("/insight/issues")
def dev_issue_insight(db: Session = Depends(get_db)):
    return build_issue_stats(db)