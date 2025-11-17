# services/jobkorea_scraper.py

import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


def crawl_jobkorea(keyword="Python", max_results=10):
    print("[JobKorea] 최신 React DOM 크롤링 시작...")

    options = Options()
    options.add_argument("user-agent=Mozilla/5.0")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")

    driver = webdriver.Chrome(options=options)

    url = f"https://www.jobkorea.co.kr/Search/?stext={keyword}&IsInLinkAction=False"
    driver.get(url)
    time.sleep(3)

    # -----------------------------
    # 🔥 무한 스크롤 - 데이터 강제 로딩
    # -----------------------------
    last_height = driver.execute_script("return document.body.scrollHeight")

    for _ in range(8):   # 8번 정도 스크롤하면 거의 80~120개 로딩됨
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    # -----------------------------
    # 🔥 Selenium DOM에서 직접 요소 가져오기 (BeautifulSoup 쓰면 실패함)
    # -----------------------------
    cards = driver.find_elements(By.CSS_SELECTOR, "div[data-sentry-component='CardJob']")
    print("[JobKorea] 감지된 공고 수:", len(cards))

    results = []

    for card in cards[:max_results]:
        try:
            # 제목
            title = card.find_element(By.CSS_SELECTOR,
                "span[class*='Typography_variant_size18']").text

            # 회사명
            company = card.find_element(By.CSS_SELECTOR,
                "span[class*='Typography_variant_size16']").text

            # 상세 링크
            link_el = card.find_element(By.CSS_SELECTOR, "a[href*='/Recruit/']")
            url = link_el.get_attribute("href")

            # 지역
            location = ""
            spans = card.find_elements(By.CSS_SELECTOR, "span")
            for sp in spans:
                if "구" in sp.text or "시" in sp.text or "도" in sp.text:
                    location = sp.text
                    break

            results.append({
                "title": title,
                "company": company,
                "location": location,
                "url": url,
                "source": "JobKorea",
            })

        except Exception:
            continue

    driver.quit()
    print("[JobKorea] 수집 완료:", len(results))
    return results
