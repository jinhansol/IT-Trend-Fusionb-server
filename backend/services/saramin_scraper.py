import requests
from bs4 import BeautifulSoup


def crawl_saramin(keyword="Python", max_results=5):
    """
    Saramin 정적 크롤링 버전 (검색 결과 페이지 직접 접근형)
    - Selenium 제거
    - 검색 파라미터 기반 URL 직접 요청
    """
    print("[Saramin] 정적 크롤링 시작...")

    # ✅ Saramin 검색 결과 페이지 직접 접근
    url = f"https://www.saramin.co.kr/zf_user/search?searchword={keyword}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.7390.123 Safari/537.36"
        )
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # ✅ Saramin은 검색결과가 div.item_recruit 로 구성됨
        job_cards = soup.select("div.item_recruit")
        print(f"[Saramin] 감지된 공고 수: {len(job_cards)}")

        results = []
        for job in job_cards[:max_results]:
            try:
                title_tag = job.select_one("h2.job_tit a")
                company_tag = job.select_one("strong.corp_name a")
                condition_tag = job.select_one("div.job_condition")

                title = title_tag.get_text(strip=True) if title_tag else "제목 없음"
                company = company_tag.get_text(strip=True) if company_tag else "회사명 없음"
                info = (
                    " · ".join(span.get_text(strip=True) for span in condition_tag.select("span"))
                    if condition_tag else ""
                )
                url = (
                    "https://www.saramin.co.kr" + title_tag["href"]
                    if title_tag and title_tag.has_attr("href")
                    else ""
                )

                results.append({
                    "title": title,
                    "company": company,
                    "info": info,
                    "url": url,
                    "source": "Saramin",
                })
            except Exception as e:
                print(f"[Saramin Parse Error] {e}")
                continue

        print(f"[Saramin] 수집 완료: {len(results)}개")
        return results

    except requests.exceptions.RequestException as e:
        print(f"[Saramin Network Error] {e}")
        return []
    except Exception as e:
        print(f"[Saramin Fatal Error] {e}")
        return []
