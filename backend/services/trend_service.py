# flake8: noqa
import os, asyncio, openai
from datetime import datetime
from database.mariadb import SessionLocal
from database.models import UserInterest, TechTrend
from services.news_service import get_latest_news

openai.api_key = os.getenv("OPENAI_API_KEY")

def save_trend_to_db(keyword, summary):
    db = SessionLocal()
    try:
        db.add(TechTrend(keyword=keyword, summary=summary, fetched_at=datetime.utcnow()))
        db.commit()
    except Exception as e:
        print(f"❌ DB 저장 실패: {e}")
        db.rollback()
    finally:
        db.close()

async def get_trend_recommendations():
    db = SessionLocal()
    interests = db.query(UserInterest).all()
    db.close()

    if not interests:
        return {"message": "저장된 관심 키워드가 없습니다."}

    results = []
    for i in [kw.keyword for kw in interests]:
        news = await asyncio.to_thread(get_latest_news, i)
        text = f"[{i}] 관련 뉴스:\n" + "\n".join([n["title"] for n in news[:3]])
        try:
            res = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": f"{text}의 핵심 트렌드를 요약해줘."}],
                max_tokens=200
            )
            summary = res.choices[0].message.content.strip()
            save_trend_to_db(i, summary)
            results.append({"keyword": i, "summary": summary})
        except Exception as e:
            results.append({"keyword": i, "summary": f"요약 실패: {e}"})
    return {"recommendations": results}

def get_ai_summary():
    db = SessionLocal()
    try:
        trends = db.query(TechTrend).order_by(TechTrend.fetched_at.desc()).limit(5).all()
        return {"insights": [{"title": t.keyword, "desc": t.summary[:80]} for t in trends]}
    finally:
        db.close()
