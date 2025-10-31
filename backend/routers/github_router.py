# backend/routers/github_router.py
from fastapi import APIRouter
from services.github_service import fetch_github_trends

router = APIRouter(tags=["GitHub"])


@router.get("/trends")
def get_github_trends(language: str = "", since: str = "daily"):
    """
    ✅ GitHub Trending 리포지토리 목록을 반환합니다.
    - language: 'python', 'javascript', 'go' 등
    - since: 'daily', 'weekly', 'monthly'
    """
    print("🔍 [github_router] /api/github/trends 호출됨")

    try:
        data = fetch_github_trends(language=language, since=since)
        print(f"✅ [github_router] 데이터 {len(data)}개 반환 완료")
        return {"count": len(data), "results": data}

    except Exception as e:
        print(f"❌ [github_router] 오류 발생: {e}")
        return {"error": str(e)}
