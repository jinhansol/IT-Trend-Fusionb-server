"""
AI 통합 뉴스 수집 서비스 (양쪽 디버깅 활성화 버전)
────────────────────────────
✅ Google 뉴스: 리디렉션 + OG 이미지 + 상세 로그
✅ Naver 뉴스: OG 이미지 시도 + 썸네일 추출 로그
✅ 디버깅 레벨 확장: 각 단계별 출력
"""

import os
import requests
import feedparser
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI

# ────────────────────────────────────────────────
# 🌿 환경 변수 로드
# ────────────────────────────────────────────────
load_dotenv()
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# ────────────────────────────────────────────────
# 🧩 공통: OpenGraph 이미지 추출
# ────────────────────────────────────────────────
def get_news_thumbnail(url: str) -> str:
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=6)
        if not res.ok:
            print(f" ❌ [썸네일] 요청 실패 ({res.status_code}) → {url}")
            return ""

        soup = BeautifulSoup(res.text, "html.parser")
        image_candidates = []

        # ① OG/Twitter 이미지 탐색
        for prop in ["og:image", "twitter:image", "image"]:
            tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
            if tag and tag.get("content"):
                image_candidates.append(tag["content"])

        # ② Fallback: 첫 번째 <img> 태그
        if not image_candidates:
            img_tag = soup.find("img")
            if img_tag and img_tag.get("src"):
                from urllib.parse import urljoin
                img_src = img_tag["src"]
                if img_src.startswith("//"):
                    img_src = "https:" + img_src
                elif img_src.startswith("/"):
                    img_src = urljoin(url, img_src)
                image_candidates.append(img_src)

        # ③ 유효 이미지 필터링
        for img_url in image_candidates:
            if img_url.startswith("http"):
                try:
                    check = requests.head(img_url, headers=headers, timeout=3)
                    if check.ok and "image" in check.headers.get("Content-Type", ""):
                        print(f" ✅ [썸네일] 감지됨 → {img_url}")
                        return img_url
                except:
                    print(f" ⚠️ [썸네일] MIME 확인 실패 → {img_url}")
                    return img_url

        print(" ⚠️ [썸네일] 유효 이미지 없음")
    except Exception as e:
        print(f"⚠️ [썸네일 오류] {e}")
        return ""
    return ""


# ────────────────────────────────────────────────
# 🎨 AI 이미지 생성
# ────────────────────────────────────────────────
def generate_ai_thumbnail(title: str, summary: str) -> str:
    try:
        prompt = f"""
        Create a minimalistic tech news illustration about:
        "{title}" — {summary}.
        Style: flat, clean, futuristic, blue accent.
        """
        res = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="512x512"
        )
        return res.data[0].url
    except Exception:
        return "https://cdn-icons-png.flaticon.com/512/2965/2965879.png"


# ────────────────────────────────────────────────
# 🧠 영어 → 한국어 요약
# ────────────────────────────────────────────────
def translate_summary(summary: str) -> str:
    if not summary:
        return "내용 없음"
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "너는 최신 IT 뉴스를 자연스럽게 한국어로 요약하는 AI야."},
                {"role": "user", "content": f"다음 문장을 2문장 이내로 자연스럽게 한국어로 요약해줘:\n{summary}"}
            ],
            max_tokens=150
        )
        return res.choices[0].message.content.strip()
    except Exception:
        return summary


# ────────────────────────────────────────────────
# 🌐 Google 뉴스 수집 (디버깅 포함)
# ────────────────────────────────────────────────
def fetch_google_news(limit: int = 4):
    print("\n🌍 [Google News] 수집 시작")
    url = "https://news.google.com/rss/search?q=technology&hl=en&gl=US&ceid=US:en"
    feed = feedparser.parse(url)
    results = []

    google_session = requests.Session()
    google_session.headers.update({"User-Agent": "Mozilla/5.0"})

    for idx, entry in enumerate(feed.entries[:limit]):
        title = getattr(entry, "title", "제목 없음")
        summary_raw = getattr(entry, "summary", "내용 없음")
        summary_kr = translate_summary(summary_raw)
        raw_link = getattr(entry, "link", "#")

        print(f"\n📰 [Google-{idx+1}] {title[:60]}")
        print(f" - RSS 링크: {raw_link}")

        # 실제 뉴스 URL 찾기
        real_link = raw_link
        if hasattr(entry, "source") and hasattr(entry.source, "href"):
            real_link = entry.source.href
            print(f" - RSS 내부 source 링크 사용: {real_link}")
        else:
            try:
                redirect_res = google_session.get(raw_link, timeout=6, allow_redirects=True)
                if redirect_res.status_code == 200 and "news.google.com" not in redirect_res.url:
                    real_link = redirect_res.url
                    print(f" - 리디렉션 성공 → {real_link}")
                else:
                    print(" ⚠️ 리디렉션 실패 (Google 내부 링크 유지)")
            except Exception as e:
                print(f" ⚠️ 리디렉션 오류: {e}")

        # 썸네일 시도
        image = get_news_thumbnail(real_link)
        if not image:
            print(" ⚠️ 썸네일 없음 → AI 생성 중...")
            image = generate_ai_thumbnail(title, summary_kr)

        results.append({
            "source": "Google News",
            "title": title,
            "summary": summary_kr,
            "url": real_link,
            "published": getattr(entry, "published", "N/A"),
            "image": image,
        })

    google_session.close()
    print(f"\n✅ [Google News] {len(results)}개 완료")
    return results


# ────────────────────────────────────────────────
# 🇰🇷 Naver 뉴스 수집 (디버깅 추가)
# ────────────────────────────────────────────────
# 🇰🇷 Naver 뉴스 수집 (디버깅 + 리디렉션 추적 강화)
def fetch_naver_news(keyword: str = "IT 기술", limit: int = 4):
    print(f"\n🇰🇷 [Naver News] 수집 시작 — 키워드: {keyword}")
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
        "User-Agent": "Mozilla/5.0",
    }
    params = {"query": keyword, "display": 10, "sort": "date"}

    try:
        with requests.Session() as s:
            res = s.get(url, headers=headers, params=params, timeout=5)
            res.raise_for_status()
            items = res.json().get("items", [])
    except Exception as e:
        print(f"❌ Naver API 실패: {e}")
        return []

    results = []
    for i, item in enumerate(items[:limit]):
        title = item["title"].replace("<b>", "").replace("</b>", "")
        summary = item["description"].replace("<b>", "").replace("</b>", "")
        link = item["link"]

        print(f"\n🗞️ [Naver-{i+1}] {title[:60]}")
        print(f" - 원본 링크: {link}")

        # ✅ 리디렉션 추적 (naver 중계 페이지인 경우 실제 언론사로 이동)
        try:
            redirect_res = s.get(link, timeout=6, allow_redirects=True)
            real_link = redirect_res.url if redirect_res.status_code == 200 else link
            print(f" - 최종 링크: {real_link}")
        except Exception as e:
            print(f" ⚠️ 리디렉션 실패: {e}")
            real_link = link

        # ✅ 썸네일 시도
        image = get_news_thumbnail(real_link)
        if image:
            print(f" ✅ 썸네일 감지: {image}")
        else:
            print(" ⚠️ 썸네일 없음 → AI 대체 생성 중...")
            image = generate_ai_thumbnail(title, summary)

        results.append({
            "source": "Naver News",
            "title": title,
            "summary": summary,
            "url": real_link,
            "published": item.get("pubDate", "N/A"),
            "image": image,
        })

    print(f"\n✅ [Naver News] {len(results)}개 완료")
    return results



# ────────────────────────────────────────────────
# 📰 통합 뉴스 수집
# ────────────────────────────────────────────────
def get_latest_news(keyword: str = "IT 기술", limit: int = 4):
    google_news = fetch_google_news(limit)
    naver_news = fetch_naver_news(keyword, limit)
    combined = google_news + naver_news
    print(f"\n🧩 통합 뉴스 총 {len(combined)}개 반환 완료")
    return combined
