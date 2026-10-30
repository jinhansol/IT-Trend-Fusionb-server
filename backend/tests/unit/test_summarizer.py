"""The summarizer with a scripted LLM: calls only when worthwhile, failures stay failures."""

import json

import pytest

from app.integrations.llm import LLMError
from app.summaries.policy import Budget
from app.summaries.prompts import RETRY_NOTE
from app.summaries.summarizer import Summarizer, SummaryInput
from tests.summary_helpers import DEV_SPRING, NEWS_KO, ScriptedLLM, article


def news_ko(**overrides):
    values = {
        "kind": "news",
        "url": "https://news.example.com/a/1",
        "title": "데브클라우드, 벡터스토어 정식 출시",
        "html": article("news_ko.html"),
    }
    return SummaryInput(**(values | overrides))


def dev_spring(**overrides):
    values = {
        "kind": "dev",
        "url": "https://blog.example.com/virtual-threads",
        "title": "가상 스레드 적용기",
        "html": article("dev_spring.html"),
    }
    return SummaryInput(**(values | overrides))


def summarizer(*answers, **budget):
    sleeps: list[float] = []
    llm = ScriptedLLM(*answers)
    return Summarizer(llm, Budget(**budget), sleep=sleeps.append), llm, sleeps


# --- success ------------------------------------------------------------------------------


def test_news_summary_is_validated_and_kept():
    s, llm, _ = summarizer(NEWS_KO)
    outcome = s.summarize(news_ko())

    assert outcome.status == "done" and outcome.attempts == 1
    assert outcome.payload["what_happened"].startswith("데브클라우드가 10월 28일")
    assert "insufficient" not in outcome.payload
    assert (outcome.model, outcome.input_tokens, outcome.output_tokens) == (
        "scripted-test-model",
        1000,
        200,
    )
    assert outcome.prompt_version == "news-e1.1" and len(outcome.input_hash) == 64
    assert outcome.warnings == []  # every number in the summary is in the article
    assert "1,200개 팀" in llm.requests[0].user


def test_dev_summary_reports_languages_and_omissions():
    s, _, _ = summarizer(DEV_SPRING)
    outcome = s.summarize(dev_spring())

    assert outcome.status == "done" and outcome.payload["implementation"]["steps"]
    assert outcome.code_languages == ["java", "yaml"]
    assert outcome.omissions.code_lines_kept == 44 and not outcome.partial_input


def test_english_news_and_python_markdown_work_the_same_way():
    s, llm, _ = summarizer(NEWS_KO, DEV_SPRING)
    english = news_ko(html=article("news_en.html"), url="https://news.example.com/en/1")
    python = SummaryInput(
        "dev", "https://blog.example.com/asyncio", "asyncio 취소", markdown=article("dev_python.md")
    )
    assert s.summarize(english).status == "done"
    assert s.summarize(python).status == "done"
    assert "```python" in llm.requests[1].user


def test_numbers_missing_from_the_article_are_flagged():
    invented = NEWS_KO | {"caveats": ["성능이 35% 개선됐다고 밝혔다."]}
    s, _, _ = summarizer(invented)
    outcome = s.summarize(news_ko())

    assert outcome.status == "done" and outcome.warnings == ["unsupported_number:35"]


def test_a_fenced_json_answer_is_accepted():
    s, _, _ = summarizer("```json\n" + json.dumps(NEWS_KO, ensure_ascii=False) + "\n```")
    assert s.summarize(news_ko()).status == "done"


# --- no call when it is not worth it ------------------------------------------------------


def test_short_content_is_skipped_without_a_call():
    s, llm, _ = summarizer(NEWS_KO)
    outcome = s.summarize(news_ko(html=article("short.html")))

    assert (outcome.status, outcome.skip_reason) == ("skipped", "insufficient_input")
    assert llm.requests == [] and outcome.payload is None


def test_the_same_input_is_summarized_once():
    s, llm, _ = summarizer(NEWS_KO)
    first = s.summarize(news_ko())
    # Same article with different whitespace and a different URL: same hash, no new call.
    again = s.summarize(
        news_ko(html=article("news_ko.html").replace("</p>", "</p>\n\n"), url="https://x.example/b")
    )

    assert len(llm.requests) == 1
    assert again.status == "done" and again.reused and again.attempts == 0
    assert again.input_hash == first.input_hash and again.payload == first.payload


def test_a_changed_article_is_summarized_again():
    s, llm, _ = summarizer(NEWS_KO)
    s.summarize(news_ko())
    s.summarize(news_ko(html=article("news_ko.html").replace("1,200개", "1,300개")))
    assert len(llm.requests) == 2


@pytest.mark.parametrize(
    "overrides",
    [
        {"url": "javascript:alert(1)"},
        {"url": "ftp://news.example.com/a"},
        {"url": "/relative/path"},
        {"url": "https://exa mple.com/a"},
        {"title": "   "},
        {"html": None},  # neither html nor markdown
        {"markdown": "# both given"},
        {"html": "<p>" + "x" * 2_000_001 + "</p>"},
    ],
)
def test_invalid_input_is_skipped_without_a_call(overrides):
    s, llm, _ = summarizer(NEWS_KO)
    outcome = s.summarize(news_ko(**overrides))

    assert (outcome.status, outcome.skip_reason) == ("skipped", "invalid_input")
    assert llm.requests == []


def test_unknown_kind_is_a_programming_error():
    s, _, _ = summarizer(NEWS_KO)
    with pytest.raises(ValueError):
        s.summarize(news_ko(kind="video"))


# --- bad answers --------------------------------------------------------------------------


def test_invalid_json_is_asked_again_once_then_fails():
    s, llm, _ = summarizer("this is not json", "still {not json")
    outcome = s.summarize(news_ko())

    assert (outcome.status, outcome.error_code, outcome.attempts) == (
        "failed",
        "invalid_json",
        2,
    )
    assert outcome.payload is None
    assert RETRY_NOTE not in llm.requests[0].system and RETRY_NOTE in llm.requests[1].system


def test_a_bad_answer_followed_by_a_good_one_succeeds():
    s, _, _ = summarizer("[1, 2, 3]", NEWS_KO)
    outcome = s.summarize(news_ko())
    assert (outcome.status, outcome.error_code, outcome.attempts) == ("done", None, 2)


@pytest.mark.parametrize(
    "answer",
    [
        {"what_happened": "headline missing"},
        NEWS_KO | {"sentiment": "positive"},
        NEWS_KO | {"headline": "h" * 200},
        DEV_SPRING,  # the other kind's schema
    ],
)
def test_schema_violations_fail_without_a_made_up_summary(answer):
    s, _, _ = summarizer(answer)
    outcome = s.summarize(news_ko())

    assert (outcome.status, outcome.error_code) == ("failed", "schema_invalid")
    assert outcome.payload is None


def test_the_model_saying_insufficient_is_respected():
    s, _, _ = summarizer({"insufficient": True})
    outcome = s.summarize(news_ko())
    assert (outcome.status, outcome.skip_reason) == ("skipped", "insufficient_input")


def test_a_summary_without_its_core_field_is_not_shown():
    s, _, _ = summarizer(NEWS_KO | {"what_happened": None})
    outcome = s.summarize(news_ko())
    assert (outcome.status, outcome.skip_reason, outcome.payload) == (
        "skipped",
        "insufficient_input",
        None,
    )


# --- provider errors ----------------------------------------------------------------------


def test_a_timeout_is_retried_once():
    s, _, sleeps = summarizer(LLMError("timeout"), NEWS_KO)
    outcome = s.summarize(news_ko())
    assert (outcome.status, outcome.attempts) == ("done", 2) and sleeps == [1.0]


@pytest.mark.parametrize("kind", ["timeout", "server", "network"])
def test_transient_errors_that_persist_fail_with_their_code(kind):
    s, _, _ = summarizer(LLMError(kind))
    outcome = s.summarize(news_ko())
    assert (outcome.status, outcome.error_code, outcome.attempts) == ("failed", kind, 2)


def test_rate_limit_waits_for_retry_after():
    s, _, sleeps = summarizer(LLMError("rate_limited", retry_after=3), NEWS_KO)
    assert s.summarize(news_ko()).status == "done" and sleeps == [3]


def test_rate_limit_with_a_long_wait_fails_at_once():
    s, llm, sleeps = summarizer(LLMError("rate_limited", retry_after=600), NEWS_KO)
    outcome = s.summarize(news_ko())

    assert (outcome.status, outcome.error_code) == ("failed", "rate_limited")
    assert len(llm.requests) == 1 and sleeps == []


def test_a_refusal_is_not_retried():
    s, llm, _ = summarizer(LLMError("refused"), NEWS_KO)
    outcome = s.summarize(news_ko())
    assert (outcome.status, outcome.skip_reason) == ("skipped", "refused")
    assert len(llm.requests) == 1


def test_a_bad_request_is_not_retried():
    s, llm, _ = summarizer(LLMError("bad_request"), NEWS_KO)
    outcome = s.summarize(news_ko())
    assert (outcome.status, outcome.error_code) == ("failed", "bad_request")
    assert len(llm.requests) == 1


# --- budget and circuit breaker -----------------------------------------------------------


def test_the_call_budget_stops_further_calls():
    s, llm, _ = summarizer(NEWS_KO, DEV_SPRING, max_calls=1)
    assert s.summarize(news_ko()).status == "done"
    outcome = s.summarize(dev_spring())

    assert (outcome.status, outcome.skip_reason) == ("skipped", "budget_exhausted")
    assert len(llm.requests) == 1


def test_the_budget_also_stops_a_retry():
    s, llm, _ = summarizer(LLMError("server"), NEWS_KO, max_calls=1)
    outcome = s.summarize(news_ko())

    assert (outcome.status, outcome.skip_reason) == ("skipped", "budget_exhausted")
    assert outcome.error_code is None and outcome.attempts == 1
    assert len(llm.requests) == 1


def test_repeated_failures_open_the_circuit():
    s, llm, _ = summarizer(LLMError("server"), max_consecutive_failures=2)
    first = s.summarize(news_ko())
    second = s.summarize(dev_spring())
    third = s.summarize(news_ko(html=article("news_en.html")))

    assert first.status == second.status == "failed"
    assert (third.status, third.skip_reason) == ("skipped", "circuit_open")
    assert len(llm.requests) == 4  # 2 attempts each for the first two, none for the third


def test_a_success_resets_the_failure_count():
    s, _, _ = summarizer(
        LLMError("bad_request"), NEWS_KO, LLMError("bad_request"), max_consecutive_failures=2
    )
    assert s.summarize(news_ko()).status == "failed"
    assert s.summarize(news_ko()).status == "done"
    assert s.summarize(dev_spring()).status == "failed"
    assert s.summarize(news_ko(html=article("news_en.html"))).skip_reason != "circuit_open"


def test_a_reused_summary_cannot_change_the_stored_one():
    s, _, _ = summarizer(NEWS_KO)
    s.summarize(news_ko())
    reused = s.summarize(news_ko())
    reused.payload["headline"] = "changed by a caller"

    assert s.summarize(news_ko()).payload["headline"] == NEWS_KO["headline"]


# --- review fixes (PR #1) -----------------------------------------------------------------


def test_neither_the_first_nor_a_reused_result_can_change_the_cache():
    s, llm, _ = summarizer(DEV_SPRING)
    first = s.summarize(dev_spring())
    first.payload["implementation"]["steps"].append("added by a caller")
    first.payload["key_concepts"][0]["name"] = "changed"
    first.warnings.append("w")
    first.code_languages.append("cobol")
    first.omissions.chars_after = -1

    reused = s.summarize(dev_spring())
    assert reused.payload == DEV_SPRING
    assert reused.warnings == [] and reused.code_languages == ["java", "yaml"]
    assert reused.omissions.chars_after > 0

    reused.payload["implementation"]["steps"].clear()
    reused.omissions.code_lines_kept = 0
    again = s.summarize(dev_spring())
    assert again.payload["implementation"]["steps"] == DEV_SPRING["implementation"]["steps"]
    assert again.omissions.code_lines_kept == 44
    assert len(llm.requests) == 1


@pytest.mark.parametrize(
    ("length", "called"),
    [(1, True), (499, True), (500, True), (501, False), (25_000, False)],
)
def test_title_length_boundary(length, called):
    s, llm, _ = summarizer(NEWS_KO)
    outcome = s.summarize(news_ko(title="가" * length))

    assert bool(llm.requests) is called
    if not called:
        assert (outcome.status, outcome.skip_reason) == ("skipped", "invalid_input")
