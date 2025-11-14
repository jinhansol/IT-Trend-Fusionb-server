# flake8: noqa
"""
🔥 IT 뉴스 통합 크롤링 + AI 요약/카테고리/키워드 + DB 저장 (최종 안정화 버전 — 매체당 3개 제한)
"""

import os
import time
import json
import requests
import feedparser
from datetime import datetime
from typing import List, Dict
from urllib.parse import urlparse, urlunparse

from dotenv import load_dotenv
from bs4 import BeautifulSoup
from openai import OpenAI

from database.mariadb import SessionLocal
from database.models import NewsFeed

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ----------------------------------------------------------
# 1. RSS 소스 (국내 + 해외)
# ----------------------------------------------------------

IT_FEEDS = [
    # 🇰🇷 ZDNet
    "https://www.zdnet.co.kr/Include/news.xml",
    "https://www.zdnet.co.kr/Include/news_ai.xml",
    "https://www.zdnet.co.kr/Include/news_cloud.xml",
    "https://www.zdnet.co.kr/Include/news_security.xml",

    # 🇰🇷 ETNews
    "https://rss.etnews.com/Section903.xml",
    "https://rss.etnews.com/AI.xml",
    "https://rss.etnews.com/Cloud.xml",
    "https://rss.etnews.com/Security.xml",
    "https://rss.etnews.com/Semicon.xml",

    # 🇰🇷 기타
    "https://www.itworld.co.kr/rss/all.xml",
    "https://www.ciokorea.com/rss/all.xml",
    "https://koreaittimes.com/rss/allArticle.xml",
    "https://www.ddaily.co.kr/news/rss/allArticle.xml",
    "https://www.bloter.net/rss",
    "https://www.boannews.com/media/rss.xml",

    # 🇺🇸 해외 IT 전문
    "https://techcrunch.com/feed/",
    "https://www.wired.com/feed/category/business/latest/rss",
    "https://www.theverge.com/rss/index.xml",
    "http://feeds.arstechnica.com/arstechnica/index",
    "https://venturebeat.com/feed/",
    "https://feeds.infoq.com/",
    "http://rss.slashdot.org/Slashdot/slashdotMain",
]


# ----------------------------------------------------------
# URL 정규화 (쿼리/해시 제거)
# ----------------------------------------------------------
def normalize_url(url: str) -> str:
    try:
        p = urlparse(url)
        return urlunparse(p._replace(query="", fragment=""))
    except:
        return url


# ----------------------------------------------------------
# RSS → 매체별 기사 그룹화
# ----------------------------------------------------------
def fetch_grouped_rss() -> Dict[str, List[Dict]]:
    grouped = {}

    for feed_url in IT_FEEDS:
        parsed = feedparser.parse(feed_url)
        source = urlparse(feed_url).netloc

        if source not in grouped:
            grouped[source] = []

        for entry in parsed.entries:
            url = entry.get("link", "").strip()
            title = entry.get("title", "").strip()
            if not url or not title:
                continue

            grouped[source].append({
                "title": title,
                "url": normalize_url(url),
                "summary": entry.get("summary", "").strip(),
                "published": entry.get("published", ""),
                "source": source,
            })

    return grouped


# ----------------------------------------------------------
# 매체당 최신 N개만 선택
# ----------------------------------------------------------
MAX_PER_SOURCE = 3

def get_limited_items() -> List[Dict]:
    grouped = fetch_grouped_rss()
    limited = []

    for source, items in grouped.items():
        # published 기준으로 최신순 정렬
        sorted_items = sorted(
            items,
            key=lambda x: x["published"] or "",
            reverse=True
        )

        limited.extend(sorted_items[:MAX_PER_SOURCE])

    return limited


# ----------------------------------------------------------
# 본문 크롤링
# ----------------------------------------------------------
def clean_text(text: str) -> str:
    return "\n".join([t.strip() for t in text.split("\n") if t.strip()])


def fetch_article_content(url: str) -> str:
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=12)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        selectors = [
            "article", "#articleBody", "#articleBodyContents",
            ".article_body", ".art_txt", "section.article"
        ]

        for sel in selectors:
            node = soup.select_one(sel)
            if node:
                return clean_text(node.get_text(separator="\n"))

        return clean_text(soup.get_text(separator="\n"))

    except Exception as e:
        print(f"[ERROR] fetch_article_content: {e}")
        return ""


# ----------------------------------------------------------
# AI 요약
# ----------------------------------------------------------
def analyze_article(title: str, content: str):
    prompt = f"""
    아래는 IT 관련 뉴스 기사입니다.

    제목:
    {title}

    본문(요약용):
    {content[:4000]}

    아래 JSON 형식으로만 반환하세요:

    {{
      "summary": "...",
      "category": "AI/보안/모바일/클라우드/정책/스타트업/기타 중 하나",
      "keywords": ["...", "...", "..."]
    }}
    """
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        raw = res.choices[0].message.content
        cleaned = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned)

    except:
        return {"summary": "", "category": "기타", "keywords": ["IT"]}


# ----------------------------------------------------------
# 날짜 파싱
# ----------------------------------------------------------
def parse_published_date(raw: str):
    try:
        parsed = feedparser._parse_date(raw)
        if parsed:
            return datetime(*parsed[:6])
    except:
        pass
    return datetime.utcnow()


# ----------------------------------------------------------
# DB 중복 체크
# ----------------------------------------------------------
def exists_in_db(url, title):
    db = SessionLocal()
    exists = (
        db.query(NewsFeed)
        .filter((NewsFeed.url == url) | (NewsFeed.title == title))
        .first()
    )
    db.close()
    return exists


# ----------------------------------------------------------
# DB 저장
# ----------------------------------------------------------
def save_news(item, ai, content):
    db = SessionLocal()
    try:
        news = NewsFeed(
            title=item["title"],
            summary=ai.get("summary", ""),
            content=content,
            category=ai.get("category", "기타"),
            keywords=json.dumps(ai.get("keywords", ["IT"]), ensure_ascii=False),
            source=item["source"],
            url=item["url"],
            published_at=parse_published_date(item["published"]),
            created_at=datetime.utcnow(),
        )
        db.add(news)
        db.commit()
        print(" - 저장 완료")

    except Exception as e:
        print(f"[ERROR] DB 저장 실패: {e}")
        db.rollback()

    finally:
        db.close()


# ----------------------------------------------------------
# 메인 파이프라인
# ----------------------------------------------------------
def run_news_pipeline():
    limited_items = get_limited_items()
    print(f"[INFO] 매체당 3개 제한 → 총 {len(limited_items)}개 기사 처리")

    for idx, item in enumerate(limited_items, start=1):
        print(f"\n[{idx}/{len(limited_items)}] {item['title']}")

        if exists_in_db(item["url"], item["title"]):
            print(" - DB 중복 → Skip")
            continue

        content = fetch_article_content(item["url"])
        if len(content) < 150:
            print(" - 본문 부족 → Skip")
            continue

        ai = analyze_article(item["title"], content)
        save_news(item, ai, content)

        time.sleep(0.8)
