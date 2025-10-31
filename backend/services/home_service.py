"""DevHub 홈 피드 서비스 — 뉴스 + GitHub 트렌드 + AI 인사이트"""

from services.news_service import get_latest_news
from services.github_service import (
    fetch_github_trends,
    get_top_languages,
)


def get_home_feed(keyword: str = "AI 기술") -> dict:
    """홈 피드 통합 데이터 반환"""
    print(f"🏠 [home_service] 홈 피드 요청 — keyword: {keyword}")

    try:
        # 1️⃣ 뉴스 데이터
        news_data = get_latest_news(keyword)[:8]

        # 2️⃣ GitHub 언어 비율 + 트렌드 Repo
        github_chart = get_top_languages() or []
        repos = fetch_github_trends()[:3]

        # 3️⃣ AI 인사이트 자동 생성
        top_lang = github_chart[0]["name"] if github_chart else "Python"
        top_usage = github_chart[0]["usage"] if github_chart else "N/A"

        ai_insight = (
            f"This week's {top_lang} repositories show a "
            f"growth rate of +{top_usage}%. 🚀"
        )

        result = {
            "news": news_data,
            "insight": ai_insight,
            "github_chart": github_chart,
            "top_repos": repos,
        }

        print("✅ [home_service] 홈 피드 통합 완료")
        return result

    except Exception as err:
        print(f"❌ [home_service] 오류 발생: {err}")
        return {
            "news": [],
            "insight": "",
            "github_chart": [],
            "top_repos": [],
        }
