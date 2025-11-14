# flake8: noqa
"""
🧠 Trend Service — 관심사 기반 + DB 뉴스 기반 트렌드 요약
"""

import os, asyncio
from datetime import datetime
import openai
from sqlalchemy.orm import Session
from sqlalchemy import or_

from database.mariadb import SessionLocal
from database.models import UserProfile, TechTrend, NewsFeed

openai.api_key = os.getenv("OPENAI_API_KEY")


# ---------------------------------------------------------
# 🧩 트렌드 DB 저장
# ---------------------------------------------------------
def save_trend_to_db(keyword: str, summary: str):
    db = SessionLocal()
    try:
        db.add(TechTrend(keyword=keyword, summary=summary, fetched_at=datetime.utcnow()))
        db.commit()
        print(f"✅ '{keyword}' 트렌드 저장 완료")
    except Exception as e:
        print(f"❌ 트렌드 저장 실패: {e}")
        db.rollback()
    finally:
        db.close()


# ---------------------------------------------------------
# 🔍 관심사 기반 트렌드 추천 (DB 기반)
# ---------------------------------------------------------
async def get_trend_recommendations(user_id: int):
    """
    관심 키워드 기반으로 DB에 저장된 최신 뉴스들을 분석하여
    트렌드 요약 생성
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

    # 2) 키워드별 뉴스 검색 → 최근 3개만
    for keyword in interests:

        # DB 뉴스 검색
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
        text = f"[{keyword}] 관련 최신 뉴스 제목:\n" + "\n".join(titles)

        # 3) GPT에게 요약 요청
        try:
            res = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "당신은 IT 기술 트렌드 분석 전문가입니다."},
                    {"role": "user", "content": f"{text}\n\n위 내용을 기반으로 핵심 트렌드를 3~4문장으로 요약해줘."},
                ],
                max_tokens=200,
            )

            summary = res.choices[0].message.content.strip()
            save_trend_to_db(keyword, summary)

            results.append({"keyword": keyword, "summary": summary})

        except Exception as e:
            print(f"⚠️ {keyword} 요약 실패: {e}")
            results.append({"keyword": keyword, "summary": f"요약 실패: {e}"})

    db.close()
    return {"recommendations": results}


# ---------------------------------------------------------
# 📊 AI 요약 (홈 화면 인사이트)
# ---------------------------------------------------------
def get_ai_summary():
    """
    최근 생성된 트렌드 5개 기반 홈 화면 인사이트
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
                    "desc": (t.summary[:150] + "...") if len(t.summary) > 150 else t.summary
                }
                for t in trends
            ]
        }

    finally:
        db.close()
