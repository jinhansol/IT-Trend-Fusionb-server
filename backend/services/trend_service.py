# backend/services/trend_service.py
# flake8: noqa
"""
🧠 Trend Service — 홈 화면 전용 (News 기반 AI 요약)
- DevDashboard와 완전히 분리됨
- 뉴스 기반 즉시 AI 요약만 제공
- TechTrend 저장 기능은 제거됨
"""

import os
import json
from datetime import datetime
from openai import OpenAI
from sqlalchemy import or_
from database.mariadb import SessionLocal
from database.models import UserProfile, NewsFeed

# 🔑 OpenAI 클라이언트
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ---------------------------------------------------------
# 🧠 GPT 요약 생성 (저장은 하지 않음)
# ---------------------------------------------------------
def generate_trend_summary(keyword: str, titles: list[str]) -> str:
    if not titles:
        return ""

    prompt = (
        f"[{keyword}] 관련 최신 뉴스 제목:\n" +
        "\n".join(titles) +
        "\n\n위 내용을 기반으로 핵심 트렌드를 3~4문장으로 요약해줘."
    )

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "당신은 최신 IT 기술 트렌드 분석 전문가입니다."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=200,
    )

    return res.choices[0].message.content.strip()


# ---------------------------------------------------------
# 🔍 사용자 관심사 기반 트렌드 추천 (저장 없음)
# ---------------------------------------------------------
async def get_trend_recommendations(user_id: int):

    db = SessionLocal()
    user = db.query(UserProfile).filter(UserProfile.id == user_id).first()

    if not user:
        db.close()
        return {"message": "❌ 사용자를 찾을 수 없습니다."}

    interests = user.interest_topics or []
    if not interests:
        db.close()
        return {"message": "ℹ 관심 키워드가 없습니다."}

    results = []

    for keyword in interests:
        news_items = (
            db.query(NewsFeed)
            .filter(
                or_(
                    NewsFeed.title.ilike(f"%{keyword}%"),
                    NewsFeed.summary.ilike(f"%{keyword}%"),
                    NewsFeed.keywords.ilike(f"%{keyword}%"),
                )
            )
            .order_by(NewsFeed.published_at.desc())
            .limit(3)
            .all()
        )

        titles = [item.title for item in news_items]
        if not titles:
            continue

        try:
            summary = generate_trend_summary(keyword, titles)
            if summary:
                results.append({"keyword": keyword, "summary": summary})
        except Exception as e:
            results.append({"keyword": keyword, "summary": f"요약 실패: {e}"})

    db.close()
    return {"recommendations": results}


# ---------------------------------------------------------
# 🔧 keyword raw 파싱
# ---------------------------------------------------------
def parse_keywords(raw):
    if not raw:
        return []

    if isinstance(raw, list):
        return [str(k).strip() for k in raw if len(str(k).strip()) > 1]

    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [str(k).strip() for k in data if len(str(k).strip()) > 1]
    except:
        pass

    return [p.strip() for p in raw.split(",") if len(p.strip()) > 1]


# ---------------------------------------------------------
# 🔍 뉴스-키워드 일치 검사
# ---------------------------------------------------------
def news_has_keyword(news: NewsFeed, keyword: str) -> bool:
    try:
        kws = parse_keywords(news.keywords)
        return keyword in kws
    except:
        return False


# ---------------------------------------------------------
# 🌐 전체 뉴스 기반 트렌드 생성 (저장 기능 제거된 버전)
# ---------------------------------------------------------
async def update_global_trends():

    print("🌐 [GLOBAL TREND] 전체 뉴스 기반 트렌드 생성 시작")

    db = SessionLocal()
    recent_news = (
        db.query(NewsFeed)
        .order_by(NewsFeed.published_at.desc())
        .limit(50)
        .all()
    )
    db.close()

    if not recent_news:
        print("❌ 최근 뉴스 없음 → 전역 트렌드 생성 불가")
        return

    all_keywords = []
    for n in recent_news:
        all_keywords.extend(parse_keywords(n.keywords))

    unique_keywords = list(dict.fromkeys(all_keywords))[:5]
    print("🌐 전역 트렌드 키워드:", unique_keywords)

    for keyword in unique_keywords:
        titles = [n.title for n in recent_news if news_has_keyword(n, keyword)]
        if not titles:
            continue

        try:
            summary = generate_trend_summary(keyword, titles)
            print(f"📌 [{keyword}] 전역 요약 생성 완료")
        except Exception as e:
            print(f"⚠️ 전역 트렌드 생성 실패({keyword}): {e}")

    print("🌐 [GLOBAL TREND] 생성 완료!")
