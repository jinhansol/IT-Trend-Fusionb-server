# flake8: noqa
"""📰 뉴스 라우터 — AI 요약 + DB 저장 통합 버전"""
from fastapi import APIRouter, Query
from services.news_service import get_latest_news, save_news_to_db

router = APIRouter(prefix="/api/news", tags=["News"])

# -------------------------------------------------------------
# 1️⃣ 실시간 뉴스 수집 (OpenAI 요약 포함)
# -------------------------------------------------------------
@router.get("/latest")
def fetch_latest_news(
    keyword: str = Query("IT 트렌드", description="검색 키워드 (예: IT, AI 등)"),
    limit: int = Query(8, description="가져올 뉴스 개수"),
):
    """
    ✅ 최신 뉴스 가져오기 (AI 요약 포함)
    ────────────────────────────────
    • Google / Naver 뉴스 통합 수집
    • OpenAI(gpt-4o-mini)로 1~2문장 요약
    • 제목/요약/링크/출처 포함
    """
    print(f"🛰️ [/api/news/latest] 호출됨 — keyword: {keyword}, limit: {limit}")
    try:
        news = get_latest_news(keyword=keyword, limit=limit)
        return {"status": "success", "count": len(news), "news": news}
    except Exception as e:
        print(f"❌ [news_router] 오류 발생: {e}")
        return {"status": "error", "message": str(e), "news": []}


# -------------------------------------------------------------
# 2️⃣ DB 저장용 엔드포인트 (/api/news/refresh)
# -------------------------------------------------------------
@router.post("/refresh")
def refresh_news_to_db(
    keyword: str = Query("IT 트렌드", description="DB에 저장할 검색 키워드 (예: AI, 기술 등)"),
):
    """
    💾 뉴스 DB 갱신
    ────────────────────────────────
    • 최신 뉴스 수집 후 home_news 테이블에 저장
    • 기존 제목 중복은 저장하지 않음
    """
    print(f"💾 [/api/news/refresh] 호출됨 — keyword: {keyword}")
    try:
        save_news_to_db(keyword)
        return {"status": "success", "message": f"'{keyword}' 뉴스 DB 갱신 완료"}
    except Exception as e:
        print(f"❌ [news_router] DB 저장 오류: {e}")
        return {"status": "error", "message": str(e)}
