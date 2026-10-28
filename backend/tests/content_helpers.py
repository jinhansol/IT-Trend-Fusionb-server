"""Builders for throwaway learning-content directories used by tests."""

from pathlib import Path

import yaml


def activity(slug="read-intro", kind="reading", **overrides):
    data = {"slug": slug, "kind": kind, "title": f"Activity {slug}", "body_md": "Some *text*."}
    data.update(overrides)
    return data


def unit(slug="unit-one", position=1, activities=None, **overrides):
    data = {
        "slug": slug,
        "position": position,
        "title": f"Unit {slug}",
        "summary": "Summary",
        "estimated_minutes": 30,
        "activities": activities if activities is not None else [activity()],
    }
    data.update(overrides)
    return data


def write_track(root: Path, slug="sample", units=(), **track_overrides) -> Path:
    directory = root / slug
    (directory / "units").mkdir(parents=True, exist_ok=True)
    for old in (directory / "units").glob("*.yaml"):
        old.unlink()
    track = {"slug": slug, "title": f"Track {slug}", "description": "Desc", "position": 1}
    track.update(track_overrides)
    (directory / "track.yaml").write_text(yaml.safe_dump(track, allow_unicode=True), "utf-8")
    for item in units:
        name = f"{item['position']:02d}-{item['slug']}.yaml"
        (directory / "units" / name).write_text(yaml.safe_dump(item, allow_unicode=True), "utf-8")
    return directory


def question(key="q1", type="single", correct=("b",), choices=("a", "b", "c"), **overrides):
    data = {
        "key": key,
        "type": type,
        "prompt": f"Question {key}?",
        "explanation": "Because.",
        "choices": [{"key": c, "label": f"Choice {c}", "correct": c in correct} for c in choices],
    }
    data.update(overrides)
    return data


def quiz(questions=None, pass_score_percent=80):
    return {
        "pass_score_percent": pass_score_percent,
        "questions": questions if questions is not None else [question("q1"), question("q2")],
    }
