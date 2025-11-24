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
    get_source_feed,
    search_by_tag,
    refresh_all_sources,
    collect_all_tags,
)

from schemas.dev_schema import (
    PublicDevFeedResponse,
    PersonalDevFeedResponse,
    SourceFeedResponse,
    TagSearchResponse,
)

router = APIRouter(prefix="/api/dev", tags=["DevDashboard"])


# -------------------------------------------------------------
# DB 의존성
# -------------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -------------------------------------------------------------
# 🔥 자동 Public ↔ Personal 전환
# -------------------------------------------------------------
@router.get("/", response_model=dict)
def dev_feed(
    current_user: UserProfile = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    try:
        if current_user is None:
            return build_public_feed(db)
        return build_personal_feed(current_user, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------
# 🔵 Public Feed
# -------------------------------------------------------------
@router.get("/public", response_model=PublicDevFeedResponse)
def dev_public(db: Session = Depends(get_db)):
    try:
        return build_public_feed(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------
# 🟣 Personal Feed (로그인 필요)
# -------------------------------------------------------------
@router.get("/personal", response_model=PersonalDevFeedResponse)
def dev_personal(
    current_user: UserProfile = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    if current_user is None:
        raise HTTPException(status_code=401, detail="로그인이 필요한 기능입니다.")

    try:
        return build_personal_feed(current_user, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------
# 🔍 Source Feed — OKKY & DEVTO만 허용
# -------------------------------------------------------------
@router.get("/source/{source}", response_model=SourceFeedResponse)
def dev_source_feed(source: str, db: Session = Depends(get_db)):
    source = source.lower()
    if source not in ["okky", "devto"]:
        raise HTTPException(status_code=400, detail="Invalid Source (okky, devto만 지원)")

    try:
        rows = get_source_feed(db, source)
        return SourceFeedResponse(
            source=source,
            total=len(rows),
            items=rows,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------
# 🏷 Tag 검색
# -------------------------------------------------------------
@router.get("/search", response_model=TagSearchResponse)
def dev_search(tag: str, db: Session = Depends(get_db)):
    try:
        return search_by_tag(db, tag)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------
# 🔄 Refresh All Sources (OKKY + DEVTO)
# -------------------------------------------------------------
@router.get("/refresh")
def dev_refresh(db: Session = Depends(get_db)):
    try:
        return refresh_all_sources(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------
# 🔖 전체 태그
# -------------------------------------------------------------
@router.get("/tags")
def dev_tags(db: Session = Depends(get_db)):
    try:
        tags = collect_all_tags(db)
        return {"tags": tags}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------
# ❤️ Health Check
# -------------------------------------------------------------
@router.get("/health")
def dev_health():
    return {"status": "ok", "service": "dev-dashboard"}
