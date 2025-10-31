import random
import requests
from bs4 import BeautifulSoup

# --------------------------------------------
# 언어 비율
# --------------------------------------------
def get_top_languages():
    langs = [
        {"name": "JavaScript", "usage": 34.5, "color": "#f1e05a"},
        {"name": "Python", "usage": 28.6, "color": "#3572A5"},
        {"name": "TypeScript", "usage": 11.5, "color": "#3178c6"},
        {"name": "Rust", "usage": 6.5, "color": "#dea584"},
        {"name": "Go", "usage": 5.3, "color": "#00ADD8"},
        {"name": "Other", "usage": 3.6, "color": "#999999"},
    ]
    return langs


# --------------------------------------------
# 언어별 성장 추세 (12개월)
# --------------------------------------------
def get_language_growth_data():
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    langs = ["FastAPI", "LangChain", "PyTorch", "React"]
    base_values = {l: random.randint(40, 180) for l in langs}
    data = []
    for m in months:
        entry = {"month": m}
        for l in langs:
            base_values[l] += random.randint(5, 15)
            entry[l] = base_values[l]
        data.append(entry)
    return data


# --------------------------------------------
# 오픈소스 트렌드
# --------------------------------------------
def fetch_github_trends():
    url = "https://github.com/trending?since=monthly"
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        repos = soup.select("article.Box-row")[:5]
    except Exception:
        repos = []

    results = []
    for idx, repo in enumerate(repos):
        name_tag = repo.select_one("h2 a")
        desc_tag = repo.select_one("p")
        repo_name = name_tag.text.strip() if name_tag else "Unknown"
        repo_url = "https://github.com" + name_tag["href"] if name_tag else "#"
        desc = desc_tag.text.strip() if desc_tag else "설명 없음"
        results.append(
            {
                "rank": idx + 1,
                "name": repo_name,
                "url": repo_url,
                "description": desc,
                "stars": f"{random.randint(40,200)}k",
                "growth": f"+{round(random.uniform(5,35),1)}%",
            }
        )
    return results


# --------------------------------------------
# AI 인사이트 & 트렌딩 토픽
# --------------------------------------------
def generate_ai_insights():
    insights = [
        {"title": "AI Framework Adoption", "desc": "LangChain 기반 프로젝트 28% 증가", "change": "+28.3%", "value": 32},
        {"title": "Python Dominance", "desc": "데이터/AI 분야의 Python 점유율 40% 돌파", "change": "+15.4%", "value": 40},
        {"title": "Frontend Ecosystem", "desc": "React와 Next.js 생태계 성장 지속", "change": "+18.9%", "value": 24},
        {"title": "System Efficiency", "desc": "Rust 기반 프로젝트의 성능 최적화 급상승", "change": "+22.7%", "value": 29},
    ]

    trending_topics = [
        {"topic": "#LLM", "change": "+44%"},
        {"topic": "#WebAssembly", "change": "+36%"},
        {"topic": "#Kubernetes", "change": "+28%"},
        {"topic": "#GraphQL", "change": "+18%"},
        {"topic": "#Blockchain", "change": "-12%"},
    ]

    return {"insights": insights, "topics": trending_topics}
