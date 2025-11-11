# flake8: noqa
"""👤 사용자 관심 키워드 라우터 — 사용자별 관심사 등록/조회/삭제"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from database.mariadb import SessionLocal
from database.models import UserProfile
from core.security import get_current_user
from services.user_service import add_interest, get_all_interests, delete_interest

router = APIRouter(prefix="/api/user", tags=["User"])

# ---------------------------------------------------------
# ⚙️ DB 세션 의존성
# ---------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------------------------------------------------
# ✅ 관심 키워드 등록
# ---------------------------------------------------------
@router.post("/add")
async def add_user_interest(
    keyword: str = Query(..., description="등록할 관심 키워드 (예: AI, React, Python 등)"),
    category: str = Query("general", description="관심사 카테고리 (예: trend, tech, career 등)"),
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    🧩 현재 로그인한 사용자의 관심 키워드 추가
    """
    try:
        result = add_interest(db=db, user=current_user, keyword=keyword, category=category)
        return {"user": current_user.username, "added": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"관심 키워드 추가 실패: {e}")

# ---------------------------------------------------------
# ✅ 관심 키워드 전체 조회
# ---------------------------------------------------------
@router.get("/list")
async def list_user_interests(
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    📋 로그인한 사용자의 관심 키워드 목록 조회
    """
    try:
        result = get_all_interests(db=db, user=current_user)
        return {"user": current_user.username, "count": len(result), "interests": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"관심 키워드 조회 실패: {e}")

# ---------------------------------------------------------
# ✅ 관심 키워드 삭제
# ---------------------------------------------------------
@router.delete("/delete/{interest_id}")
async def remove_interest(
    interest_id: int,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    🗑️ 로그인한 사용자의 특정 관심 키워드 삭제
    """
    try:
        result = delete_interest(db=db, user=current_user, interest_id=interest_id)
        return {"user": current_user.username, "deleted": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"관심 키워드 삭제 실패: {e}")
