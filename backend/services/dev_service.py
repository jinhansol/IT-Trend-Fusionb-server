"""🧠 DevDashboard 서비스 로직
- GitHub 언어 통계 / 성장률 / 트렌드 / AI 인사이트 생성
"""

import random
import logging

logger = logging.getLogger("dev_service")
logger.setLevel(logging.INFO)


# ---------------------------------------------------------
# ✅ 더미 언어 통계 (실제 크롤링/DB 연결 전용)
# ---------------------------------------------------------
def get_top_languages():
    """GitHub 언어별 점유율"""
    logger.info("📊 get_top_languages() 호출됨")

    languages = [
        {"name": "Python", "usage": 29.7},
        {"name": "JavaScript", "usage": 19.5},
        {"name": "TypeScript", "usage": 15.3},
        {"name": "Java", "usage": 10.2},
        {"name": "C++", "usage": 7.8},
        {"name": "Go", "usage": 5.9},
        {"name": "Rust", "usage": 3.1},
        {"name": "Kotlin", "usage": 2.4},
    ]
    return languages


# ---------------------------------------------------------
# ✅ 성장률 (12개월 데이터)
# ---------------------------------------------------------
def get_language_growth_data():
    """언어별 월별 성장률 (더미 데이터)"""
    logger.info("📈 get_language_growth_data() 호출됨")

    months = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    ]
    growth = []
    for m in months:
        growth.append({
            "month": m,
            "Python": round(random.uniform(1.0, 8.0), 2),
            "JavaScript": round(random.uniform(0.5, 7.0), 2),
            "TypeScript": round(random.uniform(0.5, 6.0), 2),
            "Rust": round(random.uniform(-1.0, 5.0), 2),
            "Go": round(random.uniform(-1.0, 4.0), 2),
        })
    return growth


# ---------------------------------------------------------
# ✅ GitHub 트렌드 레포
# ---------------------------------------------------------
def fetch_github_trends():
    """GitHub 트렌드 레포지토리 (샘플 데이터)"""
    logger.info("🔥 fetch_github_trends() 호출됨")

    repos = [
        {
            "full_name": "openai/gpt-engine",
            "description": "Large-scale AI reasoning engine.",
            "stars": 18.7,
            "growth": "+12%",
        },
        {
            "full_name": "microsoft/TypeChat",
            "description": "Type-safe natural language interfaces.",
            "stars": 11.2,
            "growth": "+9%",
        },
        {
            "full_name": "vercel/next.js",
            "description": "The React framework for production.",
            "stars": 113.0,
            "growth": "+6%",
        },
        {
            "full_name": "tiangolo/fastapi",
            "description": "FastAPI: modern Python web framework.",
            "stars": 72.3,
            "growth": "+7%",
        },
    ]
    return repos


# ---------------------------------------------------------
# ✅ AI 인사이트 생성
# ---------------------------------------------------------
def generate_ai_insights():
    """AI 기반 요약 인사이트 (샘플 문구)"""
    logger.info("🤖 generate_ai_insights() 호출됨")

    insights = [
        {"title": "Python retains its lead", "desc": "Data science and AI libraries remain dominant.", "change": "+4.5%", "color": "#3572A5"},
        {"title": "Rust adoption rising", "desc": "Increased use in system-level applications.", "change": "+2.8%", "color": "#DE6E48"},
        {"title": "TypeScript gains momentum", "desc": "Front-end and serverless frameworks drive growth.", "change": "+3.1%", "color": "#3178C6"},
    ]
    topics = [
        {"tag": "AI", "rate": "+7.8%", "color": "text-green-500"},
        {"tag": "Rust", "rate": "+5.1%", "color": "text-green-500"},
        {"tag": "React", "rate": "-1.2%", "color": "text-red-500"},
    ]
    return {"insights": insights, "topics": topics}


# ---------------------------------------------------------
# ✅ 통합 피드 (DB 비었을 때 호출됨)
# ---------------------------------------------------------
def get_dev_feed():
    """
    DevDashboard 통합 피드용 — DB 비어 있을 때 크롤링 기반 대체 데이터 제공
    """
    logger.info("🚀 get_dev_feed() 호출됨")

    try:
        languages = get_top_languages()
        growth = get_language_growth_data()
        repos = fetch_github_trends()
        ai_insights = generate_ai_insights()

        feed = {
            "trends": languages,
            "growth": growth,
            "repos": repos,
            "ai_insights": ai_insights,
        }

        logger.info("✅ get_dev_feed() 통합 완료")
        return feed

    except Exception as e:
        logger.error(f"❌ [get_dev_feed] 오류 발생: {e}", exc_info=True)
        return {
            "trends": [],
            "growth": [],
            "repos": [],
            "ai_insights": {},
        }
