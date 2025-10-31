from fastapi import APIRouter
from services.trend_service import get_trend_recommendations

router = APIRouter()


@router.get("/top")
def fetch_trend_summary():
    """
    ✅ 기술 트렌드 상위 데이터 (홈 요약용)
    """
    try:
        trends = get_trend_recommendations()
        return {"trend_summary": trends}
    except Exception as e:
        return {"error": str(e)}
