# services/velog_scraper.py
# flake8: noqa

import re
from bs4 import BeautifulSoup
from utils.http import safe_request


BASE = "https://velog.io"


# --------------------------------------------------------------------
# 📌 HTML 기반: Velog Trending 불러오기
# --------------------------------------------------------------------
def fetch_velog_trending_html():
    """
    Velog Trending 페이지를 HTML 기반으로 파싱하는 함수.
    - 제목
    - URL
    - 요약 (본문 일부)
    """
    url = f"{BASE}/?sort=trending"

    res = safe_request(url)
    if not res:
        return []

    soup = BeautifulSoup(res.text, "html.parser")
    posts = []

    for item in soup.select("div.post-card"):
        title_tag = item.select_one("h2")
        link_tag = item.select_one("a")

        if not title_tag or not link_tag:
            continue

        url = BASE + link_tag["href"]
        title = title_tag.text.strip()

        # 요약은 잘려 있는 본문 일부
        summary_tag = item.select_one("p.preview")
        summary = summary_tag.text.strip() if summary_tag else ""

        posts.append({
            "title": title,
            "url": url,
            "summary": summary,
        })

    return posts


# --------------------------------------------------------------------
# 📌 HTML 기반: Velog 인기 태그
# --------------------------------------------------------------------
def fetch_velog_tags_html():
    """
    Velog 인기 태그 페이지에서 태그 + count 정보를 가져오는 함수.
    """
    url = f"{BASE}/tags"

    res = safe_request(url)
    if not res:
        return []

    soup = BeautifulSoup(res.text, "html.parser")
    tags = []

    for tag_item in soup.select("div.tag-item"):
        name_tag = tag_item.select_one("h4")
        count_tag = tag_item.select_one("span.count")

        if not name_tag:
            continue

        tag = name_tag.text.strip()
        count = int(re.sub(r"[^0-9]", "", count_tag.text)) if count_tag else 0

        tags.append({
            "tag": tag,
            "count": count,
        })

    return tags


# --------------------------------------------------------------------
# 📌 HTML 기반: 특정 태그 인기글
# --------------------------------------------------------------------
def fetch_velog_by_tag_html(tag: str):
    """
    Velog 특정 태그 페이지에서 인기 글 목록을 가져옴.
    """
    url = f"{BASE}/tags/{tag}"

    res = safe_request(url)
    if not res:
        return []

    soup = BeautifulSoup(res.text, "html.parser")
    posts = []

    for item in soup.select("div.post-card"):
        title_tag = item.select_one("h2")
        link_tag = item.select_one("a")

        if not title_tag or not link_tag:
            continue

        posts.append({
            "title": title_tag.text.strip(),
            "url": BASE + link_tag["href"],
            "summary": item.select_one("p.preview").text.strip()
            if item.select_one("p.preview") else "",
        })

    return posts


# --------------------------------------------------------------------
# 📌 RSS 기반: Velog 특정 유저 블로그 글
# --------------------------------------------------------------------
def fetch_velog_rss(username: str):
    """
    https://velog.io/rss/@사용자명
    → RSS 기반으로 글 목록 파싱
    """
    rss_url = f"{BASE}/rss/@{username}"

    res = safe_request(rss_url)
    if not res:
        return []

    soup = BeautifulSoup(res.text, "xml")
    items = soup.find_all("item")

    results = []

    for item in items:
        title = item.title.text if item.title else ""
        link = item.link.text if item.link else ""
        desc = item.description.text if item.description else ""

        # description에서 HTML 제거
        summary = BeautifulSoup(desc, "html.parser").text[:150]

        results.append({
            "title": title,
            "url": link,
            "summary": summary,
        })

    return results
