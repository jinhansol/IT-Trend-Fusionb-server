# flake8: noqa
"""
🧠 Trend Service — 유저 관심사 기반 트렌드 분석 & AI 요약
(DB 구조: UserProfile.interest_topics 기준)
"""

import os, asyncio, openai
from datetime import datetime
from sqlalchemy.orm import Session
from database.mariadb import SessionLocal
from database.models import UserProfile, TechTrend
from services.news_service import get_latest_news

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
# 🔍 관심사 기반 트렌드 추천 생성
# ---------------------------------------------------------
async def get_trend_recommendations(user_id: int):
    """
    로그인한 사용자의 관심 키워드 기반으로 최신 트렌드 생성
    """
    db = SessionLocal()
    user = db.query(UserProfile).filter(UserProfile.id == user_id).first()
    db.close()

    if not user:
        return {"message": "❌ 사용자를 찾을 수 없습니다."}

    interests = user.interest_topics or []
    if not interests:
        return {"message": "ℹ️ 저장된 관심 키워드가 없습니다."}

    results = []
    for keyword in interests:
        # 최신 뉴스 가져오기
        news = await asyncio.to_thread(get_latest_news, keyword)
        titles = [n["title"] for n in news[:3]] if news else []
        text = f"[{keyword}] 관련 뉴스:\n" + "\n".join(titles)

        try:
            # GPT 기반 트렌드 요약
            res = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "당신은 기술 트렌드 전문가입니다."},
                    {"role": "user", "content": f"{text}의 핵심 트렌드를 간결하게 요약해줘."},
                ],
                max_tokens=200,
            )

            summary = res.choices[0].message.content.strip()
            save_trend_to_db(keyword, summary)
            results.append({"keyword": keyword, "summary": summary})

        except Exception as e:
            print(f"⚠️ {keyword} 요약 실패: {e}")
            results.append({"keyword": keyword, "summary": f"요약 실패: {e}"})

    return {"recommendations": results}


# ---------------------------------------------------------
# 📊 AI 요약 (최신 트렌드 요약 리스트)
# ---------------------------------------------------------
def get_ai_summary():
    """
    DB에 저장된 최근 트렌드 5개를 요약본으로 반환
    """
    db = SessionLocal()
    try:
        trends = db.query(TechTrend).order_by(TechTrend.fetched_at.desc()).limit(5).all()
        return {
            "insights": [
                {"title": t.keyword, "desc": t.summary[:120] + ("..." if len(t.summary) > 120 else "")}
                for t in trends
            ]
        }
    finally:
        db.close()
