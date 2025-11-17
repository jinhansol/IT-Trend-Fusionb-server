# backend/services/trend_service.py
# flake8: noqa
"""
🧠 Trend Service — 사용자 관심 기반 + 전체 뉴스 기반 트렌드 요약
"""

import os
import asyncio
import json
from datetime import datetime

from openai import OpenAI
from sqlalchemy import or_
from database.mariadb import SessionLocal
from database.models import UserProfile, TechTrend, NewsFeed

# 🔑 OpenAI 클라이언트 (openai>=1.x 방식)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ---------------------------------------------------------
# 🧩 트렌드 DB 저장
# ---------------------------------------------------------
def save_trend_to_db(keyword: str, summary: str):
    db = SessionLocal()
    try:
        db.add(
            TechTrend(
                keyword=keyword,
                summary=summary,
                fetched_at=datetime.utcnow(),
            )
        )
        db.commit()
        print(f"✅ '{keyword}' 트렌드 저장 완료")
    except Exception as e:
        print(f"❌ 트렌드 저장 실패: {e}")
        db.rollback()
    finally:
        db.close()


# ---------------------------------------------------------
# 🧠 공통: GPT에게 트렌드 요약 요청
# ---------------------------------------------------------
def generate_trend_summary(keyword: str, titles: list[str]) -> str:
    if not titles:
        return ""

    text = f"[{keyword}] 관련 최신 뉴스 제목:\n" + "\n".join(titles)

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "당신은 IT 기술 트렌드 분석 전문가입니다.",
            },
            {
                "role": "user",
                "content": f"{text}\n\n위 내용을 기반으로 핵심 트렌드를 3~4문장으로 요약해줘.",
            },
        ],
        max_tokens=200,
    )

    return res.choices[0].message.content.strip()


# ---------------------------------------------------------
# 🔍 사용자 관심사 기반 추천 (API에서 호출)
# ---------------------------------------------------------
async def get_trend_recommendations(user_id: int):
    """
    특정 사용자 관심사를 기반으로 트렌드를 생성함.
    (스케줄러용 아님)
    """
    db = SessionLocal()

    # 1) 사용자 정보
    user = db.query(UserProfile).filter(UserProfile.id == user_id).first()
    if not user:
        db.close()
        return {"message": "❌ 사용자를 찾을 수 없습니다."}

    interests = user.interest_topics or []
    if not interests:
        db.close()
        return {"message": "ℹ 관심 키워드가 없습니다."}

    results = []

    # 2) 키워드별 뉴스 검색 → 최근 3개
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
                save_trend_to_db(keyword, summary)
                results.append({"keyword": keyword, "summary": summary})
        except Exception as e:
            print(f"⚠️ {keyword} 요약 실패: {e}")
            results.append(
                {"keyword": keyword, "summary": f"요약 실패: {e}"}
            )

    db.close()
    return {"recommendations": results}


# ---------------------------------------------------------
# 🔎 전역 트렌드용 키워드 파싱 유틸
#   (n.keywords가 '["Microsoft", "AI", ...]' 형태여도 잘 처리)
# ---------------------------------------------------------
def parse_keywords(raw: str) -> list[str]:
    if not raw:
        return []

    # 1) JSON 리스트로 저장된 경우
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [
                k.strip()
                for k in data
                if isinstance(k, str) and len(k.strip()) > 1
            ]
    except Exception:
        pass

    # 2) 그 외 → 쉼표 기준 파싱
    return [
        part.strip()
        for part in raw.split(",")
        if len(part.strip()) > 1
    ]


def news_has_keyword(news: NewsFeed, keyword: str) -> bool:
    if not news.keywords:
        return False

    try:
        kws = parse_keywords(news.keywords)
        return any(k == keyword for k in kws)
    except Exception:
        return keyword in news.keywords


# ---------------------------------------------------------
# 🌐 전체 뉴스 기반 트렌드 (스케줄러 전용)
# ---------------------------------------------------------
async def update_global_trends():
    """
    user_id 없이 — 전체 뉴스 DB를 기반으로 기술 트렌드를 생성하여 저장.
    (스케줄러용)
    """
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
        print("❌ 최근 뉴스가 없어 전역 트렌드를 생성할 수 없습니다.")
        return

    # 1) 최근 뉴스에서 키워드 수집
    all_keywords: list[str] = []
    for n in recent_news:
        all_keywords.extend(parse_keywords(n.keywords or ""))

    # 2) 중복 제거 후 상위 몇 개만 선택
    #    (지금은 단순히 등장 순서 기준 상위 5개)
    unique_keywords = list(dict.fromkeys(all_keywords))[:5]

    print("🌐 전역 트렌드 생성 키워드:", unique_keywords)

    # 3) 키워드별로 관련 뉴스 title 모아서 GPT 요약
    for keyword in unique_keywords:
        titles = [
            n.title for n in recent_news if news_has_keyword(n, keyword)
        ]

        if not titles:
            continue

        try:
            summary = generate_trend_summary(keyword, titles)
            if summary:
                save_trend_to_db(keyword, summary)
        except Exception as e:
            print(f"⚠️ 전역 트렌드 요약 실패({keyword}): {e}")

    print("🌐 [GLOBAL TREND] 전체 트렌드 업데이트 완료!")


# ---------------------------------------------------------
# 📊 홈 화면 인사이트
# ---------------------------------------------------------
def get_ai_summary():
    """
    최근 생성된 TechTrend 5개를 기반으로
    홈 화면 인사이트 카드에 쓸 데이터 반환
    """
    db = SessionLocal()
    try:
        trends = (
            db.query(TechTrend)
            .order_by(TechTrend.fetched_at.desc())
            .limit(5)
            .all()
        )

        return {
            "insights": [
                {
                    "title": t.keyword,
                    "desc": (
                        t.summary[:150] + "..."
                    )
                    if len(t.summary) > 150
                    else t.summary,
                }
                for t in trends
            ]
        }
    finally:
        db.close()
