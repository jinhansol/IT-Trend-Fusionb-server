# backend/routers/roadmap_router.py
# flake8: noqa

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.mariadb import get_db
from services.roadmap_service import get_roadmap, complete_node
from schemas.roadmap_schema import RoadmapResponse, NodeCompleteResponse

router = APIRouter(prefix="/api/roadmap", tags=["Roadmap"])


# ================================================================
# ⭐ 1) Public Web 로드맵
# ================================================================
@router.get("/public", response_model=RoadmapResponse)
def api_public_roadmap(db: Session = Depends(get_db)):
    """
    slug를 DB에 실제 존재하는 public slug로 고정
    """
    data = get_roadmap(db, "web-roadmap", user_id=None)  # ← 여기를 DB slug에 맞춰야 함
    if not data:
        raise HTTPException(status_code=404, detail="Public roadmap not found")
    return data


# ================================================================
# ⭐ 2) Personal 로드맵
# ================================================================
@router.get("/personal/{user_id}", response_model=RoadmapResponse)
def api_personal_roadmap(user_id: int, db: Session = Depends(get_db)):
    """
    생활코딩 개인 로드맵 제공 (slug 고정)
    """
    data = get_roadmap(db, "life-coding", user_id)
    if not data:
        raise HTTPException(status_code=404, detail="Personal roadmap not found")
    return data


# ================================================================
# 🔹 3) 노드 완료
# ================================================================
@router.post("/complete/{user_id}/{node_db_id}", response_model=NodeCompleteResponse)
def api_complete_node(user_id: int, node_db_id: int, db: Session = Depends(get_db)):
    progress = complete_node(db, user_id, node_db_id)
    if not progress:
        raise HTTPException(status_code=404, detail="Node not found")

    return {"message": "Node completed", "status": progress.status}


# ================================================================
# 🔹 4) 트랙 목록 조회
# ================================================================
@router.get("/list")
def api_track_list(db: Session = Depends(get_db)):
    return db.execute("SELECT slug, title FROM skill_tracks").fetchall()


# ================================================================
# ⭐ 5) Public slug 조회 (/web-basic, /html-basic 등)
# ================================================================
@router.get("/{track_slug}", response_model=RoadmapResponse)
def api_get_roadmap_no_user(track_slug: str, db: Session = Depends(get_db)):
    data = get_roadmap(db, track_slug, user_id=None)
    if not data:
        raise HTTPException(status_code=404, detail="Track not found")
    return data


# ================================================================
# ⭐ 6) Personal slug 조회 (/web-basic/3)
# ================================================================
@router.get("/{track_slug}/{user_id}", response_model=RoadmapResponse)
def api_get_roadmap(track_slug: str, user_id: int, db: Session = Depends(get_db)):
    data = get_roadmap(db, track_slug, user_id)
    if not data:
        raise HTTPException(status_code=404, detail="Track not found")
    return data
