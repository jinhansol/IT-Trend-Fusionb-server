# backend/services/news_service.py
# flake8: noqa
"""
🔥 FINAL v3 — 20개 RSS 유지 / 매체당 3개 확보 / HTML fallback 강화
🔥 Skip ZERO / 본문 부족 강제 요약 / URL 오류 완전 해결
🔥 한국어 자동 요약 안정화 / IT 필터 개선
"""

import os
import json
import time
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urlparse, urljoin
from dotenv import load_dotenv
from openai import OpenAI

from database.mariadb import SessionLocal
from database.models import NewsFeed

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# -------------------------------
# 20개 RSS (채은 요구사항 그대로)
# -------------------------------
IT_FEEDS = [
    "https://www.zdnet.co.kr/Include/news.xml",
    "https://www.zdnet.co.kr/Include/news_ai.xml",
    "https://www.zdnet.co.kr/Include/news_cloud.xml",
    "https://www.zdnet.co.kr/Include/news_security.xml",

    "https://rss.etnews.com/Section903.xml",
    "https://rss.etnews.com/AI.xml",
    "https://rss.etnews.com/Cloud.xml",
    "https://rss.etnews.com/Security.xml",
    "https://rss.etnews.com/Semicon.xml",

    "https://www.itworld.co.kr/rss/all.xml",
    "https://www.ciokorea.com/rss/all.xml",
    "https://koreaittimes.com/rss/allArticle.xml",
    "https://www.ddaily.co.kr/news/rss/allArticle.xml",
    "https://www.bloter.net/rss",
    "https://www.boannews.com/media/rss.xml",

    "https://techcrunch.com/feed/",
    "https://www.wired.com/feed/category/business/latest/rss",
    "https://www.theverge.com/rss/index.xml",
    "http://feeds.arstechnica.com/arstechnica/index",
    "https://venturebeat.com/feed/",
    "https://feeds.infoq.com/",
    "http://rss.slashdot.org/Slashdot/slashdotMain",
]

# -------------------------------
# 도메인 매핑
# -------------------------------
FALLBACK_MAP = {
    "zdnet.co.kr": "https://www.zdnet.co.kr/news/",
    "etnews.com": "https://www.etnews.com/news/",
    "itworld.co.kr": "https://www.itworld.co.kr/",
    "ciokorea.com": "https://www.ciokorea.com/",
    "koreaittimes.com": "https://koreaittimes.com/",
    "ddaily.co.kr": "https://www.ddaily.co.kr/news/",
    "bloter.net": "https://www.bloter.net/news",
    "boannews.com": "https://www.boannews.com/media/t_list.asp",

    "techcrunch.com": "https://techcrunch.com/",
    "wired.com": "https://www.wired.com/business/",
    "theverge.com": "https://www.theverge.com/tech",
    "arstechnica.com": "https://arstechnica.com/",
    "venturebeat.com": "https://venturebeat.com/category/ai/",
    "infoq.com": "https://www.infoq.com/",
    "slashdot.org": "https://slashdot.org/",
}

# -------------------------------
# RSS 파싱
# -------------------------------
def fetch_rss(feed_url):
    parsed = feedparser.parse(feed_url)
    items = []

    for e in parsed.entries:
        title = e.get("title", "").strip()
        link = e.get("link", "").strip()

        if not title or not link:
            continue

        items.append({
            "title": title,
            "url": link,
            "published": e.get("published", ""),
            "source": feed_url
        })

    return items

# -------------------------------
# HTML fallback
# -------------------------------
def fetch_html_items(feed_url):
    domain = urlparse(feed_url).netloc.replace("www.", "")

    base_url = None
    for key in FALLBACK_MAP:
        if key in domain:
            base_url = FALLBACK_MAP[key]
            break

    if not base_url:
        return []

    try:
        res = requests.get(base_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=12)
        soup = BeautifulSoup(res.text, "html.parser")

        items = []
        for a in soup.find_all("a", href=True)[:30]:
            title = a.get_text(strip=True)
            link = a["href"]

            if len(title) < 6:
                continue

            full = link if link.startswith("http") else urljoin(base_url, link)

            items.append({
                "title": title,
                "url": full,
                "published": "",
                "source": base_url,
            })

        return items

    except:
        return []

# -------------------------------
# 본문 크롤링
# -------------------------------
ARTICLE_SELECTORS = [
    "article", "main", "#articleBody", "#articleBodyContents",
    ".article_body", ".art_txt", ".post-content", "section.article"
]

def fetch_content(url):
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=12)
        soup = BeautifulSoup(res.text, "html.parser")

        for sel in ARTICLE_SELECTORS:
            t = soup.select_one(sel)
            if t:
                txt = t.get_text(separator="\n").strip()
                if len(txt) > 80:
                    return txt
        return soup.get_text(separator="\n").strip()
    except:
        return ""

# -------------------------------
# IT 필터
# -------------------------------
IT_KEYWORDS = [
    "ai", "gpt", "llm", "openai", "cloud", "security",
    "server", "backend", "frontend", "devops",
    "gpu", "cpu", "robot", "tech", "semiconductor",
    "데이터", "보안", "반도체", "개발자"
]

def is_it_related(title, content):
    text = (title + " " + content).lower()
    # 제목 기반 우선 필터(더 강하게 적용)
    for kw in IT_KEYWORDS:
        if kw.lower() in title.lower():
            return True

    # 본문 기반 보조 필터
    for kw in IT_KEYWORDS:
        if kw.lower() in text:
            return True

    return False

# -------------------------------
# AI 요약
# -------------------------------
def analyze_article(title, content):
    if len(content) < 50:
        content = f"[본문 부족] 제목만 기반으로 IT 요약 생성: {title}"

    prompt = f"""
당신은 IT 뉴스 전문 요약 시스템입니다.

[제목]
{title}

[본문]
{content[:2500]}

다음 JSON 형식으로 출력하세요:
{{
  "summary": "한국어 3~4문장 요약",
  "category": "ai|cloud|security|backend|frontend|data|robotics|etc",
  "keywords": ["키워드1", "키워드2", "키워드3"]
}}
"""

    # ------ 1st Try ------
    try:
        res = client.responses.create(
            model="gpt-4o-mini",
            input=prompt
        )
        raw = res.output_text.strip().replace("```json", "").replace("```", "")
        return json.loads(raw)
    except:
        pass

    # ------ Retry ------
    try:
        res = client.responses.create(
            model="gpt-4o-mini",
            input=prompt + "\nJSON만 출력하세요."
        )
        raw = res.output_text.strip().replace("```json", "").replace("```", "")
        return json.loads(raw)
    except:
        return {"summary": title, "category": "etc", "keywords": ["IT"]}

# -------------------------------
# DB
# -------------------------------
def exists(url, title):
    db = SessionLocal()
    row = (
        db.query(NewsFeed)
        .filter((NewsFeed.url == url) | (NewsFeed.title == title))
        .first()
    )
    db.close()
    return row

def save(item, ai, content):
    db = SessionLocal()
    try:
        news = NewsFeed(
            title=item["title"],
            summary=ai["summary"],
            content=content,
            category=ai["category"],
            keywords=json.dumps(ai["keywords"], ensure_ascii=False),
            url=item["url"],
            source=urlparse(item["url"]).netloc,   # RSS 주소가 아니라 기사 도메인만
            published_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
        )
        db.add(news)
        db.commit()
    except Exception as e:
        print("❌ DB 저장 실패:", e)
        db.rollback()
    finally:
        db.close()

# -------------------------------
# PIPELINE
# -------------------------------
def run_news_pipeline():
    print("\n🔥 NEWS PIPELINE START")

    all_items = []

    # 각 RSS에서 3개 확보
    for feed in IT_FEEDS:
        rss = fetch_rss(feed)

        if len(rss) < 3:
            html = fetch_html_items(feed)
            rss.extend(html)

        all_items.extend(rss[:3])

    print(f"📌 1차 확보: {len(all_items)}")

    # 부족하면 보충(최소 60개)
    if len(all_items) < 60:
        need = 60 - len(all_items)
        print(f"⚠️ 부족 {need}개 → fallback 추가 확보 시작")

        for feed in IT_FEEDS:
            extra = fetch_html_items(feed)
            for ex in extra:
                if need <= 0:
                    break
                all_items.append(ex)
                need -= 1
            if need <= 0:
                break

    print(f"✅ 최종 확보: {len(all_items)}개\n")

    # 분석 + 저장
    for idx, item in enumerate(all_items, start=1):
        print(f"[{idx}/{len(all_items)}] {item['title']}")

        if exists(item["url"], item["title"]):
            print(" - Skip(중복)")
            continue

        content = fetch_content(item["url"])

        if not is_it_related(item["title"], content):
            print(" - Skip(비IT)")
            continue

        ai = analyze_article(item["title"], content)
        save(item, ai, content)

        time.sleep(0.3)

