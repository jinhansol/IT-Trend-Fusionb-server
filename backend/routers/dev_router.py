"""
DevDashboard 전용 라우터
- 언어 통계 / 성장률 / 트렌드 / AI 인사이트 통합 API
"""

from fastapi import APIRouter, HTTPException
from services.github_service import (
    get_top_languages,
    get_language_growth_data,
    fetch_github_trends,
    generate_ai_insights,
)

router = APIRouter(prefix="/api/dev", tags=["Dev Dashboard"])

# --------------------------------------------
# 🔹 언어별 비율 데이터
# --------------------------------------------
@router.get("/lang-stats")
def get_language_stats():
    try:
        data = get_top_languages()
        return {"languages": data, "count": len(data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"언어 통계 로드 오류: {e}")

# --------------------------------------------
# 🔹 언어별 성장 추이 (12개월)
# --------------------------------------------
@router.get("/growth")
def get_growth_trends():
    try:
        data = get_language_growth_data()
        return {"growth": data, "months": len(data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"성장 추이 로드 오류: {e}")

# --------------------------------------------
# 🔹 GitHub Trending 저장소 목록
# --------------------------------------------
@router.get("/repos")
def get_repo_trends():
    try:
        data = fetch_github_trends()
        return {"repos": data, "count": len(data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"트렌드 리포 로드 오류: {e}")

# --------------------------------------------
# 🔹 AI 인사이트 + 트렌딩 토픽
# --------------------------------------------
@router.get("/insights")
def get_ai_insight_summary():
    try:
        data = generate_ai_insights()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 인사이트 로드 오류: {e}")
