# backend/services/home_service.py
# flake8: noqa
"""
🏠 통합 Home Service
- 뉴스 크롤링 (News Pipeline)
- 홈 화면 데이터 구성 (Charts, Serialization)
- 트렌드 분석 (Trend Summary, Recommendation)
- 기술 사전 (Dictionary) 포함
"""

import os
import json
import time
import re
import feedparser
import requests
from bs4 import BeautifulSoup
from collections import Counter, defaultdict
from datetime import datetime
from urllib.parse import urlparse, urljoin
from dotenv import load_dotenv
from openai import OpenAI
from sqlalchemy import or_

from database.mariadb import SessionLocal
from database.models import NewsFeed, UserProfile

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ====================================================================
# 📚 Tech Dictionary (기술 분류 사전 통합)
# ====================================================================
TECH_DICTIONARY = {
    "ai": [
        "ai", "machine learning", "deep learning", "ml", "llm", "large language model",
        "gpt", "chatgpt", "rag", "bert", "t5", "neural network", "computer vision",
        "generative ai", "파인튜닝", "딥러닝", "openai", "anthropic", "claude"
    ],
    "frontend": [
        "react", "next", "vue", "svelte", "angular", "tailwind", "javascript",
        "typescript", "html", "css", "ui"
    ],
    "backend": [
        "node", "express", "nestjs", "django", "flask", "fastapi", "spring", "java",
        "go", "golang", "rust", "serverless", "microservice"
    ],
    "mobile": [
        "ios", "swift", "android", "kotlin", "react native", "flutter"
    ],
    "data": [
        "big data", "spark", "hadoop", "flink", "etl", "elt", "분산처리", "data pipeline"
    ],
    "cloud": [
        "aws", "azure", "gcp", "docker", "kubernetes", "k8s", "terraform",
        "github actions", "devops"
    ],
    "security": [
        "cybersecurity", "privacy", "encryption", "authentication", "authorization",
        "zero trust", "개인정보", "보안"
    ],
}

STOPWORDS = [
    "기술", "업계", "기업", "서비스", "출시", "발표", "개발", "도입",
    "업데이트", "시장", "관련", "효과", "업무", "산업", "분야"
]


# ====================================================================
# 1️⃣ [News Pipeline] 뉴스 크롤링 & 저장
# ====================================================================

# 20개 IT RSS 리스트
IT_FEEDS = [
    "https://www.zdnet.co.kr/Include/news.xml", "https://rss.etnews.com/Section903.xml",
    "https://www.itworld.co.kr/rss/all.xml", "https://www.ciokorea.com/rss/all.xml",
    "https://koreaittimes.com/rss/allArticle.xml", "https://www.ddaily.co.kr/news/rss/allArticle.xml",
    "https://www.bloter.net/rss", "https://www.boannews.com/media/rss.xml",
    "https://techcrunch.com/feed/", "https://www.wired.com/feed/category/business/latest/rss",
    "https://www.theverge.com/rss/index.xml", "http://feeds.arstechnica.com/arstechnica/index",
    "https://venturebeat.com/feed/", "https://feeds.infoq.com/",
    "http://rss.slashdot.org/Slashdot/slashdotMain",
]

# HTML Fallback 도메인 매핑
FALLBACK_MAP = {
    "zdnet.co.kr": "https://www.zdnet.co.kr/news/",
    "etnews.com": "https://www.etnews.com/news/",
    "itworld.co.kr": "https://www.itworld.co.kr/",
    "techcrunch.com": "https://techcrunch.com/",
    "theverge.com": "https://www.theverge.com/tech",
}

def fetch_rss(feed_url):
    parsed = feedparser.parse(feed_url)
    items = []
    for e in parsed.entries:
        title = e.get("title", "").strip()
        link = e.get("link", "").strip()
        if title and link:
            items.append({"title": title, "url": link})
    return items

def fetch_html_items(feed_url):
    domain = urlparse(feed_url).netloc.replace("www.", "")
    base_url = next((v for k, v in FALLBACK_MAP.items() if k in domain), None)
    if not base_url:
        return []

    try:
        res = requests.get(base_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        items = []
        for a in soup.find_all("a", href=True)[:20]:
            title = a.get_text(strip=True)
            link = a["href"]
            if len(title) > 10:
                full = link if link.startswith("http") else urljoin(base_url, link)
                items.append({"title": title, "url": full})
        return items
    except:
        return []

def fetch_content(url):
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        for sel in ["article", "main", "#articleBody", ".article_body", ".post-content"]:
            t = soup.select_one(sel)
            if t: return t.get_text(separator="\n").strip()
        return soup.get_text(separator="\n").strip()[:3000]
    except:
        return ""

def analyze_article(title, content):
    """GPT-4o-mini를 이용한 뉴스 요약 및 분류"""
    if len(content) < 50:
        content = f"제목 기반 요약: {title}"

    prompt = f"""
    [제목] {title}
    [본문] {content[:2000]}
    
    위 내용을 바탕으로 다음 JSON을 생성하세요:
    {{
      "summary": "한국어 3문장 요약",
      "category": "ai|cloud|security|backend|frontend|data|etc",
      "keywords": ["키워드1", "키워드2", "키워드3"]
    }}
    """
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(res.choices[0].message.content)
    except:
        return {"summary": title, "category": "etc", "keywords": ["IT"]}

def run_news_pipeline():
    print("🔥 [Home] News Pipeline Started...")
    all_items = []
    
    # 1. 수집
    for feed in IT_FEEDS:
        items = fetch_rss(feed)
        if len(items) < 3:
            items.extend(fetch_html_items(feed))
        all_items.extend(items[:3])

    # 2. 저장
    db = SessionLocal()
    count = 0
    for item in all_items:
        if db.query(NewsFeed).filter(NewsFeed.url == item["url"]).first():
            continue
            
        content = fetch_content(item["url"])
        ai_data = analyze_article(item["title"], content)
        
        news = NewsFeed(
            title=item["title"],
            summary=ai_data["summary"],
            content=content,
            category=ai_data["category"],
            keywords=json.dumps(ai_data["keywords"], ensure_ascii=False),
            url=item["url"],
            source=urlparse(item["url"]).netloc,
            published_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
        )
        db.add(news)
        count += 1
        
    try:
        db.commit()
        print(f"✅ [Home] {count} new articles saved.")
    except Exception as e:
        print(f"❌ [Home] Save Error: {e}")
        db.rollback()
    finally:
        db.close()


# ====================================================================
# 2️⃣ [Chart & Data] 홈 화면 데이터 구성
# ====================================================================

def get_date_key(date):
    return date.strftime("%Y-%m-%d")

def detect_category(text: str):
    t = text.lower()
    scores = defaultdict(int)
    for cat, kws in TECH_DICTIONARY.items():
        for kw in kws:
            if kw in t: scores[cat] += 1
    return max(scores, key=scores.get) if scores else "Other"

def extract_keywords(text: str):
    t = re.sub(r"[^a-zA-Z0-9가-힣\s]", " ", text.lower())
    words = [w for w in t.split() if len(w) > 1 and w not in STOPWORDS]
    return words

def build_charts(news_items):
    """뉴스 데이터를 분석하여 프론트엔드용 차트 데이터 생성"""
    if not news_items:
        return {"category_ratio": [], "keyword_ranking": [], "weekly_trend": []}

    cat_counter = Counter()
    kw_counter = Counter()
    daily_trend = defaultdict(lambda: defaultdict(int))

    for n in news_items:
        text = f"{n.title} {n.summary}"
        cat = detect_category(text)
        cat_counter[cat] += 1
        
        try:
            kws = json.loads(n.keywords)
            kw_counter.update(kws)
        except:
            kw_counter.update(extract_keywords(text))

        if n.published_at:
            date_key = get_date_key(n.published_at)
            daily_trend[date_key][cat] += 1

    weekly_trend = []
    for d in sorted(daily_trend.keys()):
        data = {"date": d}
        data.update(daily_trend[d])
        weekly_trend.append(data)

    return {
        "category_ratio": [{"category": k, "count": v} for k, v in cat_counter.items()],
        "keyword_ranking": [{"keyword": k, "count": v} for k, v in kw_counter.most_common(20)],
        "weekly_trend": weekly_trend,
    }

def serialize_news(item: NewsFeed):
    return {
        "id": item.id,
        "title": item.title,
        "summary": item.summary,
        "source": item.source,
        "url": item.url,
        "published_at": item.published_at,
        "category": item.category,
    }


# ====================================================================
# 3️⃣ [Trend Logic] 트렌드 추천 및 요약
# ====================================================================

async def get_trend_recommendations(user_id: int):
    """사용자 관심사 기반 트렌드 추천"""
    db = SessionLocal()
    user = db.query(UserProfile).filter(UserProfile.id == user_id).first()
    
    if not user or not user.interest_topics:
        db.close()
        return {"message": "관심사를 설정해주세요."}

    results = []
    for keyword in user.interest_topics:
        news_items = (
            db.query(NewsFeed)
            .filter(NewsFeed.title.ilike(f"%{keyword}%"))
            .order_by(NewsFeed.published_at.desc())
            .limit(3)
            .all()
        )
        
        if not news_items:
            continue
            
        titles = [n.title for n in news_items]
        prompt = f"키워드 [{keyword}] 관련 뉴스 제목들입니다:\n" + "\n".join(titles) + "\n핵심 트렌드를 2문장으로 요약해줘."
        
        try:
            res = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}]
            )
            summary = res.choices[0].message.content.strip()
            results.append({"keyword": keyword, "summary": summary})
        except:
            pass

    db.close()
    return {"recommendations": results}