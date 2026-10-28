import copy
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.content_loader.taxonomy import (
    SourcesFile,
    TechnologiesFile,
    read_sources,
    read_technologies,
)
from tests.collect_helpers import SOURCES, TECHNOLOGIES

CONTENT = Path(__file__).resolve().parents[2] / "content"


def test_repository_files_are_valid():
    technologies = read_technologies(CONTENT / "technologies.yaml")
    sources = read_sources(CONTENT / "sources.yaml")
    assert len(technologies.technologies) >= 40
    assert {s.adapter for s in sources.sources} == {"rss", "devto", "hackernews", "stackoverflow"}


def with_source(**changes):
    data = copy.deepcopy(SOURCES)
    data["sources"][1].update(changes)  # devto
    return data


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (with_source(channel=None, channel_name=None), "every other source needs one"),
        (with_source(channel_name=None), "channel and channel_name go together"),
        (with_source(options={"top_days": 99}), "less than or equal to 30"),
        (with_source(options={"unknown": 1}), "Extra inputs"),
        (with_source(site_url="ftp://dev.to"), "http(s)"),
        (with_source(adapter="rss", options={}), "rss sources need a feed_url"),
        (with_source(channel="kr-techblog"), "must share the name"),
    ],
)
def test_invalid_sources_are_rejected(data, message):
    with pytest.raises(ValidationError, match=message):
        SourcesFile.model_validate(data)


def test_source_options_get_their_defaults():
    hn = SourcesFile.model_validate(SOURCES).sources[2]
    assert hn.options == {"tags": "front_page"}


def test_aliases_are_lower_cased_and_unique_across_technologies():
    data = copy.deepcopy(TECHNOLOGIES)
    data["technologies"][0]["aliases"] = ["Python", "PYTHON"]
    with pytest.raises(ValidationError, match="duplicate alias: python"):
        TechnologiesFile.model_validate(data)
