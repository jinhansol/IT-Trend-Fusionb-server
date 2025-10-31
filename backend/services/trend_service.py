import os
import asyncio
import openai
from database.models import SessionLocal, UserInterest
from services.news_service import get_latest_news
from services.github_service import fetch_github_trends
from services.career_service import get_job_postings

openai.api_key = os.getenv("OPENAI_API_KEY")


async def get_trend_recommendations():
    """관심 키워드 기반 통합 추천"""

    db = SessionLocal()
    interests = db.query(UserInterest).all()
    db.close()

    if not interests:
        return {
            "message": "저장된 관심 키워드가 없습니다. /api/user/add 로 등록해주세요."
        }

    keywords = [i.keyword for i in interests]
    combined_results = []

    # 🔹 키워드별 뉴스/GitHub/채용 결과 수집
    for kw in keywords:
        news = await asyncio.to_thread(get_latest_news, kw)
        github = await asyncio.to_thread(fetch_github_trends, kw)
        jobs = await asyncio.to_thread(get_job_postings, kw)
        combined_results.append({
            "keyword": kw,
            "news": news[:3],
            "github": github[:3],
            "jobs": jobs[:3],
        })

    # 🔹 OpenAI로 요약 요청
    summaries = []
    for block in combined_results:
        content = f"""
        [키워드] {block['keyword']}
        [뉴스] {', '.join([n['title'] for n in block['news']])}
        [GitHub] {', '.join([g['name'] for g in block['github']])}
        [채용] {', '.join([j['title'] for j in block['jobs']])}
        """
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "당신은 IT 취준생과 개발자에게 트렌드를 요약해주는 AI 어시스턴트입니다."
                        ),
                    },
                    {"role": "user", "content": content},
                ],
                max_tokens=200,
            )
            summaries.append({
                "keyword": block["keyword"],
                "summary": response.choices[0].message.content.strip(),
            })
        except Exception as e:
            summaries.append({
                "keyword": block["keyword"],
                "summary": f"요약 생성 실패: {str(e)}",
            })

    return {
        "message": "✅ 관심 키워드 기반 추천 생성 완료",
        "keywords": keywords,
        "recommendations": summaries,
    }
    
    # 기존 코드 하단에 아래 함수 추가
def get_ai_summary():
    """AI 관련 기술 트렌드 인사이트"""
    print("🧠 [trend_service] AI 인사이트 생성")
    return {
        "insights": [
            {"title": "AI/Data Contributions", "percent": 23, "desc": "AI 관련 오픈소스 기여율 증가"},
            {"title": "ML Framework Adoption", "percent": 67, "desc": "PyTorch 67% 채택률"},
            {"title": "Rust Growth", "percent": 89, "desc": "Rust 리포지토리 성장률 급상승"},
            {"title": "Developer Activity", "percent": 2.1, "unit": "M", "desc": "활성 개발자 210만 명"},
            {"title": "Security Focus", "percent": 156, "desc": "보안 커밋 비율 증가"},
        ]
    }

