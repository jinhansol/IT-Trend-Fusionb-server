"""홈 피드 서비스 (이미지 제거 버전)"""
from services.news_service import get_latest_news
from services.github_service import fetch_github_trends, get_top_languages


def get_home_feed(keyword: str = "IT 트렌드") -> dict:
    print(f"🏠 [home_service] 홈 피드 요청 — keyword: {keyword}")

    try:
        news_data = get_latest_news(keyword)
        github_chart = get_top_languages() or []
        repos = fetch_github_trends()[:3]

        top_lang = github_chart[0]["name"] if github_chart else "Python"
        top_usage = github_chart[0]["usage"] if github_chart else "0"
        ai_insight = f"이번 주 {top_lang} 저장소 성장률은 +{top_usage}%입니다. 🚀"

        print("✅ [home_service] 홈 피드 통합 완료")
        return {
            "news": news_data,
            "insight": ai_insight,
            "github_chart": github_chart,
            "top_repos": repos,
        }

    except Exception as err:
        print(f"❌ [home_service] 오류 발생: {err}")
        return {"news": [], "insight": "", "github_chart": [], "top_repos": []}
