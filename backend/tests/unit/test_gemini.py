"""GeminiClient against a fake google-genai client: request and response mapping, errors.

Nothing here reaches Google; the fake stands in for client.models.generate_content and
answers with real SDK response/error objects.
"""

import json

import httpx
import pytest
from google.genai import errors, types

from app.core.config import Settings
from app.integrations.gemini import GeminiClient, GeminiNotConfigured, gemini_client
from app.integrations.llm import LLMError, LLMRequest
from app.summaries.policy import Budget
from app.summaries.summarizer import Summarizer, SummaryInput
from app.summaries.translate import build_request, translate
from tests.summary_helpers import DEV_SPRING, NEWS_KO, article

KEY = "test-key-not-real-0123456789"
RETRY_INFO = {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "42s"}


def answer(text, finish="STOP", blocked=None, thought=None):
    parts = [{"text": thought, "thought": True}] if thought else []
    data = {
        "candidates": [
            {
                "content": {"role": "model", "parts": [*parts, {"text": text}]},
                "finishReason": finish,
            }
        ],
        "usageMetadata": {"promptTokenCount": 120, "candidatesTokenCount": 45},
    }
    if blocked:
        data = {"promptFeedback": {"blockReason": blocked}}
    return types.GenerateContentResponse.model_validate(data)


def api_error(code, status, headers=None, details=None):
    body = {"error": {"code": code, "status": status, "message": f"{status} from Google"}}
    if details:
        body["error"]["details"] = details
    response = httpx.Response(code, headers=headers or {})
    cls = errors.ClientError if code < 500 else errors.ServerError
    return cls(code, body, response)


class FakeModels:
    def __init__(self, *results):
        self.results, self.calls = list(results), []

    def generate_content(self, *, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class FakeSDK:
    def __init__(self, *results):
        self.models = FakeModels(*results)


def client(*results, model="gemini-3.1-flash-lite"):
    sdk = FakeSDK(*results)
    return GeminiClient(KEY, model, 30, client=sdk), sdk.models


def test_the_request_maps_onto_generate_content():
    gemini, models = client(answer('{"title": "제목", "excerpt": null}'))
    response = gemini.complete(LLMRequest("system rules", "user text", 400))

    call = models.calls[0]
    assert call["model"] == "gemini-3.1-flash-lite" and call["contents"] == "user text"
    config = call["config"]
    assert config.system_instruction == "system rules"
    assert config.response_mime_type == "application/json"
    assert config.max_output_tokens == 400
    assert (response.text, response.input_tokens, response.output_tokens) == (
        '{"title": "제목", "excerpt": null}',
        120,
        45,
    )


def test_thought_parts_are_left_out_of_the_answer():
    gemini, _ = client(answer('{"a": 1}', thought="thinking..."))
    assert gemini.complete(LLMRequest("s", "u", 10)).text == '{"a": 1}'


def test_the_sdk_client_makes_one_attempt_with_the_configured_timeout():
    gemini = GeminiClient(KEY, "m", 12.5)
    options = gemini._client._api_client._http_options
    assert options.timeout == 12500 and options.retry_options.attempts == 1
    assert gemini._client._api_client.vertexai is False


def test_translation_through_gemini():
    gemini, models = client(
        answer(
            json.dumps(
                {"title": "Nimbus, N3 출시를 2027년으로 연기", "excerpt": None},
                ensure_ascii=False,
            )
        )
    )
    result = translate(gemini, "Nimbus delays its N3 AI accelerator to 2027", None)
    assert (result.status, result.title) == ("done", "Nimbus, N3 출시를 2027년으로 연기")
    expected = build_request("Nimbus delays its N3 AI accelerator to 2027", None)
    assert models.calls[0]["contents"] == expected.user
    assert models.calls[0]["config"].system_instruction == expected.system


@pytest.mark.parametrize(
    ("kind", "page", "payload", "field"),
    [
        ("news", "news_ko.html", NEWS_KO, "what_happened"),
        ("dev", "dev_spring.html", DEV_SPRING, "implementation"),
    ],
)
def test_news_and_dev_summaries_through_gemini(kind, page, payload, field):
    gemini, _ = client(answer(json.dumps(payload, ensure_ascii=False)))
    outcome = Summarizer(gemini).summarize(
        SummaryInput(kind, "https://example.com/a", "Title", html=article(page))
    )
    assert outcome.status == "done" and outcome.model == "gemini-3.1-flash-lite"
    assert outcome.payload[field] == payload[field]
    assert (outcome.input_tokens, outcome.output_tokens) == (120, 45)


def test_invalid_json_is_asked_once_more_then_fails():
    gemini, models = client(answer("not json"), answer("still not json"))
    outcome = Summarizer(gemini, sleep=lambda s: None).summarize(
        SummaryInput("news", "https://example.com/a", "Title", html=article("news_ko.html"))
    )
    assert (outcome.status, outcome.error_code, outcome.payload) == ("failed", "invalid_json", None)
    assert len(models.calls) == 2


def test_invalid_translation_answer_fails_without_a_result():
    gemini, _ = client(answer('{"title": 1}'))
    result = translate(gemini, "Nimbus delays N3", None)
    assert (result.status, result.error_code, result.title) == ("failed", "invalid_answer", None)


@pytest.mark.parametrize(
    ("error", "kind", "retry_after"),
    [
        (api_error(429, "RESOURCE_EXHAUSTED", headers={"retry-after": "7"}), "rate_limited", 7),
        (
            api_error(
                429,
                "RESOURCE_EXHAUSTED",
                details=[RETRY_INFO],
            ),
            "rate_limited",
            42,
        ),
        (api_error(429, "RESOURCE_EXHAUSTED"), "rate_limited", None),
        (api_error(500, "INTERNAL"), "server", None),
        (api_error(503, "UNAVAILABLE"), "server", None),
        (api_error(408, "DEADLINE_EXCEEDED"), "timeout", None),
        (api_error(400, "INVALID_ARGUMENT"), "bad_request", None),
        (api_error(401, "UNAUTHENTICATED"), "bad_request", None),
        (api_error(403, "PERMISSION_DENIED"), "bad_request", None),
        (api_error(404, "NOT_FOUND"), "bad_request", None),
        (httpx.ReadTimeout("slow"), "timeout", None),
        (httpx.ConnectError("refused"), "network", None),
    ],
)
def test_errors_become_llm_errors(error, kind, retry_after):
    gemini, _ = client(error)
    with pytest.raises(LLMError) as caught:
        gemini.complete(LLMRequest("s", "u", 10))
    assert caught.value.kind == kind and caught.value.retry_after == retry_after
    assert KEY not in str(caught.value) and gemini.last_error == str(caught.value)


def test_auth_and_missing_model_errors_say_what_to_check():
    gemini, _ = client(api_error(403, "PERMISSION_DENIED"), api_error(404, "NOT_FOUND"))
    for expected in ("check GEMINI_API_KEY", "model gemini-3.1-flash-lite not available"):
        with pytest.raises(LLMError, match=expected):
            gemini.complete(LLMRequest("s", "u", 10))


def test_a_long_rate_limit_wait_is_not_retried_and_nothing_is_stored():
    gemini, models = client(api_error(429, "RESOURCE_EXHAUSTED", headers={"retry-after": "60"}))
    outcome = Summarizer(gemini, sleep=lambda s: pytest.fail("no wait")).summarize(
        SummaryInput("news", "https://example.com/a", "Title", html=article("news_ko.html"))
    )
    assert (outcome.status, outcome.error_code, outcome.payload) == ("failed", "rate_limited", None)
    assert len(models.calls) == 1


def test_a_server_error_is_retried_once_within_the_budget():
    budget = Budget(max_calls=4)
    gemini, models = client(
        api_error(503, "UNAVAILABLE"), answer(json.dumps(NEWS_KO, ensure_ascii=False))
    )
    outcome = Summarizer(gemini, budget, sleep=lambda s: None).summarize(
        SummaryInput("news", "https://example.com/a", "Title", html=article("news_ko.html"))
    )
    assert outcome.status == "done" and len(models.calls) == 2 == budget.calls


@pytest.mark.parametrize(
    "response",
    [answer("", blocked="SAFETY"), answer('{"title": "x"}', finish="SAFETY")],
)
def test_blocked_answers_are_refusals(response):
    gemini, _ = client(response)
    with pytest.raises(LLMError) as caught:
        gemini.complete(LLMRequest("s", "u", 10))
    assert caught.value.kind == "refused"


def test_a_missing_key_fails_before_any_client_exists(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    settings = Settings(
        database_url="mysql+pymysql://u:p@127.0.0.1:3307/devhub_dev",
        jwt_secret="x" * 40,
        _env_file=None,
    )
    assert settings.gemini_model == "gemini-3.1-flash-lite"
    with pytest.raises(GeminiNotConfigured, match="GEMINI_API_KEY is not set"):
        gemini_client(settings)


def test_the_key_and_model_come_from_the_environment(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", KEY)
    monkeypatch.setenv("GEMINI_MODEL", "gemini-other")
    settings = Settings(
        database_url="mysql+pymysql://u:p@127.0.0.1:3307/devhub_dev",
        jwt_secret="x" * 40,
        _env_file=None,
    )
    gemini = gemini_client(settings)
    assert gemini.model == "gemini-other"
    assert KEY not in repr(settings) and KEY not in str(settings.model_dump())
