# utils/http.py
import requests
import time
import random

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/118.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}


def safe_request(url, max_retry=5, timeout=10, sleep_min=0.5, sleep_max=1.2):
    """
    Velog / GitHub / RSS 요청 실패시 자동 retry 해주는 안전 요청 함수.
    
    retry 조건:
      - 응답 없음
      - HTTP status: 429 / 500 / 502 / 503 / 504 / 404 (Velog는 종종 잘못된 404 포함)
    """

    for attempt in range(max_retry):
        try:
            response = requests.get(
                url,
                headers=DEFAULT_HEADERS,
                timeout=timeout,
            )

            # 정상 응답이면 바로 return
            if response.status_code == 200:
                return response

            # Velog는 랜덤하게 404도 내보내므로 retry 처리
            if response.status_code in [404, 429, 500, 502, 503, 504]:
                print(f"[HTTP {response.status_code}] {url}")
                time.sleep(random.uniform(sleep_min, sleep_max))
                continue

            return response

        except Exception as e:
            print(f"[Request Error] {e} — retrying…")
            time.sleep(random.uniform(sleep_min, sleep_max))

    # 실패 시 None
    return None
