"""홈 피드 라우터 — 뉴스 + GitHub + AI 인사이트 통합"""

from fastapi import APIRouter, Query
from services.home_service import get_home_feed

router = APIRouter(tags=["Home"])


@router.get("/feed")
def home_feed(
    keyword: str = Query("IT 트렌드", description="홈 피드용 키워드")
):
    """
    ✅ DevHub 홈 피드
    뉴스 + GitHub 트렌드 + AI 인사이트 데이터 반환
    """
    print(f"🛰️ /api/home/feed 호출됨 — keyword: {keyword}")

    try:
        data = get_home_feed(keyword)
        print("✅ [home_router] 정상 반환 완료")
        return data

    except Exception as err:
        print(f"❌ [home_router] 오류 발생: {err}")
        return {
            "error": str(err),
            "news": [],
            "insight": "",
            "github_chart": [],
            "top_repos": [],
        }
