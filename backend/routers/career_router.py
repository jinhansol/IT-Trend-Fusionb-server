# routers/career_router.py
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from services.career_service import crawl_all_jobs

router = APIRouter(tags=["Career"])  # ✅ prefix 삭제

@router.get("/jobs")
async def get_career_jobs(keyword: str = Query("Python", description="검색할 키워드 (예: AI, 데이터, React 등)")):
    """
    ✅ IT 잡 공고 통합 API
    - JobKorea (Selenium)
    - Saramin (BeautifulSoup)
    """
    try:
        print(f"\n🔍 [CareerRouter] /jobs 요청 수신 — keyword: {keyword}")
        jobs = crawl_all_jobs(keyword=keyword, max_results=5)
        return JSONResponse(content={"count": len(jobs), "results": jobs})
    except Exception as e:
        print(f"[CareerRouter Error] {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})
