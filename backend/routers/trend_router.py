# flake8: noqa
"""
📈 Trend Router — 유저 관심사 기반 트렌드 추천 & 요약
"""
from fastapi import APIRouter, HTTPException
from services.trend_service import get_trend_recommendations, get_ai_summary

router = APIRouter(prefix="/api/trend", tags=["Trend"])


# ---------------------------------------------------------
# 🔍 관심사 기반 트렌드 추천 (로그인 사용자별)
# ---------------------------------------------------------
@router.get("/recommendations/{user_id}")
async def fetch_trend_recommendations(user_id: int):
    """
    특정 유저의 관심사 기반 트렌드 요약 추천
    """
    try:
        result = await get_trend_recommendations(user_id)
        if "message" in result and result["message"].startswith("❌"):
            raise HTTPException(status_code=404, detail=result["message"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류: {e}")


# ---------------------------------------------------------
# 🧠 최신 트렌드 요약 인사이트 (홈 대시보드용)
# ---------------------------------------------------------
@router.get("/insight")
def fetch_ai_insight():
    """
    최근 저장된 트렌드 요약 5개 반환
    """
    try:
        return get_ai_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류: {e}")
