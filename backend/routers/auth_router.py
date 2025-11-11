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
router = APIRouter(prefix="/api/auth", tags=["Auth"])

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
# ✅ 이메일 중복 확인 (Email Duplication Check)
# ==================================================
@router.get("/check-email")
def check_email(email: str, db: Session = Depends(get_db)):
    """
    클라이언트에서 이메일 중복 여부 확인용.
    /api/auth/check-email?email=example@email.com
    """
    existing_user = db.query(UserProfile).filter(UserProfile.email == email).first()
    return {"exists": bool(existing_user)}

# ==================================================
# ✅ 회원가입 (Register)
# ==================================================
@router.post("/register", response_model=AuthResponse)
def register(user: UserRegister, db: Session = Depends(get_db)):
    """
    신규 유저 등록 후 JWT 발급.
    - 이메일 중복 검사
    - 비밀번호 해싱
    - JWT 반환
    """

    # 이메일 중복 검사
    existing_user = db.query(UserProfile).filter(UserProfile.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 등록된 이메일입니다.",
        )

    # 비밀번호 해시
    hashed_pw = hash_password(user.password)

    # 유저 생성
    new_user = UserProfile(
        username=user.username,
        email=user.email,
        password_hash=hashed_pw,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # JWT 토큰 발급 (기본 만료 60분)
    access_token_expires = timedelta(minutes=60)
    access_token = create_access_token(
        data={"sub": new_user.email},
        expires_delta=access_token_expires,
    )

    return {
        "message": "회원가입이 완료되었습니다.",
        "user": new_user,  # ✅ ORM 객체 그대로 전달 가능 (orm_mode 덕분)
        "access_token": access_token,
        "token_type": "bearer",
    }

# ==================================================
# ✅ 로그인 (Login)
# ==================================================
@router.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    """
    로그인 검증 및 JWT 발급.
    - 이메일 존재 확인
    - 비밀번호 검증
    - 토큰 생성 및 반환
    """

    db_user = db.query(UserProfile).filter(UserProfile.email == user.email).first()

    # 이메일 불일치 or 비밀번호 오류
    if not db_user or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="잘못된 이메일 또는 비밀번호입니다.",
        )

    # JWT 생성 (유효기간 60분)
    access_token_expires = timedelta(minutes=60)
    access_token = create_access_token(
        data={"sub": db_user.email},
        expires_delta=access_token_expires,
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
