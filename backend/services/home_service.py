"""
홈 피드 서비스 (AI 기반 기술 키워드 분석)
"""

from collections import Counter, defaultdict
import re
from datetime import datetime
from database.models import NewsFeed

from services.tech_dictionary import TECH_DICTIONARY, STOPWORDS


# ---------------------------------------------------------
# 🔧 키워드 추출 + 정제
# ---------------------------------------------------------
def extract_keywords(text: str):
    if not text:
        return []

    t = text.lower()
    t = re.sub(r"[^a-zA-Z0-9가-힣 ]", " ", t)

    # 조사 제거
    t = re.sub(
        r"\b(은|는|이|가|을|를|와|과|의|에서|으로|에게|부터|까지|도)\b",
        " ",
        t
    )

    words = [w.strip() for w in t.split() if len(w) > 2]
    words = [w for w in words if w not in STOPWORDS]

    clean_list = []

    # 기술사전 단어가 포함된 경우만 허용
    for w in words:
        for kw_list in TECH_DICTIONARY.values():
            if any(k in w for k in kw_list):
                clean_list.append(w)
                break

    return clean_list


# ---------------------------------------------------------
# 🔧 기술 카테고리 점수 기반 감지
# ---------------------------------------------------------
def detect_category(text: str):
    t = text.lower()
    scores = defaultdict(int)

    for category, keywords in TECH_DICTIONARY.items():
        for kw in keywords:
            if kw in t:
                scores[category] += 1

    return max(scores, key=scores.get) if scores else "Other"


# ---------------------------------------------------------
# 🔧 ISO 주차 생성
# ---------------------------------------------------------
def get_week_key(date):
    return f"{date.year}-W{date.isocalendar().week}"


# ---------------------------------------------------------
# 🔥 차트 데이터 생성
# ---------------------------------------------------------
def build_charts(news_items):
    if not news_items:
        return {
            "category_ratio": [],
            "keyword_ranking": [],
            "weekly_trend": [],
        }

    category_counter = Counter()
    keyword_counter = Counter()
    weekly_counter = defaultdict(int)

    for n in news_items:
        text = f"{n.title} {n.summary or ''}"

        # 기술 카테고리
        category = detect_category(text)
        category_counter[category] += 1

        # 키워드
        keywords = extract_keywords(text)
        keyword_counter.update(keywords)

        # 주별 카운트
        if n.published_at:
            week_key = get_week_key(n.published_at.date())
            weekly_counter[week_key] += 1

    return {
        "category_ratio": [
            {"category": cat, "count": cnt}
            for cat, cnt in category_counter.items()
        ],
        "keyword_ranking": [
            {"keyword": kw, "count": cnt}
            for kw, cnt in keyword_counter.most_common(20)
        ],
        "weekly_trend": [
            {"week": w, "count": weekly_counter[w]}
            for w in sorted(weekly_counter.keys())
        ],
    }


# ---------------------------------------------------------
# 🔄 직렬화
# ---------------------------------------------------------
def serialize_news(item: NewsFeed):
    return {
        "id": item.id,
        "title": item.title,
        "summary": item.summary,
        "source": item.source,
        "url": item.url,
        "published_at": item.published_at,
        "created_at": item.created_at,
    }
