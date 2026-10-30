"""The LLM client interface the summary and translation jobs talk to.

The real client (app/integrations/gemini.py) turns provider errors into LLMError kinds
so the jobs can decide what to retry. Tests use a scripted fake client.
"""

from dataclasses import dataclass
from typing import Literal, Protocol

ErrorKind = Literal["timeout", "network", "rate_limited", "server", "refused", "bad_request"]
RETRYABLE: frozenset[str] = frozenset({"timeout", "network", "rate_limited", "server"})


class LLMError(Exception):
    def __init__(self, kind: ErrorKind, message: str = "", retry_after: float | None = None):
        super().__init__(message or kind)
        self.kind = kind
        # Seconds the provider asked us to wait (rate_limited); None means "use the backoff".
        self.retry_after = retry_after

    @property
    def retryable(self) -> bool:
        return self.kind in RETRYABLE


@dataclass(frozen=True)
class LLMRequest:
    system: str
    user: str
    max_output_tokens: int


@dataclass(frozen=True)
class LLMResponse:
    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None


class LLMClient(Protocol):
    model: str

    def complete(self, request: LLMRequest) -> LLMResponse: ...
