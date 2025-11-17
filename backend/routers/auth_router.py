from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta

from database.models import UserProfile
from database.mariadb import SessionLocal
from core.security import (
    hash_password,
    verify_password,
    create_access_token,
)
from schemas.user_schema import UserRegister, UserLogin, AuthResponse


# --------------------------------------------------
# 🔐 Auth Router
# --------------------------------------------------
# ⚠ prefix 절대 넣지 마라 → main.py에서 prefix="/api/auth" 추가됨
router = APIRouter(tags=["Auth"])


# ==================================================
# 🧩 DB 세션 의존성
# ==================================================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==================================================
# ✅ 이메일 중복 확인
# ==================================================
@router.get("/check-email")
def check_email(email: str, db: Session = Depends(get_db)):
    existing_user = db.query(UserProfile).filter(UserProfile.email == email).first()
    return {"exists": bool(existing_user)}


# ==================================================
# ✅ 회원가입
# ==================================================
@router.post("/register", response_model=AuthResponse)
def register(user: UserRegister, db: Session = Depends(get_db)):

    # 이메일 중복 검사
    existing_user = db.query(UserProfile).filter(UserProfile.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 등록된 이메일입니다.",
        )

    # 비밀번호 해시
    hashed_pw = hash_password(user.password)

    # DB 저장
    new_user = UserProfile(
        username=user.username,
        email=user.email,
        password_hash=hashed_pw,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # JWT 생성
    access_token = create_access_token(
        data={"sub": new_user.email},
        expires_delta=timedelta(minutes=60),
    )

    return {
        "message": "회원가입이 완료되었습니다.",
        "user": new_user,   # ORM 객체, schema의 orm_mode=True 덕분에 직렬화됨
        "access_token": access_token,
        "token_type": "bearer",
    }


# ==================================================
# ✅ 로그인
# ==================================================
@router.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(UserProfile).filter(UserProfile.email == user.email).first()

    # 이메일 또는 PW 오류
    if not db_user or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="잘못된 이메일 또는 비밀번호입니다.",
        )

    # JWT 생성
    access_token = create_access_token(
        data={"sub": db_user.email},
        expires_delta=timedelta(minutes=60),
    )

    return {
        "message": "로그인 성공",
        "user": {
            "id": db_user.id,
            "username": db_user.username,
            "email": db_user.email,
        },
        "access_token": access_token,
        "token_type": "bearer",
    }
