# backend/routers/trend_router.py
# flake8: noqa
"""
📈 Trend Router — 홈 전용 API
"""

from fastapi import APIRouter, Depends, HTTPException
from core.security import get_current_user
from services.trend_service import get_trend_recommendations

router = APIRouter(prefix="/api/trend", tags=["Trend"])


# ---------------------------------------------------------
# 🔍 관심사 기반 트렌드 추천 (로그인 기반)
# ---------------------------------------------------------
@router.get("/recommend")
async def trend_recommend(current_user=Depends(get_current_user)):
    """
    사용자가 선택한 관심 분야 기반 News → AI 요약 반환
    """
    try:
        return await get_trend_recommendations(current_user.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류: {e}")

