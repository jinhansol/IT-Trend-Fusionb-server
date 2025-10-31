# backend/services/learn_service.py
import requests
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv

load_dotenv()

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

def fetch_learning_resources(keyword: str, max_results: int = 8):
    """Naver API 기반 학습 자료 추천"""
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        raise ValueError("⚠️ Naver API 환경변수가 설정되지 않았습니다.")

    url = "https://openapi.naver.com/v1/search/blog.json"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    params = {"query": f"{keyword} 개발 튜토리얼", "display": max_results, "sort": "sim"}

    try:
        res = requests.get(url, headers=headers, params=params, timeout=10)
        res.raise_for_status()
        data = res.json()

        resources = []
        for item in data.get("items", []):
            title = BeautifulSoup(item["title"], "html.parser").get_text()
            desc = BeautifulSoup(item["description"], "html.parser").get_text()
            link = item["link"]

            resources.append({
                "title": title.strip(),
                "summary": desc.strip(),
                "url": link,
                "source": "Naver Blog",
            })

        return resources

    except Exception as e:
        print("[LearnService Error]", e)
        return []
