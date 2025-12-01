# backend/services/user_service.py
# flake8: noqa
"""
👤 User Service
- 회원가입, 로그인, 중복 체크 (Auth)
- 관심사 저장 및 조회 (Interests) -> 자동 분류 저장 기능 추가됨!
"""

from datetime import timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import json

from database.models import UserProfile
from core.security import (
    hash_password,
    verify_password,
    create_access_token,
)

# ----------------------------------------------------------
# 🧠 스마트 분류기: 기술 vs 분야 자동 구분
# ----------------------------------------------------------
TECH_KEYWORDS = {
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust", "kotlin", "swift",
    "react", "vue", "vue.js", "next.js", "node.js", "spring", "spring boot", "django", "flask", "fastapi",
    "tensorflow", "pytorch", "pandas", "numpy", "scikit-learn",
    "docker", "kubernetes", "k8s", "aws", "azure", "gcp", "linux", "git",
    "mysql", "postgresql", "mongodb", "redis", "elasticsearch", "flutter", "react native"
}

def classify_keywords(selected_list):
    """
    입력받은 리스트를 Tech(기술)와 Interest(분야)로 분리합니다.
    """
    tech_stack = []
    interest_topics = []

    for item in selected_list:
        # 소문자로 변환해서 비교
        lower_item = item.lower()
        
        # 1. 기술 키워드에 포함되면 Tech Stack으로
        if lower_item in TECH_KEYWORDS:
            tech_stack.append(item)
        # 2. 아니면 관심 분야(Interest)로 (ex: Frontend, AI Ethics, Startups)
        else:
            interest_topics.append(item)
            
    return tech_stack, interest_topics


# ==========================================================
# 🔐 인증 (Auth) 로직
# ==========================================================

def check_email_exists(db: Session, email: str) -> bool:
    user = db.query(UserProfile).filter(UserProfile.email == email).first()
    return bool(user)

def register_user(db: Session, user_data):
    if check_email_exists(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 등록된 이메일입니다.",
        )

    hashed_pw = hash_password(user_data.password)
    new_user = UserProfile(
        username=user_data.username,
        email=user_data.email,
        password_hash=hashed_pw,
        main_focus=user_data.main_focus
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # ✅ [수정] 토큰 생성 시 'id' 필드 추가
    token = create_access_token(
        data={
            "sub": new_user.email,
            "id": new_user.id  # 여기 추가됨!
        },
        expires_delta=timedelta(minutes=60)
    )
    
    return {
        "message": "회원가입 완료",
        "user": new_user,
        "access_token": token,
        "token_type": "bearer"
    }

def authenticate_user(db: Session, login_data):
    user = db.query(UserProfile).filter(UserProfile.email == login_data.email).first()
    
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="잘못된 이메일 또는 비밀번호입니다.",
        )
    
    # ✅ [수정] 토큰 생성 시 'id' 필드 추가
    token = create_access_token(
        data={
            "sub": user.email,
            "id": user.id  # 여기 추가됨!
        },
        expires_delta=timedelta(minutes=60)
    )
    
    return {
        "message": "로그인 성공",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "main_focus": user.main_focus,
            "interest_topics": user.interest_topics,
            "tech_stack": user.tech_stack  # Tech Stack도 반환
        },
        "access_token": token,
        "token_type": "bearer"
    }


# ==========================================================
# ❤️ 관심사 (Interests) 로직 (업그레이드 완료!)
# ==========================================================

def update_user_interests(db: Session, user_id: int, interests: list, main_focus: str):
    user = db.query(UserProfile).filter(UserProfile.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # ✅ 여기서 자동 분류 실행!
    techs, topics = classify_keywords(interests)

    # DB에 분리해서 저장 (JSON 직렬화 불필요, SQLAlchemy가 리스트 처리함)
    user.tech_stack = techs
    user.interest_topics = topics
    user.main_focus = main_focus
    
    db.commit()
    db.refresh(user)
    
    print(f"✅ [User Update] ID:{user_id} | Tech: {techs} | Interest: {topics}")
    
    # 반환할 때는 프론트엔드가 헷갈리지 않게 합쳐서 줍니다 (선택사항)
    return {
        "user_id": user.id,
        "interests": techs + topics, # 프론트엔드 호환용 (전체 리스트)
        "main_focus": user.main_focus,
        "tech_stack": techs,         # 디버깅용
        "interest_topics": topics    # 디버깅용
    }

def get_user_profile_data(db: Session, user_id: int):
    user = db.query(UserProfile).filter(UserProfile.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 조회 시에는 두 컬럼을 합쳐서 반환 (프론트엔드 'selected' 상태 복구용)
    tech = user.tech_stack if isinstance(user.tech_stack, list) else []
    interest = user.interest_topics if isinstance(user.interest_topics, list) else []
    
    return {
        "user_id": user.id,
        "interests": tech + interest, # 합쳐서 반환
        "main_focus": user.main_focus or "Career"
    }