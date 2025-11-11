# flake8: noqa
"""🧩 사용자 관심 키워드 관련 서비스 로직 (중복 방지 포함)"""

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from database.models import UserInterest

# ---------------------------------------------------------
# ✅ 관심 키워드 추가 (중복 방지 포함)
# ---------------------------------------------------------
def add_interest(db: Session, user, keyword: str, category: str = "general"):
    """현재 로그인한 사용자의 관심 키워드 추가 (중복 방지 포함)"""

    # 1️⃣ 기존 키워드 중복 여부 확인 (대소문자 무시)
    existing = (
        db.query(UserInterest)
        .filter(
            UserInterest.user_id == user.id,
            UserInterest.keyword.ilike(keyword),
        )
        .first()
    )
    if existing:
        return {
            "message": f"이미 '{keyword}' 키워드가 등록되어 있습니다.",
            "data": {
                "id": existing.id,
                "keyword": existing.keyword,
                "category": existing.category,
                "created_at": str(existing.created_at),
            },
        }

    # 2️⃣ 신규 키워드 추가
    try:
        new_interest = UserInterest(
            user_id=user.id,
            keyword=keyword,
            category=category,
        )
        db.add(new_interest)
        db.commit()
        db.refresh(new_interest)

        return {
            "message": "관심 키워드가 추가되었습니다.",
            "data": {
                "id": new_interest.id,
                "keyword": new_interest.keyword,
                "category": new_interest.category,
                "created_at": str(new_interest.created_at),
            },
        }

    except SQLAlchemyError as e:
        db.rollback()
        raise Exception(f"DB 처리 중 오류가 발생했습니다: {e}")

# ---------------------------------------------------------
# ✅ 사용자별 관심 키워드 조회
# ---------------------------------------------------------
def get_all_interests(db: Session, user):
    """로그인한 사용자의 관심 키워드 전체 조회"""
    items = (
        db.query(UserInterest)
        .filter(UserInterest.user_id == user.id)
        .order_by(UserInterest.created_at.desc())
        .all()
    )
    return [
        {
            "id": i.id,
            "keyword": i.keyword,
            "category": i.category,
            "created_at": str(i.created_at),
        }
        for i in items
    ]

# ---------------------------------------------------------
# ✅ 관심 키워드 삭제
# ---------------------------------------------------------
def delete_interest(db: Session, user, interest_id: int):
    """로그인한 사용자의 특정 관심 키워드 삭제"""
    target = (
        db.query(UserInterest)
        .filter(
            UserInterest.id == interest_id,
            UserInterest.user_id == user.id,
        )
        .first()
    )

    if not target:
        raise Exception("해당 ID의 키워드가 없거나 권한이 없습니다.")

    try:
        db.delete(target)
        db.commit()
        return {"message": f"'{target.keyword}' 키워드가 삭제되었습니다."}
    except SQLAlchemyError as e:
        db.rollback()
        raise Exception(f"삭제 중 오류가 발생했습니다: {e}")
