# backend/routers/user_router.py
# flake8: noqa
"""
👤 통합 User Router
- /api/auth      : 로그인, 회원가입
- /api/interests : 관심사 설정
- /api/user      : 사용자 정보
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database.mariadb import SessionLocal
from schemas.user_schema import UserRegister, UserLogin, AuthResponse
from services.user_service import (
    register_user,
    authenticate_user,
    check_email_exists,
    update_user_interests,
    get_user_profile_data
)

# 통합 라우터 (Prefix는 main.py에서 /api로 설정한다고 가정하거나, 여기서 하위 경로 지정)
router = APIRouter(tags=["User & Auth"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ----------------------------------------------------
# 🔐 Auth (경로: /api/auth/...)
# ----------------------------------------------------

@router.get("/auth/check-email")
def check_email_api(email: str, db: Session = Depends(get_db)):
    exists = check_email_exists(db, email)
    return {"exists": exists}

@router.post("/auth/register", response_model=AuthResponse)
def register_api(user: UserRegister, db: Session = Depends(get_db)):
    return register_user(db, user)

@router.post("/auth/login")
def login_api(user: UserLogin, db: Session = Depends(get_db)):
    return authenticate_user(db, user)


# ----------------------------------------------------
# ❤️ Interests (경로: /api/interests/...)
# ----------------------------------------------------

# 요청/응답 스키마 (간단해서 여기에 정의, 필요 시 schemas로 이동 가능)
class InterestRequest(BaseModel):
    user_id: int
    interests: list[str]
    main_focus: str

@router.post("/interests/save")
def save_interests_api(data: InterestRequest, db: Session = Depends(get_db)):
    return update_user_interests(db, data.user_id, data.interests, data.main_focus)

@router.get("/interests/{user_id}")
def get_interests_api(user_id: int, db: Session = Depends(get_db)):
    return get_user_profile_data(db, user_id)