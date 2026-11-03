"""Scheduled collection settings: the repository schedule, time conversion, validation and
the rendered crontab."""

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.content_loader.taxonomy import read_sources
from app.jobs.schedule import SCHEDULE_FILE, Schedule, check_sources, crontab, load_schedule
from tests.conftest import BACKEND_DIR

GOOD = {
    "timezone": "Asia/Seoul",
    "groups": {
        "news": {"minute": 0, "hours": [14, 2], "sources": []},
        "dev": {"minute": 0, "hours": [5, 11, 17, 23], "sources": ["webdev"]},
    },
}


def with_changes(**groups):
    data = {"timezone": GOOD["timezone"], "groups": {k: dict(v) for k, v in GOOD["groups"].items()}}
    for name, change in groups.items():
        if change is None:
            data["groups"].pop(name)
        else:
            data["groups"].setdefault(name, {}).update(change)
    return data


def test_the_repository_schedule_is_the_trial_policy():
    schedule = load_schedule()
    assert schedule.timezone == "Asia/Seoul"
    assert schedule.groups["news"].hours == [2, 14]
    assert schedule.groups["dev"].hours == [5, 11, 17, 23]
    assert {g.minute for g in schedule.groups.values()} == {0}


def test_only_sources_with_checked_terms_are_scheduled():
    schedule = load_schedule()
    # No Korean source has confirmed reuse terms yet, so nothing is collected on schedule.
    assert schedule.groups["news"].sources == []
    assert schedule.groups["dev"].sources == []
    defined = {s.slug: s for s in read_sources(BACKEND_DIR / "content" / "sources.yaml").sources}
    for group, settings in schedule.groups.items():
        for slug in settings.sources:
            assert slug in defined, slug
            assert (defined[slug].kind == "news") == (group == "news"), slug


@pytest.mark.parametrize(
    ("zone", "news", "dev"),
    [
        ("Asia/Seoul", [2, 14], [5, 11, 17, 23]),
        ("UTC", [5, 17], [2, 8, 14, 20]),  # 02:00 KST is 17:00 UTC the day before
        ("Asia/Tokyo", [2, 14], [5, 11, 17, 23]),
        ("Asia/Kolkata", None, None),  # +05:30: not a whole hour
    ],
)
def test_hours_are_converted_to_the_server_zone(zone, news, dev):
    schedule = Schedule.model_validate(GOOD)
    if news is None:
        with pytest.raises(ValueError, match="whole-hour"):
            schedule.hours_in("news", zone)
        return
    assert schedule.hours_in("news", zone) == news
    assert schedule.hours_in("dev", zone) == dev


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (with_changes(news={"hours": [24]}), "0 to 23"),
        (with_changes(news={"hours": [2, 2]}), "distinct"),
        (with_changes(news={"hours": []}), "at least 1"),
        (with_changes(dev={"minute": 60}), "less than or equal to 59"),
        (with_changes(dev=None), "exactly news, dev"),
        (with_changes(qna={"minute": 0, "hours": [1]}), "exactly news, dev"),
        (with_changes(dev={"interval": 6}), "Extra inputs"),
        ({**GOOD, "timezone": "Europe/Berlin"}, "daylight saving"),
        ({**GOOD, "timezone": "Mars/Base"}, "unknown time zone"),
    ],
)
def test_invalid_schedules_are_rejected(data, message):
    with pytest.raises(ValidationError, match=message):
        Schedule.model_validate(data)


def test_the_crontab_runs_each_group_once_per_slot_without_overlap():
    schedule = Schedule.model_validate(GOOD)
    text = crontab(schedule, Path("/srv/devhub/backend"), "/usr/bin/uv", Path("/var/log/devhub"))
    jobs = [line for line in text.splitlines() if line and not line.startswith("#")]
    assert jobs == [
        "0 5,17 * * * cd /srv/devhub/backend && flock -n /tmp/devhub-collect-news.lock "
        "/usr/bin/uv run python -m app.jobs collect --group news "
        ">> /var/log/devhub/collect-news.log 2>&1",
        "0 2,8,14,20 * * * cd /srv/devhub/backend && flock -n /tmp/devhub-collect-dev.lock "
        "/usr/bin/uv run python -m app.jobs collect --group dev "
        ">> /var/log/devhub/collect-dev.log 2>&1",
    ]
    assert "# news: 02:00,14:00 Asia/Seoul" in text
    assert "summarize" not in text and "translate" not in text  # no Gemini on schedule


def test_a_server_zone_with_daylight_saving_is_refused():
    schedule = Schedule.model_validate(GOOD)
    with pytest.raises(ValueError, match="daylight saving"):
        crontab(schedule, Path("/b"), "uv", Path("/l"), server_tz="America/New_York")


def source(slug, kind, status="active"):
    return SimpleNamespace(slug=slug, kind=kind, status=status)


def test_a_group_runs_only_its_own_active_sources():
    run, skipped = check_sources(
        "dev",
        [source("webdev", "blog"), source("techcrunch", "news"), source("devto", "blog", "paused")],
    )
    assert [s.slug for s in run] == ["webdev"]
    assert skipped == [
        "techcrunch: a news source is not in the dev group",
        "devto: paused",
    ]


def test_the_default_schedule_file_is_in_content():
    assert SCHEDULE_FILE == BACKEND_DIR / "content" / "collect-schedule.yaml"


def test_the_crontab_is_one_marked_block_that_a_reinstall_replaces(tmp_path):
    schedule = Schedule.model_validate(GOOD)
    block = crontab(schedule, Path("/srv/devhub/backend"), "/usr/bin/uv", Path("/var/log/devhub"))
    lines = block.splitlines()
    assert lines[0] == "# BEGIN devhub-collect" and lines[-1] == "# END devhub-collect"

    # The install command from app/jobs/schedule.py, run twice over an existing crontab.
    current = tmp_path / "crontab"
    current.write_text("MAILTO=ops@example.com\n15 3 * * * /usr/bin/backup\n", encoding="utf-8")
    for _ in range(2):
        kept = subprocess.run(
            ["sed", "/^# BEGIN devhub-collect$/,/^# END devhub-collect$/d", str(current)],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        current.write_text(kept + block, encoding="utf-8")
    text = current.read_text(encoding="utf-8")
    assert text.count("# BEGIN devhub-collect") == 1
    assert text.count("--group dev") == 1
    assert text.startswith("MAILTO=ops@example.com\n15 3 * * * /usr/bin/backup\n")


def test_paths_are_quoted_and_unsafe_ones_refused():
    schedule = Schedule.model_validate(GOOD)
    block = crontab(
        schedule, Path("/srv/dev hub/backend"), "/opt/uv bin/uv", Path("/var/log/dev hub")
    )
    assert "cd '/srv/dev hub/backend' && " in block
    assert "'/opt/uv bin/uv' run python" in block
    assert ">> '/var/log/dev hub/collect-news.log' 2>&1" in block
    for backend, uv, logs, message in (
        (Path("backend"), "/usr/bin/uv", Path("/var/log/devhub"), "absolute"),
        (Path("/srv/backend"), "uv", Path("/var/log/devhub"), "absolute"),
        (Path("/srv/backend"), "/usr/bin/uv", Path("/var/log/50%"), "%"),
        (Path("/srv/back\nend"), "/usr/bin/uv", Path("/var/log/devhub"), "newline"),
    ):
        with pytest.raises(ValueError, match=message):
            crontab(schedule, backend, uv, logs)
