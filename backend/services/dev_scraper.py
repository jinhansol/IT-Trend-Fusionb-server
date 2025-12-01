# backend/services/dev_scraper.py
# flake8: noqa

"""
🔥 Hybrid Dev Scraper
1. OKKY: Selenium (안정성) + ThreadPool (속도)
2. Dev.to: API (안정성 & 속도) + ThreadPool (AI 요약 가속)
"""

import os
import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from dotenv import load_dotenv
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ================================================================
# 🟢 Selenium Driver (OKKY용)
# ================================================================
def create_driver():
    options = Options()
    options.add_argument("--headless=new") 
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/127.0.0.1 Safari/537.36"
    )

    driver = webdriver.Chrome(options=options)
    
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
# 🧠 AI 요약
# ================================================================
def summarize_text(title, content=None, author=None):
    content = content or ""
    prompt = f"""
    당신은 개발자 커뮤니티 글을 요약하는 전문 요약 시스템입니다.

    [제목]
    {title}

    [내용]
    {content}

    다음 규칙으로 3~4문장 한국어 요약을 생성하세요:
    - 기술적 내용을 중심으로 핵심 요약
    - 너무 장황하게 쓰지 말 것
    - 자연스러운 한국어 사용
    - HTML, 코드 블록 등 제거
    """
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return res.choices[0].message.content.strip()
    except Exception as e:
        print(f"⚠️ AI Summary Error: {e}")
        return title

# ================================================================
# 🛠️ 작업자 함수 (Worker)
# ================================================================
def process_okky_card(card_html):
    try:
        if isinstance(card_html, str):
            card = BeautifulSoup(card_html, "html.parser")
        else:
            card = card_html

        title_el = card.select_one("h3 a")
        if not title_el: return None

        title = title_el.text.strip()
        link = title_el.get("href")
        url = "https://okky.kr" + link if link.startswith("/") else link
        source_id = link.split("/")[-1]

        author_el = card.select_one('a[href^="/users/"]')
        author = author_el.text.strip() if author_el else "Anonymous"

        view_count = 0
        view_el = card.find("span", string=lambda x: x and "조회" in x)
        if view_el:
            strong = view_el.find("strong")
            if strong:
                view_count = int(strong.text.strip())

        time_el = card.select_one("time")
        published_at = time_el["datetime"] if time_el else None

        summary = summarize_text(title, content=None, author=author)

        return {
            "source": "okky",
            "source_id": source_id,
            "title": title,
            "url": url,
            "author": author,
            "summary": summary,
            "tags": [],
            "like_count": 0,
            "comment_count": 0,
            "view_count": view_count,
            "published_at": published_at,
            "crawled_at": None,
        }
    except Exception as e:
        print(f"Error processing OKKY item: {e}")
        return None

def process_devto_item(p):
    try:
        title = p["title"]
        url = p["url"]
        author = p["user"]["username"]
        description = p.get("description") or p.get("title")

        summary = summarize_text(title, content=description, author=author)

        return {
            "source": "devto",
            "source_id": str(p["id"]),
            "title": title,
            "url": url,
            "author": author,
            "summary": summary,
            "tags": p.get("tag_list", []),
            "like_count": p.get("public_reactions_count", 0),
            "comment_count": p.get("comments_count", 0),
            "view_count": p.get("page_views_count", 0),
            "published_at": p["published_at"],
            "crawled_at": None,
        }
    except Exception as e:
        print(f"Error processing Dev.to item: {e}")
        return None

# ================================================================
# 🔵 OKKY 크롤링 (함수명 수정: fetch_okky_latest -> crawl_okky)
# ================================================================
def crawl_okky(limit=20):
    print("🚀 [OKKY] Starting Selenium...")
    driver = create_driver()
    url = "https://okky.kr/articles/tech?sort=latest"

    try:
        driver.get(url)
        time.sleep(2)

        page_source = driver.page_source
        soup = BeautifulSoup(page_source, "html.parser")
        driver.quit() 
        print("✅ [OKKY] Page Source Fetched. Processing Items...")

        cards = soup.select("div.flex.gap-4")[:limit]
        card_htmls = [str(card) for card in cards]

        results = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(process_okky_card, html) for html in card_htmls]
            
            for future in as_completed(futures):
                item = future.result()
                if item:
                    results.append(item)
        
        return results

    except Exception as e:
        print(f"❌ OKKY Selenium Error: {e}")
        try: driver.quit()
        except: pass
        return []

# ================================================================
# 🟣 Dev.to (함수명 수정: fetch_devto_latest -> crawl_devto)
# ================================================================
def crawl_devto(limit=20, tag=None):
    base_url = "https://dev.to/api/articles"
    params = {"per_page": limit}
    if tag: params["tag"] = tag

    try:
        res = requests.get(base_url, params=params, timeout=10)
        if res.status_code != 200: return []

        arr = res.json()
        results = []

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(process_devto_item, p) for p in arr]
            
            for future in as_completed(futures):
                item = future.result()
                if item:
                    results.append(item)

        return results
        
    except Exception as e:
        print(f"❌ Dev.to Crawling Error: {e}")
        return []