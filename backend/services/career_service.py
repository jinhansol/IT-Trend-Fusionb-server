from services.jobkorea_scraper import crawl_jobkorea
from services.saramin_scraper import crawl_saramin


def crawl_all_jobs(keyword: str = "Python", max_results: int = 5):
    """
    ✅ JobKorea + Saramin 통합 채용 데이터
    """
    print(f"🔍 [career_service] 통합 크롤링 — keyword: {keyword}")

    results = []
    results.extend(crawl_jobkorea(keyword, max_results=max_results))
    results.extend(crawl_saramin(keyword, max_results=max_results))

    return results[:max_results]


# ✅ 하위호환용 별칭 (이전 코드 지원용)
get_job_postings = crawl_all_jobs
