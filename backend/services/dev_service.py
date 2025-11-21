# backend/services/dev_service.py
# flake8: noqa

"""
🔥 DevDashboard — GitHub Trending + README Raw 기반 완전 안정 버전
- GitHub API 사용 안함 → 401 완전 차단
- README는 raw.githubusercontent.com에서 직접 다운로드
- summary_kor: 제목 기반 간단 요약
- summary_detail: README 기반 3~5줄 요약
"""

import os
import json
import time
import logging
import requests
import re
from bs4 import BeautifulSoup
import feedparser
from openai import OpenAI

logger = logging.getLogger("dev_service")
logger.setLevel(logging.INFO)

# ============================================================
# 🔑 ENV
# ============================================================
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_KEY)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "text/html,application/xhtml+xml",
}


# ============================================================
# 🔐 Safe Request
# ============================================================
def safe_request(url, headers=None, timeout=10):
    try:
        res = requests.get(url, headers=headers or HEADERS, timeout=timeout)

        if res.status_code == 429:
            time.sleep(1.0)
            res = requests.get(url, headers=headers or HEADERS, timeout=timeout)

        if res.status_code != 200:
            logger.warning(f"[HTTP {res.status_code}] {url}")
            return None

        return res
    except Exception as e:
        logger.error(f"❌ 요청 실패 {url}: {e}")
        return None


# ============================================================
# JSON 파서
# ============================================================
def safe_json_parse(text):
    try:
        clean = re.sub(r"```json|```", "", text).strip()
        s = clean.find("[")
        e = clean.rfind("]") + 1
        clean = clean[s:e]
        return json.loads(clean)
    except:
        return []


# ============================================================
# 🔥 GitHub README Raw 기반 텍스트 가져오기
# ============================================================
def fetch_repo_readme(full_repo_name):
    """
    가장 안정적인 방법:
    https://raw.githubusercontent.com/{owner}/{repo}/{branch}/README.md
    API도 HTML도 아님 → 401 없음, Shadow DOM 없음.
    """
    if "/" not in full_repo_name:
        return ""

    owner, repo = full_repo_name.split("/")
    branches = ["main", "master"]

    for branch in branches:
        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/README.md"
        res = safe_request(raw_url)

        if res:
            text = res.text.strip()
            if len(text) > 20:
                return text[:6000]  # 6KB 제한

    return ""


# ============================================================
# README 요약
# ============================================================
def summarize_readme(full_name, readme):
    if not readme or len(readme) < 60:
        return ""

    prompt = f"""
아래는 GitHub 저장소 README 내용입니다.
핵심 기능·특징·목적을 한국어 3~5줄로 요약하세요.

출력(JSON):
{{
  "name": "{full_name}",
  "summary": "요약"
}}

README:
{readme}
"""

    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.2,
        )

        raw = res.choices[0].message.content
        data = safe_json_parse(raw)

        if isinstance(data, dict):
            return data.get("summary", "")

        return ""
    except Exception as e:
        logger.error("❌ README 요약 실패:", e)
        return ""


# ============================================================
# GitHub Trending 크롤링
# ============================================================
def fetch_github_trending(language: str = "", since: str = "daily"):
    base = "https://github.com/trending"
    url = f"{base}/{language}" if language else base
    url += f"?since={since}"

    res = safe_request(url)
    if not res:
        return []

    soup = BeautifulSoup(res.text, "html.parser")
    items = soup.select("article.Box-row")[:10]

    repos = []
    for it in items:
        link = it.select_one("h2 a")
        if not link:
            continue

        full_name = link.get("href", "").strip("/")

        stars_el = it.select_one("a.Link--muted[href*='stargazers']")
        stars = stars_el.text.strip() if stars_el else "0"

        repos.append({
            "full_name": full_name,
            "url": f"https://github.com/{full_name}",
            "stars": stars,
            "summary_kor": "",
            "summary_detail": "",
        })

    # 제목 요약
    repos = summarize_github_trending(repos)

    # README 요약
    for r in repos:
        readme = fetch_repo_readme(r["full_name"])
        if readme:
            r["summary_detail"] = summarize_readme(r["full_name"], readme)

    return repos


# ============================================================
# 간단 Trending 요약 (제목 기반)
# ============================================================
def summarize_github_trending(repos):
    if not repos:
        return repos

    names = [r["full_name"] for r in repos]
    joined = "\n".join([f"- {n}" for n in names])

    prompt = f"""
아래 GitHub Trending 저장소 목록의 목표를 한국어로 1~2문장씩 요약하세요.

출력(JSON 배열):
[
  {{"name": "owner/repo", "summary": "요약"}}
]

목록:
{joined}
"""

    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600,
            temperature=0.2,
        )

        raw = res.choices[0].message.content
        data = safe_json_parse(raw)

        mapping = {d["name"].lower(): d["summary"] for d in data if "name" in d}

        for r in repos:
            r["summary_kor"] = mapping.get(r["full_name"].lower(), "")

        return repos

    except Exception:
        return repos


# ============================================================
# (선택) GitHub Repo 상세 정보 (API 사용하지만 로그인 모드에서만)
# ============================================================
def fetch_github_repo_updates(full_repo_name):
    """
    Personal 모드에서만 사용됨.
    API는 토큰 있을 때만 동작, 없어도 앱이 깨지지 않게 방지.
    """
    url = f"https://api.github.com/repos/{full_repo_name}"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"token {os.getenv('GITHUB_TOKEN')}"
    }

    res = safe_request(url, headers=headers)
    if not res:
        return None

    d = res.json()
    return {
        "full_name": d.get("full_name"),
        "description": d.get("description"),
        "stars": d.get("stargazers_count"),
        "forks": d.get("forks_count"),
        "open_issues": d.get("open_issues_count"),
        "updated_at": d.get("updated_at"),
    }


# ============================================================
# Velog API
# ============================================================
def fetch_velog_popular_tags():
    url = "https://v2.velog.io/api/tags"
    res = safe_request(url)
    if not res:
        return []

    try:
        return [
            {"tag": t["name"], "count": t["count"]}
            for t in res.json()[:20]
        ]
    except:
        return []


def fetch_velog_posts_by_tag(tag):
    url = f"https://v2.velog.io/api/posts?tag={tag}"
    res = safe_request(url)
    if not res:
        return []

    try:
        arr = res.json()
    except:
        return []

    return [
        {
            "title": p["title"],
            "username": p["user"]["username"],
            "url": f"https://velog.io/@{p['user']['username']}/{p['url_slug']}",
            "likes": p["likes"],
            "thumbnail": p.get("thumbnail"),
            "summary": "",
        }
        for p in arr
    ]


def fetch_velog_trending_posts():
    url = "https://v2.velog.io/api/posts?sort=trending"
    res = safe_request(url)
    if not res:
        return []

    try:
        arr = res.json()
    except:
        return []

    return [
        {
            "title": p["title"],
            "username": p["user"]["username"],
            "url": f"https://velog.io/@{p['user']['username']}/{p['url_slug']}",
            "likes": p["likes"],
            "thumbnail": p.get("thumbnail"),
            "summary": p["title"],
        }
        for p in arr[:15]
    ]


def fetch_velog_rss(username):
    try:
        feed = feedparser.parse(f"https://v2.velog.io/rss/{username}")
        return [
            {
                "title": e.title,
                "url": e.link,
                "summary": e.summary,
                "published": e.published,
            }
            for e in feed.entries[:10]
        ]
    except:
        return []
