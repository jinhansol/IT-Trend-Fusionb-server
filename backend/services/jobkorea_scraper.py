# services/jobkorea_scraper.py

import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


def crawl_jobkorea(keyword="Python", max_results=10):
    print("[JobKorea] Headless + Anti-Detect 크롤링 시작...")

    options = Options()

    # ----------------------------
    # 🔥 Headless 모드 (JobKorea 우회)
    # ----------------------------
    # 최신 Headless 모드
    options.add_argument("--headless=new")

    # 자동화 감지 우회
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # user-agent 변경 (일반 Chrome처럼 보이게)
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/127.0.0.1 Safari/537.36"
    )

    # WebDriver 표시 제거
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(options=options)

    # navigator.webdriver = false 만들어 감지 방지
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

    # ----------------------------
    # 🔥 페이지 진입
    # ----------------------------
    url = f"https://www.jobkorea.co.kr/Search/?stext={keyword}&IsInLinkAction=False"
    driver.get(url)
    time.sleep(3)

    # ----------------------------
    # 🔥 무한 스크롤
    # ----------------------------
    last_height = driver.execute_script("return document.body.scrollHeight")

    for _ in range(10):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.8)

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    # ----------------------------
    # 🔥 DOM 선택 (최신 구조)
    # ----------------------------
    cards = driver.find_elements(By.CSS_SELECTOR, "div[data-sentry-component='CardJob']")
    print("[JobKorea] 감지된 공고 수:", len(cards))

    results = []

    for card in cards[:max_results]:
        try:
            title = card.find_element(By.CSS_SELECTOR,
                "span[class*='Typography_variant_size18']").text

            company = card.find_element(By.CSS_SELECTOR,
                "span[class*='Typography_variant_size16']").text

            link_el = card.find_element(By.CSS_SELECTOR, "a[href*='/Recruit/']")
            url = link_el.get_attribute("href")

            # 지역 추출
            location = ""
            spans = card.find_elements(By.CSS_SELECTOR, "span")
            for sp in spans:
                if any(x in sp.text for x in ["구", "시", "도"]):
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
