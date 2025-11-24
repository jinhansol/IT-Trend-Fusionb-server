# services/dev_scraper.py
# flake8: noqa

"""
🔥 Selenium 기반 Dev Scraper — OKKY + Dev.to
- Cloudflare 우회
- JS 렌더링 대응
- Chromedriver 경로 필요 없음 (자동 탐색)
"""

import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import requests


# ================================================================
# 🟢 공통 Selenium Driver 생성
# ================================================================
def create_driver():
    options = Options()

    # 최신 Headless 모드
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    # Anti-Detect 설정
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # User-Agent
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/127.0.0.1 Safari/537.36"
    )

    driver = webdriver.Chrome(options=options)

    # navigator.webdriver = false
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """
        },
    )

    return driver


# ================================================================
# 🔵 OKKY 크롤링
# ================================================================
def fetch_okky_latest(limit=20):
    driver = create_driver()
    url = "https://okky.kr/articles/tech?sort=latest"

    driver.get(url)
    time.sleep(2)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    cards = soup.select("div.flex.gap-4")[:limit]

    results = []
    if not cards:
        print("❌ OKKY selector mismatch — 구조 변경 필요")
        return []

    for card in cards:
        title_el = card.select_one("h3 a")
        if not title_el:
            continue

        title = title_el.text.strip()
        url = "https://okky.kr" + title_el.get("href")
        source_id = title_el.get("href").split("/")[-1]

        author_el = card.select_one('a[href^="/users/"]')
        author = author_el.text.strip() if author_el else None

        # 조회수
        view_el = card.find("span", string=lambda x: x and "조회" in x)
        view_count = 0
        if view_el:
            strong = view_el.find("strong")
            if strong:
                view_count = int(strong.text.strip())

        time_el = card.select_one("time")
        published_at = (
            time_el["datetime"] if time_el and "datetime" in time_el.attrs else None
        )

        results.append({
            "source": "okky",
            "source_id": source_id,
            "title": title,
            "url": url,
            "author": author,
            "summary": None,
            "tags": [],
            "like_count": 0,
            "comment_count": 0,
            "view_count": view_count,
            "published_at": published_at,
        })

    return results


# ================================================================
# 🟣 Dev.to API 크롤링
# ================================================================
def fetch_devto_latest(limit=20, tag=None):
    base_url = "https://dev.to/api/articles"
    params = {"per_page": limit}

    if tag:
        params["tag"] = tag

    res = requests.get(base_url, params=params, timeout=10)
    if res.status_code != 200:
        return []

    arr = res.json()

    results = []
    for p in arr[:limit]:
        results.append({
            "source": "devto",
            "source_id": str(p["id"]),
            "title": p["title"],
            "url": p["url"],
            "author": p["user"]["username"],
            "summary": p.get("description") or p.get("title"),
            "tags": p.get("tag_list", []),
            "like_count": p.get("public_reactions_count", 0),
            "comment_count": p.get("comments_count", 0),
            "view_count": p.get("page_views_count", 0),
            "published_at": p["published_at"],
        })

    return results
