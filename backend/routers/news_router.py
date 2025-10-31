"""뉴스 관련 라우터"""

from fastapi import APIRouter, Query
from services.news_service import get_latest_news

router = APIRouter(tags=["News"])


@router.get("/feed")
def get_news_feed(keyword: str = Query("IT 트렌드", description="검색 키워드")):
    """Google + Naver 통합 뉴스 피드 반환"""
    print(f"📰 [news_router] 뉴스 피드 요청 — keyword: {keyword}")

    try:
        data = get_latest_news(keyword)
        return {"count": len(data), "results": data}

    except Exception as err:
        print(f"❌ [news_router] 오류 발생: {err}")
        return {"count": 0, "results": [], "error": str(err)}
