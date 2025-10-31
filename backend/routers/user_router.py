# backend/routers/user_router.py
from fastapi import APIRouter, Query
from services.user_service import add_interest, get_all_interests, delete_interest

router = APIRouter()

@router.post("/add")
async def add_user_interest(keyword: str = Query(...), category: str = Query("general")):
    """관심 키워드 저장"""
    return add_interest(keyword, category)

@router.get("/list")
async def list_user_interests():
    """모든 관심 키워드 조회"""
    return get_all_interests()

@router.delete("/delete/{interest_id}")
async def remove_interest(interest_id: int):
    """특정 관심 키워드 삭제"""
    return delete_interest(interest_id)
