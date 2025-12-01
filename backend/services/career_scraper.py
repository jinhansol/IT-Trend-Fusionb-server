# backend/services/career_scraper.py

import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

# ==========================================================
# 🛡️ Anti-Detect Selenium Driver (공통 사용)
# ==========================================================
def create_driver():
    options = Options()
    options.add_argument("--headless=new") # 최신 헤드리스 모드
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    # 봇 탐지 우회 옵션 (잡코리아/사람인 공통 적용)
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    driver = webdriver.Chrome(options=options)

    # navigator.webdriver = undefined로 조작 (매우 중요)
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


# ==========================================================
# 🟢 잡코리아 (JobKorea)
# ==========================================================
def scrape_jobkorea(keyword, limit=20):
    print(f"🚀 [JobKorea] Searching: {keyword}...")
    driver = create_driver()
    results = []
    
    try:
        url = f"https://www.jobkorea.co.kr/Search/?stext={keyword}&IsInLinkAction=False"
        driver.get(url)
        time.sleep(random.uniform(2, 3)) # 랜덤 대기

        # 무한 스크롤 (데이터 확보)
        last_height = driver.execute_script("return document.body.scrollHeight")
        for _ in range(3): # 너무 많이하면 느려지므로 3~5회 적당
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        # BS4로 파싱 (Selenium보다 빠르고 안정적)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # 최신 DOM 구조 반영
        cards = soup.select("div[data-sentry-component='CardJob']")
        
        for card in cards[:limit]:
            try:
                title_el = card.select_one("span[class*='Typography_variant_size18']")
                company_el = card.select_one("span[class*='Typography_variant_size16']")
                link_el = card.select_one("a[href*='/Recruit/']")
                
                if not title_el or not link_el:
                    continue

                title = title_el.get_text(strip=True)
                company = company_el.get_text(strip=True) if company_el else "Unknown"
                link = "https://www.jobkorea.co.kr" + link_el["href"] if link_el["href"].startswith("/") else link_el["href"]
                
                # 지역 추출
                location = "서울" # 기본값
                spans = card.select("span")
                for sp in spans:
                    text = sp.get_text(strip=True)
                    if any(x in text for x in ["서울", "경기", "인천", "구", "시"]):
                        location = text
                        break

                results.append({
                    "source": "JobKorea",
                    "title": title,
                    "company": company,
                    "url": link,
                    "location": location,
                    "info": location  # 통일된 포맷
                })
            except Exception:
                continue

    except Exception as e:
        print(f"❌ [JobKorea] Error: {e}")
    finally:
        driver.quit()
    
    print(f"✅ [JobKorea] Found {len(results)} jobs.")
    return results


# ==========================================================
# 🔵 사람인 (Saramin)
# ==========================================================
def scrape_saramin(keyword, limit=20):
    print(f"🚀 [Saramin] Searching: {keyword}...")
    driver = create_driver()
    results = []

    try:
        url = f"https://www.saramin.co.kr/zf_user/search?searchword={keyword}"
        driver.get(url)
        time.sleep(random.uniform(2, 3))

        # 스크롤
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.5)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        job_cards = soup.select("div.item_recruit")
        
        for job in job_cards[:limit]:
            try:
                title_tag = job.select_one("h2.job_tit > a")
                company_tag = job.select_one("strong.corp_name > a")
                condition_tag = job.select_one("div.job_condition")

                if not title_tag:
                    continue

                title = title_tag.get_text(strip=True)
                company = company_tag.get_text(strip=True) if company_tag else "Unknown"
                link = "https://www.saramin.co.kr" + title_tag["href"]
                
                info_list = [span.get_text(strip=True) for span in condition_tag.select("span")] if condition_tag else []
                info_str = " · ".join(info_list)
                
                # 지역은 info_list의 첫 번째 요소인 경우가 많음
                location = info_list[0] if info_list else "지역 정보 없음"

                results.append({
                    "source": "Saramin",
                    "title": title,
                    "company": company,
                    "url": link,
                    "location": location,
                    "info": info_str
                })
            except Exception:
                continue

    except Exception as e:
        print(f"❌ [Saramin] Error: {e}")
    finally:
        driver.quit()

    print(f"✅ [Saramin] Found {len(results)} jobs.")
    return results


# ==========================================================
# ⚡ 통합 실행 (병렬 처리)
# ==========================================================
def crawl_career_all(keyword="Python", limit_per_site=20):
    """
    JobKorea와 Saramin을 동시에 크롤링하여 결과를 합칩니다.
    """
    print("🔥 [Career Scraper] Starting Parallel Crawling...")
    
    total_results = []
    
    # ThreadPoolExecutor를 사용하여 두 브라우저를 동시에 띄움 (시간 절약)
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_jk = executor.submit(scrape_jobkorea, keyword, limit_per_site)
        future_sr = executor.submit(scrape_saramin, keyword, limit_per_site)
        
        for future in as_completed([future_jk, future_sr]):
            try:
                data = future.result()
                if data:
                    total_results.extend(data)
            except Exception as e:
                print(f"⚠️ Worker Error: {e}")

    # 결과를 랜덤하게 섞거나, 최신순 정렬 등을 할 수 있음 (여기선 그냥 반환)
    print(f"🎉 [Career Scraper] Total {len(total_results)} jobs collected.")
    return total_results