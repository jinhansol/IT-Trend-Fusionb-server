"""News and Dev output schemas: null and empty lists are fine, made-up fillers are not needed."""

import pytest
from pydantic import ValidationError

from app.summaries.schemas import DevSummary, NewsSummary
from tests.summary_helpers import DEV_SPRING, NEWS_KO


def test_full_news_and_dev_summaries_validate():
    assert NewsSummary.model_validate(NEWS_KO).displayable()
    assert DevSummary.model_validate(DEV_SPRING).displayable()


def test_news_accepts_nulls_and_empty_lists():
    summary = NewsSummary.model_validate(
        {
            "headline": "발표 일정만 공개",
            "what_happened": "회사가 행사 일정을 공개했다.",
            "key_changes": [],
            "why_it_matters": None,
            "caveats": [],
        }
    )
    assert summary.why_it_matters is None and summary.key_changes == []
    assert summary.displayable()


def test_dev_accepts_no_implementation():
    summary = DevSummary.model_validate(
        {
            "headline": "개념 설명 글",
            "key_concepts": [{"name": "TaskGroup", "explanation": "작업을 묶어 함께 취소한다."}],
            "implementation": None,
        }
    )
    assert summary.implementation is None and summary.applicable_when == []
    assert summary.displayable()


def test_blank_strings_count_as_null_and_are_dropped_from_lists():
    summary = NewsSummary.model_validate(
        {"headline": "h", "what_happened": "  ", "key_changes": ["", " a "], "caveats": [" "]}
    )
    assert summary.what_happened is None
    assert summary.key_changes == ["a"] and summary.caveats == []
    assert not summary.displayable()  # no core event, nothing to show


def test_insufficient_needs_no_other_field():
    for schema in (NewsSummary, DevSummary):
        summary = schema.model_validate({"insufficient": True})
        assert summary.headline is None and not summary.displayable()


@pytest.mark.parametrize(
    ("schema", "data"),
    [
        (NewsSummary, {"what_happened": "headline missing"}),
        (NewsSummary, {"headline": "h", "sentiment": "positive"}),  # unknown field
        (NewsSummary, {"headline": "h" * 61}),
        (NewsSummary, {"headline": "h", "key_changes": ["a", "b", "c", "d"]}),
        (NewsSummary, {"headline": "h", "caveats": "not a list"}),
        (DevSummary, {"headline": "h", "key_concepts": [{"name": "only a name"}]}),
        (DevSummary, {"headline": "h", "implementation": {"steps": ["no approach"]}}),
        (DevSummary, {"headline": "h", "key_concepts": [{"name": "n", "explanation": "e"}] * 5}),
        (DevSummary, {"headline": "h", "code": "print('copied code')"}),
    ],
)
def test_invalid_outputs_are_rejected_not_trimmed(schema, data):
    with pytest.raises(ValidationError):
        schema.model_validate(data)


def test_news_and_dev_schemas_are_separate():
    with pytest.raises(ValidationError):
        NewsSummary.model_validate(DEV_SPRING)
    with pytest.raises(ValidationError):
        DevSummary.model_validate(NEWS_KO)
