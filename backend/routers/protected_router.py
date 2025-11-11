# backend/routers/protected_router.py
from fastapi import APIRouter, Depends
from core.security import get_current_user
from database.models import UserProfile

router = APIRouter(prefix="/api/user", tags=["User"])

# ✅ 로그인한 사용자 정보 조회
@router.get("/me")
def read_my_profile(current_user: UserProfile = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role_type": current_user.role_type,
        "tech_stack": current_user.tech_stack,
        "interest_topics": current_user.interest_topics,
    }

# ✅ 로그인 사용자 전용 테스트 엔드포인트
@router.get("/dashboard")
def my_dashboard(current_user: UserProfile = Depends(get_current_user)):
    return {
        "message": f"환영합니다, {current_user.username}님!",
        "status": "authorized",
    }
