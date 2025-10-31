# backend/services/user_service.py
from database.models import SessionLocal, UserInterest

def add_interest(keyword: str, category: str = "general"):
    """새로운 관심 키워드 추가"""
    db = SessionLocal()
    try:
        new_interest = UserInterest(keyword=keyword, category=category)
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
    finally:
        db.close()

def get_all_interests():
    """저장된 모든 관심 키워드 불러오기"""
    db = SessionLocal()
    try:
        items = db.query(UserInterest).order_by(UserInterest.created_at.desc()).all()
        return [
            {
                "id": i.id,
                "keyword": i.keyword,
                "category": i.category,
                "created_at": str(i.created_at),
            }
            for i in items
        ]
    finally:
        db.close()

def delete_interest(interest_id: int):
    """관심 키워드 삭제"""
    db = SessionLocal()
    try:
        target = db.query(UserInterest).filter(UserInterest.id == interest_id).first()
        if not target:
            return {"message": f"ID {interest_id}는 존재하지 않습니다."}
        db.delete(target)
        db.commit()
        return {"message": f"ID {interest_id}가 삭제되었습니다."}
    finally:
        db.close()
