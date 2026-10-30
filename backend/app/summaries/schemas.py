"""What the model must return, per kind. News and Dev answer different questions.

Rules shared by both (design v2, 4.4):
- Only headline is required, and not even that when the model reports insufficient=true.
- Anything the article does not state is null or an empty list; empty strings count as null.
- Unknown fields and over-long values are rejected, never trimmed.
"""

from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

Kind = Literal["news", "dev"]


def _text(max_length: int):
    return Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=max_length)
    ]


class _Summary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # The model says the article does not hold enough to summarize.
    insufficient: bool = False
    headline: _text(60) | None = None

    @field_validator("*", mode="before")
    @classmethod
    def _blank_is_null(cls, value):
        if isinstance(value, str) and not value.strip():
            return None
        if isinstance(value, list):
            return [v for v in value if not (isinstance(v, str) and not v.strip())]
        return value

    @model_validator(mode="after")
    def _headline_unless_insufficient(self):
        if not self.insufficient and self.headline is None:
            raise ValueError("headline is required unless insufficient is true")
        return self


class NewsSummary(_Summary):
    what_happened: _text(200) | None = None  # 핵심 사건
    key_changes: list[_text(120)] = Field(default_factory=list, max_length=3)  # 주요 변경 사항
    why_it_matters: _text(200) | None = None  # 원문이 밝힌 의미 (모델의 평가가 아님)
    caveats: list[_text(120)] = Field(default_factory=list, max_length=3)  # 주의 사항

    def displayable(self) -> bool:
        return not self.insufficient and self.what_happened is not None


class KeyConcept(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: _text(40)
    explanation: _text(120)


class Implementation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approach: _text(250)
    steps: list[_text(100)] = Field(default_factory=list, max_length=5)


class DevSummary(_Summary):
    key_concepts: list[KeyConcept] = Field(default_factory=list, max_length=4)  # 핵심 기술 개념
    implementation: Implementation | None = None  # 구현 접근 방식
    applicable_when: list[_text(100)] = Field(default_factory=list, max_length=3)  # 활용 상황
    caveats: list[_text(120)] = Field(default_factory=list, max_length=4)  # 한계·주의 사항

    def displayable(self) -> bool:
        return not self.insufficient and bool(self.key_concepts or self.implementation)


SCHEMAS: dict[str, type[NewsSummary] | type[DevSummary]] = {
    "news": NewsSummary,
    "dev": DevSummary,
}
