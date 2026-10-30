"""One pipeline for News and Dev: check input, extract, decide, call the model, validate.

The order matters for cost: every check that can avoid a model call runs first
(invalid input, too little text, a summary for the same input already done, budget).
A failure is returned as a status with a code, never replaced by a made-up summary.

Offline only (E1): the caller passes article HTML/Markdown it already holds and an
LLMClient. Nothing here fetches pages or writes to the database; done results are
kept in the in-memory `done` map until F2 gives them a table.
"""

import copy
import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from typing import Literal

from pydantic import ValidationError

from app.integrations.links import SkipEntry, checked_url
from app.integrations.llm import LLMClient, LLMError, LLMRequest
from app.summaries.extract import Extracted, Omissions, extract_html, extract_markdown
from app.summaries.policy import (
    MAX_INPUT_CHARS,
    MAX_SOURCE_CHARS,
    MAX_TITLE_CHARS,
    Budget,
    input_hash,
    sufficiency,
    unsupported_numbers,
)
from app.summaries.prompts import PROMPT_VERSIONS, build_prompt
from app.summaries.schemas import SCHEMAS

Status = Literal["done", "failed", "skipped"]
SkipReason = Literal[
    "invalid_input",
    "insufficient_input",
    "budget_exhausted",
    "circuit_open",
    "refused",
]
ErrorCode = Literal[
    "timeout",
    "network",
    "rate_limited",
    "server",
    "bad_request",
    "invalid_json",
    "schema_invalid",
]

MAX_ATTEMPTS = 2  # model calls per item in one run, retries and re-asks included
BACKOFF_SECONDS = (1.0,)
MAX_RETRY_AFTER_SECONDS = 30.0
MAX_OUTPUT_TOKENS = 800


@dataclass(frozen=True)
class SummaryInput:
    kind: str  # news | dev
    url: str
    title: str
    html: str | None = None
    markdown: str | None = None


@dataclass
class SummaryOutcome:
    status: Status
    kind: str
    prompt_version: str
    input_hash: str | None = None
    skip_reason: SkipReason | None = None
    error_code: ErrorCode | None = None
    payload: dict | None = None
    model: str | None = None
    partial_input: bool = False
    omissions: Omissions | None = None
    code_languages: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    attempts: int = 0
    input_tokens: int | None = None
    output_tokens: int | None = None
    reused: bool = False


def _strip_fence(text: str) -> str:
    """Accept a JSON object wrapped in a ``` fence; nothing more lenient than that."""
    text = text.strip()
    if text.startswith("```") and text.endswith("```"):
        text = text[3:-3].strip()
        if text.startswith("json"):
            text = text[4:]
    return text.strip()


def _add(total: int | None, value: int | None) -> int | None:
    return value if total is None else total + (value or 0)


class Summarizer:
    def __init__(
        self,
        client: LLMClient,
        budget: Budget | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._client = client
        self._budget = budget or Budget()
        self._sleep = sleep
        # (kind, input_hash, prompt_version) -> done outcome. F2 replaces this with a table.
        self.done: dict[tuple[str, str, str], SummaryOutcome] = {}

    def summarize(self, item: SummaryInput) -> SummaryOutcome:
        if item.kind not in SCHEMAS:
            raise ValueError(f"unknown kind: {item.kind}")
        outcome = SummaryOutcome("skipped", item.kind, PROMPT_VERSIONS[item.kind])

        extracted = self._extract(item)
        if extracted is None:
            outcome.skip_reason = "invalid_input"
            return outcome
        outcome.omissions = extracted.omissions
        outcome.code_languages = extracted.code_languages
        outcome.input_hash = input_hash(item.kind, item.title, extracted.text)

        verdict = sufficiency(item.kind, extracted)
        if verdict == "insufficient":
            outcome.skip_reason = "insufficient_input"
            return outcome
        outcome.partial_input = verdict == "partial"

        key = (item.kind, outcome.input_hash, outcome.prompt_version)
        if key in self.done:
            # A deep copy: nothing a caller does to the result can change the stored one.
            return replace(copy.deepcopy(self.done[key]), reused=True, attempts=0)

        if self._budget.circuit_open():
            outcome.skip_reason = "circuit_open"
            return outcome
        if self._budget.exhausted():
            outcome.skip_reason = "budget_exhausted"
            return outcome

        self._call(item, extracted, outcome)
        if outcome.status != "skipped" or outcome.attempts:
            self._budget.record_outcome(failed=outcome.status == "failed")
        if outcome.status == "done":
            self.done[key] = copy.deepcopy(outcome)
        return outcome

    def input_hash_of(self, item: SummaryInput) -> str | None:
        """The hash summarize() would use for this input, or None if the input is invalid."""
        extracted = self._extract(item)
        return None if extracted is None else input_hash(item.kind, item.title, extracted.text)

    def _extract(self, item: SummaryInput) -> Extracted | None:
        try:
            checked_url(item.url)
        except SkipEntry:
            return None
        sources = [s for s in (item.html, item.markdown) if s is not None]
        if len(sources) != 1 or len(sources[0]) > MAX_SOURCE_CHARS:
            return None
        if not item.title.strip() or len(item.title.strip()) > MAX_TITLE_CHARS:
            return None
        limit = MAX_INPUT_CHARS[item.kind]
        if item.html is not None:
            return extract_html(item.html, limit)
        return extract_markdown(item.markdown, limit)

    def _call(self, item: SummaryInput, extracted: Extracted, outcome: SummaryOutcome) -> None:
        schema = SCHEMAS[item.kind]
        outcome.model = self._client.model
        retry_prompt = False
        while outcome.attempts < MAX_ATTEMPTS:
            if self._budget.exhausted():
                outcome.status, outcome.skip_reason = "skipped", "budget_exhausted"
                outcome.error_code = None  # skipped carries a reason, failed a code
                return
            prompt = build_prompt(item.kind, item.title, extracted.text, retry=retry_prompt)
            request = LLMRequest(prompt.system, prompt.user, MAX_OUTPUT_TOKENS)
            outcome.attempts += 1
            self._budget.record_call()
            try:
                response = self._client.complete(request)
            except LLMError as exc:
                if exc.kind == "refused":
                    outcome.status, outcome.skip_reason = "skipped", "refused"
                    return
                outcome.status, outcome.error_code = "failed", exc.kind
                too_long = (exc.retry_after or 0) > MAX_RETRY_AFTER_SECONDS
                if not exc.retryable or too_long or outcome.attempts >= MAX_ATTEMPTS:
                    return
                self._sleep(
                    BACKOFF_SECONDS[outcome.attempts - 1]
                    if exc.retry_after is None
                    else exc.retry_after
                )
                continue
            outcome.input_tokens = _add(outcome.input_tokens, response.input_tokens)
            outcome.output_tokens = _add(outcome.output_tokens, response.output_tokens)

            try:
                data = json.loads(_strip_fence(response.text))
                if not isinstance(data, dict):
                    raise ValueError("not an object")
            except ValueError:
                outcome.status, outcome.error_code = "failed", "invalid_json"
                retry_prompt = True
                continue
            try:
                summary = schema.model_validate(data)
            except ValidationError:
                outcome.status, outcome.error_code = "failed", "schema_invalid"
                retry_prompt = True
                continue

            outcome.error_code = None
            if not summary.displayable():
                outcome.status, outcome.skip_reason = "skipped", "insufficient_input"
                return
            payload = summary.model_dump(exclude={"insufficient"})
            outcome.status, outcome.payload = "done", payload
            numbers = unsupported_numbers(
                json.dumps(payload, ensure_ascii=False), f"{item.title}\n{extracted.text}"
            )
            outcome.warnings = [f"unsupported_number:{n}" for n in numbers]
            return
