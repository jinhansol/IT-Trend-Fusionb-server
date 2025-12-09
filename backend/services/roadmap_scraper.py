# backend/services/roadmap_scraper.py

import requests
from bs4 import BeautifulSoup
import time

BASE_URL = "https://opentutorials.org"


# -----------------------------------------------------------
# 기본 요청 함수
# -----------------------------------------------------------
def _request(url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    time.sleep(0.3)

    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.text


# -----------------------------------------------------------
# 1) 생활코딩 홈(course/1)에서 lesson URL 수집
# -----------------------------------------------------------
def find_lessons_from_root():
    """생활코딩 메인(course/1) 페이지에서 모든 강의 링크 탐색"""
    root_url = f"{BASE_URL}/course/1"
    print(f"   📘 Crawling 생활코딩 메인: {root_url}")

    html = _request(root_url)
    soup = BeautifulSoup(html, "html.parser")

    lesson_links = []

    # 생활코딩의 대부분 강의 리스트가 .lecture 안에 있음
    lecture_blocks = soup.select(".lecture a[href]")

    if lecture_blocks:
        print("   🔍 lecture 블록에서 강의 추출 중...")
        for a in lecture_blocks:
            href = a["href"]
            if "/course/" in href and href.count("/") >= 3:
                full_url = href if href.startswith("http") else BASE_URL + href
                if full_url not in lesson_links:
                    lesson_links.append(full_url)

    # lecture 블록을 못 찾으면 전체 링크에서 fallback
    if not lesson_links:
        print("   ⚠️ lecture 블록 없음 → fallback으로 전체 링크 검색")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/course/" in href and href.count("/") >= 3:
                full_url = href if href.startswith("http") else BASE_URL + href
                if full_url not in lesson_links:
                    lesson_links.append(full_url)

    print(f"   ➤ Found {len(lesson_links)} lessons from root")
    return lesson_links


# -----------------------------------------------------------
# 2) 단일 강의 페이지 스크래핑
# -----------------------------------------------------------
def scrape_opentutorials(url):
    try:
        print(f"      🕷️ Scraping: {url}", end=" ")

        html = _request(url)
        soup = BeautifulSoup(html, "html.parser")

        title_tag = soup.find("meta", property="og:title")
        desc_tag = soup.find("meta", property="og:description")

        title = title_tag["content"] if title_tag else "생활코딩 강의"
        desc = desc_tag["content"] if desc_tag else ""

        print("OK")
        return {
            "title": title.strip(),
            "description": desc[:250].strip(),
            "resource_link": url,
            "thumbnail": None,
        }

    except Exception as e:
        print(f"FAILED ({e})")
        return {
            "title": "생활코딩 강의",
            "description": "",
            "resource_link": url,
            "thumbnail": None,
        }


# -----------------------------------------------------------
# 3) 최종 → 생활코딩 라이브러리 크롤링
# -----------------------------------------------------------
def crawl_life_coding_library():
    print("🔥 생활코딩 강의 수집 시작...")

    lesson_urls = find_lessons_from_root()
    lessons = []

    # URL 너무 많아지면 200개 이하로 잘라서 안정성 유지
    LESSON_LIMIT = 200
    lesson_urls = lesson_urls[:LESSON_LIMIT]

    for url in lesson_urls:
        lessons.append(scrape_opentutorials(url))

    print(f"\n📚 Total lessons parsed: {len(lessons)}")
    return lessons
