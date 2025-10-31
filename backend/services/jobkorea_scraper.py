from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
import time


def crawl_jobkorea(keyword="Python", max_results=5):
    """JobKorea 최신 DOM 대응 (2025.10 가상리스트 대응 + 확장 버전)"""
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--lang=ko-KR")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.7390.123 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.set_page_load_timeout(30)
    results = []

    try:
        print("[JobKorea] 페이지 접속 중...")
        driver.get("https://www.jobkorea.co.kr/recruit/joblist?menucode=duty")

        # 검색창
        search_box = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input#stext"))
        )
        search_box.clear()
        search_box.send_keys(keyword)
        time.sleep(1.2)
        search_box.send_keys(u'\ue007')  # Enter

        print("[JobKorea] 검색 실행 완료, 결과 로딩 중...")
        time.sleep(4)

        # 🔹 스크롤을 여러 번 내려서 가상 DOM을 강제로 렌더링
        last_height = driver.execute_script("return document.body.scrollHeight")
        for _ in range(4):  # 4번 정도 스크롤 (필요 시 늘릴 수 있음)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2.5)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        # React 렌더링 완료 대기
        cards = WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "div.Box_bgColor_white__1wwr54u0")
            )
        )
        print(f"[JobKorea] 감지된 공고 수: {len(cards)}")

        for card in cards[:max_results]:
            try:
                link_el = card.find_element(By.CSS_SELECTOR, "a[href*='/Recruit/GI_Read/']")
                url = link_el.get_attribute("href")

                title_el = card.find_element(By.CSS_SELECTOR, "span.Typography_variant_size18__344nw25")
                title = title_el.text.strip()

                company_el = card.find_element(By.CSS_SELECTOR, "span.Typography_variant_size16__344nw26")
                company = company_el.text.strip()

                info_elems = card.find_elements(By.CSS_SELECTOR, "span.Typography_variant_size14__344nw27")
                info_text = " · ".join([i.text.strip() for i in info_elems if i.text.strip()])

                results.append({
                    "title": title,
                    "company": company,
                    "info": info_text,
                    "url": url,
                    "source": "JobKorea"
                })
            except Exception:
                continue

    except TimeoutException:
        print("[JobKorea Error] 검색 결과 로딩 실패")
    except Exception as e:
        print("[JobKorea Fatal Error]", e)
    finally:
        driver.quit()

    print(f"[JobKorea] 수집 완료: {len(results)}개")
    return results
