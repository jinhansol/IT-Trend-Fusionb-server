# backend/routers/quest_router.py
# flake8: noqa

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.mariadb import get_db
from database.models import LearningQuest

# 📌 최신 서비스 로직 (추천 / 완료 / 리프레시)
from services.quest_service import get_today_quests, complete_quest
from services.quest_generator import refresh_learning_quests  # 🔥 NEW: 생활코딩 전체 재크롤링

# 📌 응답 스키마
from schemas.quest_schema import (
    QuestResponse,
    QuestCompleteResponse,
)

router = APIRouter(prefix="/api/quest", tags=["Quest"])


# ===================================================================
# 📌 1) 오늘의 학습 퀘스트 — 유저별 5개 추천
# ===================================================================
@router.get("/today/{user_id}", response_model=list[QuestResponse])
def api_today_quests(user_id: int, db: Session = Depends(get_db)):
    quests = get_today_quests(db, user_id)
    return quests


# ===================================================================
# 📌 2) 퀘스트 완료 → XP 증가 + SkillNode 자동 업데이트
# ===================================================================
@router.post("/complete/{user_id}/{quest_id}", response_model=QuestCompleteResponse)
def api_complete_quest(user_id: int, quest_id: int, db: Session = Depends(get_db)):
    quest = complete_quest(db, user_id, quest_id)

    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")

    return {
        "message": "Quest completed successfully!",
        "quest": quest,
    }


# ===================================================================
# 📌 3) 전체 퀘스트 조회 — 관리자·디버깅용
# ===================================================================
@router.get("/all", response_model=list[QuestResponse])
def api_all_quests(db: Session = Depends(get_db)):
    return db.query(LearningQuest).all()


# ===================================================================
# 📌 4) 생활코딩 전체 재크롤링 → 학습 퀘스트 재생성
# ===================================================================
@router.post("/refresh")
def api_refresh_quests(db: Session = Depends(get_db)):
    """
    생활코딩 구조가 변경되거나, 전체 퀘스트를 재구축해야 할 때 사용.
    refresh_learning_quests() 내부에서 크롤링 → 파싱 → DB 갱신 수행.
    """
    count = refresh_learning_quests(db)
    return {"message": f"{count} quests refreshed"}


# ===================================================================
# 📌 5) Router Root Test
# ===================================================================
@router.get("/")
def quest_root():
    return {"message": "Quest API is running"}
