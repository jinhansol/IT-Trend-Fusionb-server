# backend/routers/learn_router.py
from fastapi import APIRouter, Query, HTTPException
from services.learn_service import fetch_learning_resources

router = APIRouter()

@router.get("/resources")
async def get_learning_resources(keyword: str = Query(..., min_length=1)):
    """IT 학습 자료 추천 API"""
    try:
        results = fetch_learning_resources(keyword)
        if not results:
            raise HTTPException(status_code=404, detail="관련 학습 자료를 찾을 수 없습니다.")
        return {"keyword": keyword, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
