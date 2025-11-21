# services/dev_service.py
# flake8: noqa

"""
🔥 Dev Dashboard Service (A 방식 – Velog 중심 / GitHub 보조)
- 모든 스크래핑 로직을 이 파일 하나에 통합
- import 오류, 모듈 분리 문제 완전 해결
"""

import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from database.models import UserProfile, UserInterest

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html",
}



# ===========================================================
# 🔥 0) Helpers: Unique 필터
# ===========================================================
def unique(items, key):
    seen = set()
    result = []
    for x in items:
        k = x.get(key)
        if k not in seen:
            seen.add(k)
            result.append(x)
    return result



# ===========================================================
# 🔥 1) Velog Trending (HTML 크롤링)
# ===========================================================
def fetch_velog_trending_html():
    url = "https://v2.velog.io/api/posts?sort=trending"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code != 200:
            return []
        arr = res.json()
    except:
        return []

    results = []
    for p in arr[:15]:
        results.append({
            "title": p["title"],
            "username": p["user"]["username"],
            "url": f"https://velog.io/@{p['user']['username']}/{p['url_slug']}",
            "likes": p["likes"],
            "thumbnail": p.get("thumbnail"),
            "summary": p["title"],
        })
    return results



# ===========================================================
# 🔥 2) Velog Popular Tags
# ===========================================================
def fetch_velog_tags_html():
    url = "https://v2.velog.io/api/tags"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code != 200:
            return []
        arr = res.json()
    except:
        return []
    return [{"tag": t["name"], "count": t["count"]} for t in arr[:20]]



# ===========================================================
# 🔥 3) Velog By Tag
# ===========================================================
def fetch_velog_by_tag_html(tag):
    url = f"https://v2.velog.io/api/posts?tag={tag}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code != 200:
            return []
        arr = res.json()
    except:
        return []

    results = []
    for p in arr[:10]:
        results.append({
            "title": p["title"],
            "username": p["user"]["username"],
            "url": f"https://velog.io/@{p['user']['username']}/{p['url_slug']}",
            "likes": p["likes"],
            "thumbnail": p.get("thumbnail"),
            "summary": "",
        })
    return results



# ===========================================================
# 🔥 4) Velog RSS (특정 유저 기반 추천)
# ===========================================================
def fetch_velog_rss(username):
    rss_url = f"https://v2.velog.io/rss/{username}"
    try:
        res = requests.get(rss_url, headers=HEADERS, timeout=10)
        if res.status_code != 200:
            return []
        soup = BeautifulSoup(res.text, "xml")
    except:
        return []

    items = soup.find_all("item")[:10]
    results = []
    for it in items:
        results.append({
            "title": it.title.text,
            "url": it.link.text,
            "summary": it.description.text if it.description else "",
        })
    return results



# ===========================================================
# 🔥 5) GitHub Trending (HTML 크롤링)
# ===========================================================
def fetch_github_trending(language="", since="daily"):

    url = "https://github.com/trending"
    if language:
        url += f"/{language}"
    url += f"?since={since}"

    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code != 200:
            return []
        soup = BeautifulSoup(res.text, "html.parser")
    except:
        return []

    rows = soup.select("article.Box-row")[:10]
    results = []

    for it in rows:
        a = it.select_one("h2 a")
        if not a:
            continue

        full_name = a.get("href", "").strip("/")
        desc_el = it.select_one("p")
        stars_el = it.select_one("a[href*='stargazers']")

        results.append({
            "full_name": full_name,
            "url": f"https://github.com/{full_name}",
            "description": desc_el.text.strip() if desc_el else "",
            "stars": stars_el.text.strip() if stars_el else "0",
        })

    return results



# ===========================================================
# 🔥 6) Public Feed — 로그인 없이 제공
# ===========================================================
def build_public_feed():
    velog_trending = fetch_velog_trending_html()
    velog_tags = fetch_velog_tags_html()
    github_trending = fetch_github_trending("", "daily")

    return {
        "mode": "public",
        "velog_trending": velog_trending,
        "velog_tags": velog_tags,
        "github_trending": github_trending,

        # personal용 필드들 (빈값)
        "velog_recommended": [],
        "velog_interest_match": [],
        "github_recommended": [],
    }



# ===========================================================
# 🔥 7) Personal Feed — 관심사 기반 추천
# ===========================================================
def build_personal_feed(user: UserProfile, db: Session):

    # 관심 키워드 불러오기
    interests = (
        db.query(UserInterest)
        .filter(UserInterest.user_id == user.id)
        .order_by(UserInterest.id.desc())
        .all()
    )
    keywords = [i.keyword for i in interests]

    # ---------------------------
    # Velog: 태그 기반 추천
    # ---------------------------
    velog_interest_match = []
    for kw in keywords:
        posts = fetch_velog_by_tag_html(kw)
        if posts:
            velog_interest_match.extend(posts[:5])

    # ---------------------------
    # Velog: RSS 기반 유저 취향 추천 (@username)
    # ---------------------------
    velog_recommended = []
    for kw in keywords:
        if kw.startswith("@"):
            rss_posts = fetch_velog_rss(kw.replace("@", ""))
            if rss_posts:
                velog_recommended.extend(rss_posts[:5])

    # ---------------------------
    # GitHub: 관심 기술 기반 추천
    # ---------------------------
    github_recommended = []
    for kw in keywords:
        repos = fetch_github_trending(language=kw, since="daily")
        github_recommended.extend(repos[:5])

    # ---------------------------
    # 중복 제거
    # ---------------------------
    velog_interest_match = unique(velog_interest_match, "url")
    velog_recommended = unique(velog_recommended, "url")
    github_recommended = unique(github_recommended, "url")

    # ---------------------------
    # Public Trending도 포함
    # ---------------------------
    velog_trending = fetch_velog_trending_html()
    github_trending = fetch_github_trending()

    return {
        "mode": "personal",
        "interests": keywords,

        "velog_interest_match": velog_interest_match,
        "velog_recommended": velog_recommended,
        "velog_trending": velog_trending,

        "github_recommended": github_recommended,
        "github_trending": github_trending,

        "velog_tags": [],
    }
