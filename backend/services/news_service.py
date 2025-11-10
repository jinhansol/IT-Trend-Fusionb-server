# flake8: noqa
"""🚀 실시간 뉴스 수집 서비스 (AI 요약 + DB 저장 통합 버전)"""
import os, requests, feedparser
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

from database.mariadb import SessionLocal
from database.models import NewsFeed

# -----------------------------
# 🌍 환경 변수 로드
# -----------------------------
load_dotenv()
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=OPENAI_API_KEY)

# -----------------------------
# 🧠 AI 요약 함수
# -----------------------------
def summarize_text(text: str) -> str:
    """뉴스 제목을 기반으로 1~2문장 간결 요약"""
    if not text:
        return ""
    try:
        prompt = f"다음 뉴스 제목을 한국어로 1~2문장으로 요약해줘:\n\n{text}"
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
        )
        summary = response.choices[0].message.content.strip()
        return summary
    except Exception as e:
        print(f"⚠️ 요약 실패: {e}")
        return ""

# -----------------------------
# 🌍 Google 뉴스 수집
# -----------------------------
def fetch_google_news(limit: int = 4):
    url = "https://news.google.com/rss/search?q=technology&hl=en&gl=US&ceid=US:en"
    feed = feedparser.parse(url)
    results = []

    for entry in feed.entries[:limit]:
        title = entry.title
        summary = summarize_text(title)
        results.append({
            "source": "Google News",
            "title": title,
            "summary": summary,
            "link": entry.link,
        })
    return results

# -----------------------------
# 🇰🇷 Naver 뉴스 수집
# -----------------------------
def fetch_naver_news(keyword: str = "IT 트렌드", limit: int = 4):
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    params = {"query": keyword, "display": limit, "sort": "date"}

    res = requests.get(url, headers=headers, params=params, timeout=5)
    items = res.json().get("items", [])
    results = []

    for item in items:
        clean_title = item["title"].replace("<b>", "").replace("</b>", "")
        summary = summarize_text(clean_title)
        results.append({
            "source": "Naver News",
            "title": clean_title,
            "summary": summary,
            "link": item["link"],
        })
    return results

# -----------------------------
# 🧩 뉴스 통합 및 중복 제거
# -----------------------------
def get_latest_news(keyword: str = "IT 트렌드", limit: int = 8):
    print(f"📰 [get_latest_news] '{keyword}' 뉴스 수집 + AI 요약 시작")

    google_news = fetch_google_news(limit // 2)
    naver_news = fetch_naver_news(keyword, limit // 2)
    all_news = google_news + naver_news

    # 제목 기준 중복 제거
    seen = set()
    unique_news = [n for n in all_news if not (n["title"] in seen or seen.add(n["title"]))]

    print(f"✅ [get_latest_news] {len(unique_news)}개 뉴스 반환 완료 (요약 포함)")
    return unique_news

# -----------------------------
# 💾 DB 저장 함수
# -----------------------------
def save_news_to_db(keyword: str = "IT 트렌드"):
    """뉴스 수집 → 요약 → DB 저장"""
    db = SessionLocal()
    try:
        news_items = get_latest_news(keyword)
        existing_titles = {t[0] for t in db.query(NewsFeed.title).all()}

        added = 0
        for n in news_items:
            if n["title"] in existing_titles:
                continue
            news = NewsFeed(
                title=n["title"],
                summary=n["summary"],
                source=n["source"],
                link=n["link"],
                published_at=datetime.utcnow(),
            )
            db.add(news)
            added += 1

        db.commit()
        print(f"✅ [save_news_to_db] {added}개 뉴스 저장 완료")
    except Exception as e:
        db.rollback()
        print(f"❌ [save_news_to_db] 오류: {e}")
    finally:
        db.close()
