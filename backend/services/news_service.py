# flake8: noqa
"""🚀 실시간 뉴스 수집 + AI 요약 + 카테고리/키워드 태깅 + DB 저장 통합"""

import os
import json
import requests
import feedparser
from datetime import datetime
from urllib.parse import urljoin
from dotenv import load_dotenv
from openai import OpenAI

from database.mariadb import SessionLocal
from database.models import NewsFeed

load_dotenv()

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)


# -----------------------------
# 🔧 URL 통합 함수
# -----------------------------
def extract_url(item: dict) -> str:
    """Google/Naver 혼합 구조에서 안전하게 URL만 뽑아냄"""
    return (item.get("url") or item.get("link") or "").strip()


# -----------------------------
# 🧠 LLM 요약
# -----------------------------
def summarize_text(title: str) -> str:
    if not title:
        return ""
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": f"다음 뉴스 제목을 한국어로 1~2문장으로 간결하게 요약해줘:\n\n{title}",
                }
            ],
            temperature=0.4,
        )
        return res.choices[0].message.content.strip()
    except Exception:
        return ""


# -----------------------------
# 🧠 LLM 카테고리 / 키워드 추출
# -----------------------------
BASE_CATEGORIES = [
    "AI / ML",
    "Frontend",
    "Backend",
    "Cloud",
    "DevOps",
    "Security",
    "Data / Analytics",
    "Mobile",
    "Game",
    "Open Source",
    "Other",
]


def extract_tags_with_llm(title: str, summary: str) -> dict:
    """
    LLM으로부터 카테고리(1~2개) + 키워드(5~10개)를 JSON 형식으로 받아옴.
    출력이 코드블록/텍스트 섞여 있어도 최대한 JSON만 파싱.
    """
    try:
        prompt = f"""
다음 IT/기술 뉴스의 주제 카테고리와 대표 키워드를 추출해줘.

- category: 아래 리스트에서 1~2개만 고르고, 없으면 "Other" 사용
{BASE_CATEGORIES}

- keywords: 5~10개, 한국어/영어 섞여도 되고, 한 단어 또는 짧은 구문 위주

반드시 JSON만 출력해.
형식 예시:
{{
  "category": ["AI / ML"],
  "keywords": ["챗봇", "LLM", "오픈AI", "생성형 AI", "모델 업데이트"]
}}

뉴스 제목: {title}
뉴스 요약: {summary}
"""
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
        )
        raw = res.choices[0].message.content.strip()

        # 코드블록/텍스트 섞인 경우 대비해서 { ... } 부분만 추출
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1:
            return {"category": [], "keywords": []}

        json_str = raw[start : end + 1]
        data = json.loads(json_str)

        cats = data.get("category") or data.get("categories") or []
        kws = data.get("keywords") or []

        # 문자열 하나만 온 경우 리스트로 감싸기
        if isinstance(cats, str):
            cats = [cats]
        if isinstance(kws, str):
            kws = [kws]

        # 베이스 카테고리 외의 값은 Other로 처리
        normalized_cats = []
        for c in cats:
            c = str(c).strip()
            if not c:
                continue
            if c in BASE_CATEGORIES:
                normalized_cats.append(c)
            else:
                normalized_cats.append("Other")

        if not normalized_cats:
            normalized_cats = ["Other"]

        # 키워드는 공백 제거 + 중복 제거
        clean_kws = []
        seen = set()
        for k in kws:
            k = str(k).strip()
            if not k or k.lower() in seen:
                continue
            seen.add(k.lower())
            clean_kws.append(k)

        return {
            "category": normalized_cats,
            "keywords": clean_kws[:10],  # 최대 10개
        }

    except Exception:
        return {"category": [], "keywords": []}


# -----------------------------
# 🌍 Google 뉴스
# -----------------------------
def fetch_google_news(limit: int = 4):
    url = "https://news.google.com/rss/search?q=technology&hl=en&gl=US&ceid=US:en"
    feed = feedparser.parse(url)

    results = []
    for entry in feed.entries[:limit]:
        link = urljoin("https://news.google.com/", entry.link)

        published = (
            datetime(*entry.published_parsed[:6])
            if hasattr(entry, "published_parsed")
            else datetime.utcnow()
        )

        title = entry.title
        summary = summarize_text(title)

        tags = extract_tags_with_llm(title, summary)

        results.append(
            {
                "source": "Google News",
                "title": title,
                "summary": summary,
                "url": link,
                "published_at": published,
                "category": tags["category"],
                "keywords": tags["keywords"],
            }
        )

    return results


# -----------------------------
# 🇰🇷 Naver 뉴스
# -----------------------------
def fetch_naver_news(keyword: str = "IT", limit: int = 4):
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    params = {"query": keyword, "display": limit, "sort": "date"}

    res = requests.get(url, headers=headers, params=params, timeout=8)
    items = res.json().get("items", [])

    results = []
    for item in items:
        clean_title = item["title"].replace("<b>", "").replace("</b>", "")

        try:
            pub = datetime.strptime(item["pubDate"], "%a, %d %b %Y %H:%M:%S %z")
            published = pub.astimezone().replace(tzinfo=None)
        except Exception:
            published = datetime.utcnow()

        summary = summarize_text(clean_title)
        tags = extract_tags_with_llm(clean_title, summary)

        results.append(
            {
                "source": "Naver News",
                "title": clean_title,
                "summary": summary,
                "url": item["link"],
                "published_at": published,
                "category": tags["category"],
                "keywords": tags["keywords"],
            }
        )

    return results


# -----------------------------
# 🧩 통합 + 중복 제거
# -----------------------------
def get_latest_news(keyword: str = "IT", limit: int = 8):
    google = fetch_google_news(limit // 2)
    naver = fetch_naver_news(keyword, limit // 2)

    news = google + naver

    seen = set()
    unique = []

    for n in news:
        url = extract_url(n)
        key = (n["title"].lower(), url)

        if key not in seen:
            seen.add(key)
            unique.append(n)

    return unique


# -----------------------------
# 💾 DB 저장
# -----------------------------
def save_news_to_db(keyword: str = "IT"):
    """
    - 최신 뉴스 수집 (Google + Naver)
    - 요약 + 카테고리 + 키워드 태깅
    - news_feed 테이블에 중복 없이 저장
    """
    db = SessionLocal()

    try:
        news_items = get_latest_news(keyword)

        existing = db.query(NewsFeed.title, NewsFeed.source, NewsFeed.url).all()
        existing_set = {(t.lower(), s, u) for t, s, u in existing}

        added = 0
        for n in news_items:
            key = (n["title"].lower(), n["source"], n["url"])
            if key in existing_set:
                continue

            record = NewsFeed(
                title=n["title"],
                summary=n["summary"],
                source=n["source"],
                url=n["url"],
                published_at=n["published_at"],
                # LLM 태깅 결과를 JSON 문자열로 저장
                content=None,
                category=json.dumps(n.get("category", []), ensure_ascii=False),
                keywords=json.dumps(n.get("keywords", []), ensure_ascii=False),
            )

            db.add(record)
            added += 1

        db.commit()
        print(f"💾 {added}개 뉴스 저장됨")

    except Exception as e:
        db.rollback()
        print("❌ DB 저장 오류:", e)

    finally:
        db.close()
