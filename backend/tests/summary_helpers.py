"""Test doubles for the summarizer: a scripted LLM client and the synthetic articles."""

import json
from pathlib import Path

from app.integrations.llm import LLMError, LLMRequest, LLMResponse

ARTICLES = Path(__file__).parent / "fixtures" / "summaries"


def article(name: str) -> str:
    return (ARTICLES / name).read_text(encoding="utf-8")


class ScriptedLLM:
    """Answers each call with the next scripted item: a str, a dict (sent as JSON) or an
    LLMError (raised). The last item repeats. Records every request."""

    model = "scripted-test-model"

    def __init__(self, *answers) -> None:
        self.answers = list(answers)
        self.requests: list[LLMRequest] = []

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        answer = self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]
        if isinstance(answer, LLMError):
            raise answer
        text = json.dumps(answer, ensure_ascii=False) if isinstance(answer, dict) else answer
        return LLMResponse(text=text, input_tokens=1000, output_tokens=200)


NEWS_KO = {
    "headline": "데브클라우드, 서울 리전 관리형 벡터 DB 정식 출시",
    "what_happened": "데브클라우드가 10월 28일 서울 리전에서 벡터스토어를 정식 출시했다.",
    "key_changes": ["하이브리드 검색 지원", "자동 백업 주기 6시간으로 변경"],
    "why_it_matters": "데이터를 국내에 두려는 수요에 대응한다고 회사가 설명했다.",
    "caveats": ["하이브리드 검색 성능 수치는 공개되지 않았다."],
}

DEV_SPRING = {
    "headline": "Spring Boot 3.2에서 가상 스레드로 블로킹 I/O 처리량 늘리기",
    "key_concepts": [
        {"name": "가상 스레드", "explanation": "생성 비용이 낮아 요청당 스레드 모델을 유지한다."}
    ],
    "implementation": {
        "approach": "설정으로 가상 스레드를 켜고 별도 스레드 풀과 synchronized를 정리했다.",
        "steps": ["스레드 풀 제거", "ReentrantLock으로 교체", "커넥션 풀 크기 조정"],
    },
    "applicable_when": ["블로킹 JDBC 호출이 많은 서비스"],
    "caveats": ["synchronized 안의 블로킹 I/O는 pinning을 일으킨다."],
}
