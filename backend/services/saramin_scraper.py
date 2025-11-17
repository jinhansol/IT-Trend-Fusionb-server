from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time

def crawl_saramin(keyword="Python", max_results=20):
    print("[Saramin] Selenium 크롤링 시작...")

    # ─────────────────────────────────────
    # 🔧 Selenium 설정
    # ─────────────────────────────────────
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0")

    driver = webdriver.Chrome(options=options)

    url = f"https://www.saramin.co.kr/zf_user/search?searchword={keyword}"
    driver.get(url)
    time.sleep(2)  # JS 렌더링 시간

    # 스크롤 다운 (공고 더 로드됨)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)

    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")

    driver.quit()

    # ─────────────────────────────────────
    # 🎯 공고 카드 선택
    # ─────────────────────────────────────
    job_cards = soup.select("div.item_recruit")
    print(f"[Saramin] 감지된 공고 수: {len(job_cards)}")

    results = []

    for job in job_cards[:max_results]:
        try:
            title_tag = job.select_one("h2.job_tit > a")
            company_tag = job.select_one("strong.corp_name > a")
            condition_tag = job.select_one("div.job_condition")

            title = title_tag.get_text(strip=True) if title_tag else "제목 없음"
            company = company_tag.get_text(strip=True) if company_tag else "회사명 없음"

            info = (
                " · ".join([span.get_text(strip=True) for span in condition_tag.select("span")])
                if condition_tag else ""
            )

            link = (
                "https://www.saramin.co.kr" + title_tag["href"]
                if title_tag and title_tag.has_attr("href")
                else ""
            )

            results.append({
                "title": title,
                "company": company,
                "info": info,
                "url": link,
                "source": "Saramin",
            })
        except Exception as e:
            print("[Saramin Parse Error]", e)

    print(f"[Saramin] 수집 완료: {len(results)}개")
    return results
