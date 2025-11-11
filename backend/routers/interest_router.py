# flake8: noqa
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database.mariadb import SessionLocal
from database.models import UserProfile

router = APIRouter(prefix="/api/interests", tags=["Interests"])

# ✅ 요청 스키마
class InterestRequest(BaseModel):
    user_id: int
    interests: list[str]
    main_focus: str  # career / dev / insight

# ✅ 응답 스키마
class InterestResponse(BaseModel):
    user_id: int
    interests: list[str]
    main_focus: str

# ✅ 관심사 저장/수정
@router.post("/save", response_model=InterestResponse)
def save_interests(data: InterestRequest):
    db = SessionLocal()
    try:
        user = db.query(UserProfile).filter(UserProfile.id == data.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # 관심사 및 메인 포커스 저장
        user.interest_topics = data.interests
        user.main_focus = data.main_focus
        db.commit()
        db.refresh(user)

        return {
            "user_id": user.id,
            "interests": user.interest_topics,
            "main_focus": user.main_focus,
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"저장 중 오류가 발생했습니다: {e}")

    finally:
        db.close()

# ✅ 관심사 조회
@router.get("/{user_id}", response_model=InterestResponse)
def get_interests(user_id: int):
    db = SessionLocal()
    try:
        user = db.query(UserProfile).filter(UserProfile.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return {
            "user_id": user.id,
            "interests": user.interest_topics or [],
            "main_focus": user.main_focus or "career",
        }

    finally:
        db.close()
