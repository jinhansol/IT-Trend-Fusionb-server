"""Google Gemini behind the LLMClient interface (google-genai SDK). Jobs only, server side.

One HTTP request per complete() call: the SDK's own retries are off, so the summary and
translation retry policy and call budget count every request that reaches Google.
Provider errors become LLMError kinds. Messages carry the HTTP code and status only,
never the API key or the request text.
"""

import re

import httpx
from google import genai
from google.genai import errors, types

from app.core.config import Settings
from app.integrations.llm import LLMError, LLMRequest, LLMResponse

# Finish reasons that mean the model declined to answer: skipped, not retried.
_REFUSED = {"SAFETY", "RECITATION", "BLOCKLIST", "PROHIBITED_CONTENT", "SPII"}
_SECONDS = re.compile(r"^(\d+(?:\.\d+)?)s$")


class GeminiNotConfigured(Exception):
    """GEMINI_API_KEY is missing; nothing was sent."""


class GeminiClient:
    def __init__(self, api_key: str, model: str, timeout_seconds: float, client=None) -> None:
        if not api_key:
            raise GeminiNotConfigured("GEMINI_API_KEY is not set")
        self.model = model
        self.last_error: str | None = None  # for the job's closing line
        self._client = client or genai.Client(
            api_key=api_key,
            vertexai=False,
            http_options=types.HttpOptions(
                timeout=int(timeout_seconds * 1000),
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )

    def complete(self, request: LLMRequest) -> LLMResponse:
        config = types.GenerateContentConfig(
            system_instruction=request.system,
            response_mime_type="application/json",
            max_output_tokens=request.max_output_tokens,
            # Thinking tokens share the output cap; these jobs only extract and translate.
            thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.MINIMAL),
        )
        try:
            response = self._client.models.generate_content(
                model=self.model, contents=request.user, config=config
            )
        except errors.APIError as exc:
            raise self._failed(_api_error(exc, self.model)) from None
        except httpx.TimeoutException:
            raise self._failed(LLMError("timeout", "gemini: request timed out")) from None
        except httpx.TransportError:
            raise self._failed(LLMError("network", "gemini: connection failed")) from None

        feedback = response.prompt_feedback
        if feedback is not None and feedback.block_reason is not None:
            raise self._failed(LLMError("refused", f"gemini: blocked ({feedback.block_reason})"))
        candidates = response.candidates or []
        reason = candidates[0].finish_reason if candidates else None
        if reason is not None and str(getattr(reason, "value", reason)) in _REFUSED:
            raise self._failed(LLMError("refused", f"gemini: answer withheld ({reason})"))

        usage = response.usage_metadata
        return LLMResponse(
            text=_text(response),
            input_tokens=usage.prompt_token_count if usage else None,
            output_tokens=usage.candidates_token_count if usage else None,
        )

    def _failed(self, error: LLMError) -> LLMError:
        self.last_error = str(error)
        return error


def _text(response) -> str:
    """The answer's text parts, without thought summaries."""
    candidates = response.candidates or []
    content = candidates[0].content if candidates else None
    parts = (content.parts if content else None) or []
    return "".join(p.text for p in parts if p.text and not p.thought)


def _api_error(exc: errors.APIError, model: str) -> LLMError:
    code, status = exc.code or 0, exc.status or ""
    if code == 429:
        return LLMError("rate_limited", f"gemini: 429 {status}", _retry_after(exc))
    if code == 408:
        return LLMError("timeout", f"gemini: 408 {status}")
    if code >= 500:
        return LLMError("server", f"gemini: {code} {status}")
    if code in (401, 403):
        return LLMError("bad_request", f"gemini: {code} {status} (check GEMINI_API_KEY)")
    if code == 404:
        return LLMError("bad_request", f"gemini: 404 {status} (model {model} not available)")
    return LLMError("bad_request", f"gemini: {code} {status}")


def _retry_after(exc: errors.APIError) -> float | None:
    """Seconds from the Retry-After header or the RetryInfo detail, if Google sent one."""
    header = getattr(getattr(exc, "response", None), "headers", None) or {}
    try:
        value = header.get("retry-after")
        if value is not None:
            return float(value)
    except (TypeError, ValueError):
        pass
    body = exc.details if isinstance(exc.details, dict) else {}
    for detail in body.get("error", {}).get("details", []) or []:
        if isinstance(detail, dict) and detail.get("@type", "").endswith("RetryInfo"):
            match = _SECONDS.match(str(detail.get("retryDelay", "")))
            if match:
                return float(match.group(1))
    return None


def gemini_client(settings: Settings) -> GeminiClient:
    key = settings.gemini_api_key.get_secret_value() if settings.gemini_api_key else ""
    return GeminiClient(key, settings.gemini_model, settings.gemini_timeout_seconds)
