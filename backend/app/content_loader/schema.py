"""Format of the learning content files (backend/content/<track>/).

    content/<track>/track.yaml          track metadata
    content/<track>/units/NN-<slug>.yaml one file per unit, activities in order

Files are validated completely before anything is written to the database.
"""

import re
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlsplit

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    field_validator,
    model_validator,
)

SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
MAX_BODY_CHARS = 50_000

Slug = Annotated[str, StringConstraints(pattern=SLUG_PATTERN, max_length=64)]
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
ActivityKind = Literal["reading", "video", "exercise", "external"]


# CommonMark does not close **bold** when the closing ** follows punctuation and is
# directly followed by a letter, e.g. "**자료형(type)**이" renders the asterisks.
_UNCLOSED_BOLD = re.compile(r"\*\*[^*\n]*[)\]}'\".,!?:;]\*\*(?=[0-9A-Za-z가-힣])")


class ContentError(ValueError):
    pass


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ActivityDef(_Strict):
    slug: Slug
    kind: ActivityKind
    title: Title
    url: str | None = Field(default=None, max_length=2048)
    body_md: str | None = Field(default=None, max_length=MAX_BODY_CHARS)
    required: bool = True
    status: Literal["draft", "published"] = "published"

    @field_validator("url")
    @classmethod
    def _http_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parts = urlsplit(value)
        if parts.scheme not in ("http", "https") or not parts.netloc:
            raise ValueError("url must be an absolute http(s) URL")
        return value

    @field_validator("body_md")
    @classmethod
    def _bold_renders(cls, value: str | None) -> str | None:
        return _check_bold(value)

    @model_validator(mode="after")
    def _has_content(self) -> "ActivityDef":
        if self.url is None and not self.body_md:
            raise ValueError("an activity needs a url or body_md")
        if self.kind in ("external", "video") and self.url is None:
            raise ValueError(f"'{self.kind}' activities need a url")
        return self


def _check_bold(value: str | None) -> str | None:
    match = _UNCLOSED_BOLD.search(value or "")
    if match:
        raise ValueError(
            f"bold text will not render: {match.group(0)!r} "
            "(move the punctuation outside the ** markers)"
        )
    return value


Key = Annotated[str, StringConstraints(pattern=SLUG_PATTERN, max_length=32)]
Markdown = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)]


class ChoiceDef(_Strict):
    key: Key
    label: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
    correct: bool = False


class QuestionDef(_Strict):
    key: Key
    type: Literal["single", "multiple"] = "single"
    prompt: Markdown
    explanation: Markdown | None = None
    choices: list[ChoiceDef] = Field(min_length=2, max_length=8)

    @field_validator("prompt", "explanation")
    @classmethod
    def _bold_renders(cls, value: str | None) -> str | None:
        return _check_bold(value)

    @model_validator(mode="after")
    def _answers_make_sense(self) -> "QuestionDef":
        _require_unique([c.key for c in self.choices], f"choice key in question {self.key}")
        correct = sum(c.correct for c in self.choices)
        if self.type == "single" and correct != 1:
            raise ValueError(f"question {self.key}: single-choice needs exactly one correct choice")
        if self.type == "multiple" and correct < 1:
            raise ValueError(f"question {self.key}: needs at least one correct choice")
        return self


class QuizDef(_Strict):
    pass_score_percent: int = Field(default=80, ge=1, le=100)
    questions: list[QuestionDef] = Field(min_length=1, max_length=30)

    @model_validator(mode="after")
    def _unique_questions(self) -> "QuizDef":
        _require_unique([q.key for q in self.questions], "question key")
        return self


class UnitDef(_Strict):
    slug: Slug
    position: int = Field(ge=1)
    title: Title
    summary: str | None = None
    estimated_minutes: int | None = Field(default=None, gt=0, le=600)
    status: Literal["draft", "published"] = "published"
    activities: list[ActivityDef] = Field(min_length=1)
    # A unit without a quiz can be studied but not completed (completion needs a pass).
    quiz: QuizDef | None = None
    # Technology slugs (content/technologies.yaml) this unit teaches. Optional.
    technologies: list[Slug] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def _unique_activity_slugs(self) -> "UnitDef":
        _require_unique([a.slug for a in self.activities], "activity slug")
        _require_unique(self.technologies, "technology")
        return self


# Career screens live at /career/explore, /career/roles/<slug> and /career/goals, next
# to /career/<track>; a track with one of these slugs could not be opened.
RESERVED_TRACK_SLUGS = ("explore", "roles", "goals")


class TrackDef(_Strict):
    slug: Slug
    title: Title
    description: str | None = None
    position: int = Field(ge=1)
    status: Literal["draft", "published", "retired"] = "published"

    @field_validator("slug")
    @classmethod
    def _not_reserved(cls, value: str) -> str:
        if value in RESERVED_TRACK_SLUGS:
            raise ValueError(f"'{value}' is reserved for Career screens; pick another track slug")
        return value


class TrackContent(_Strict):
    track: TrackDef
    units: list[UnitDef]

    @model_validator(mode="after")
    def _unique_units(self) -> "TrackContent":
        _require_unique([u.slug for u in self.units], "unit slug")
        _require_unique([u.position for u in self.units], "unit position")
        return self


def _require_unique(values: list, label: str) -> None:
    duplicates = sorted({str(v) for v in values if values.count(v) > 1})
    if duplicates:
        raise ValueError(f"duplicate {label}: {', '.join(duplicates)}")


def _read_yaml(path: Path) -> dict:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ContentError(f"{path}: invalid YAML ({exc})") from exc
    if not isinstance(data, dict):
        raise ContentError(f"{path}: expected a mapping at the top level")
    return data


def _validate(model: type[_Strict], data: dict, path: Path):
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(p) for p in err['loc']) or '(file)'}: {err['msg']}"
            for err in exc.errors()
        )
        raise ContentError(f"{path}: {problems}") from exc


def read_track_directory(directory: Path) -> TrackContent:
    """Read and validate one track directory. Raises ContentError with file names."""
    track_file = directory / "track.yaml"
    if not track_file.is_file():
        raise ContentError(f"{directory}: missing track.yaml")
    track = _validate(TrackDef, _read_yaml(track_file), track_file)

    unit_files = sorted((directory / "units").glob("*.yaml"))
    units = [_validate(UnitDef, _read_yaml(path), path) for path in unit_files]
    try:
        return TrackContent(track=track, units=units)
    except ValidationError as exc:
        raise ContentError(f"{directory}: {exc.errors()[0]['msg']}") from exc
