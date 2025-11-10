# flake8: noqa
from fastapi import APIRouter
from services.trend_service import get_trend_recommendations, get_ai_summary

router = APIRouter(prefix="/api/trend", tags=["Trend"])

@router.get("/top")
async def fetch_trend_summary():
    try:
        return await get_trend_recommendations()
    except Exception as e:
        return {"error": str(e)}

@router.get("/insight")
def fetch_ai_insight():
    try:
        return get_ai_summary()
    except Exception as e:
        return {"error": str(e)}
