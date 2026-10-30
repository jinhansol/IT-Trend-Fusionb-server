"""Decisions made before any model call: input limits, sufficiency, the input hash, and
the per-run budget. Numbers marked [제안값] in design v2 are constants here so a later
review can change them in one place."""

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

from app.summaries.extract import Extracted

# Input after extraction, in characters [제안값].
MAX_INPUT_CHARS = {"news": 6000, "dev": 12000}
# Raw HTML/Markdown larger than this is refused before parsing.
MAX_SOURCE_CHARS = 2_000_000
# A summary needs at least this much article text, and News at least 3 paragraphs [제안값].
MIN_CHARS = {"news": 800, "dev": 1500}
MIN_PARAGRAPHS = {"news": 3, "dev": 1}
# Partial input (design v2, 5.3) [제안값].
PARTIAL_BODY_CUT = 0.25
PARTIAL_CODE_CUT = 0.50
REFUSE_BODY_CUT = 0.60

Sufficiency = Literal["full", "partial", "insufficient"]


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n")
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def input_hash(kind: str, title: str, text: str) -> str:
    """Same kind, title and normalized text -> same hash, whatever the whitespace."""
    material = f"{kind}\n{normalize_text(title)}\n{normalize_text(text)}"
    return hashlib.sha256(material.encode()).hexdigest()


def sufficiency(kind: str, extracted: Extracted) -> Sufficiency:
    om = extracted.omissions
    if om.chars_after < MIN_CHARS[kind] or extracted.paragraphs < MIN_PARAGRAPHS[kind]:
        return "insufficient"
    if om.sections_dropped or om.body_cut_ratio > REFUSE_BODY_CUT:
        return "insufficient"
    if (
        om.sections_truncated
        or om.body_cut_ratio > PARTIAL_BODY_CUT
        or om.code_cut_ratio > PARTIAL_CODE_CUT
    ):
        return "partial"
    return "full"


@dataclass
class Budget:
    """Per-run limits: model calls, and consecutive failures before the run stops."""

    max_calls: int = 50
    max_consecutive_failures: int = 5
    calls: int = 0
    consecutive_failures: int = 0

    def exhausted(self) -> bool:
        return self.calls >= self.max_calls

    def circuit_open(self) -> bool:
        return self.consecutive_failures >= self.max_consecutive_failures

    def record_call(self) -> None:
        self.calls += 1

    def record_outcome(self, failed: bool) -> None:
        self.consecutive_failures = self.consecutive_failures + 1 if failed else 0


_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")


def unsupported_numbers(summary_text: str, source_text: str) -> list[str]:
    """Numbers and versions in the summary that the source never mentions.

    A cheap check for one error type (design v2, F2 in 9.2); it cannot see wrong names
    or wrong claims, which need a human review."""
    source = set(_NUMBER.findall(source_text))
    return sorted({n for n in _NUMBER.findall(summary_text) if n not in source})
