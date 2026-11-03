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
from app.services.tagging import Tagger
from tests.collect_helpers import SOURCES, TECHNOLOGIES

CONTENT = Path(__file__).resolve().parents[2] / "content"


def test_repository_files_are_valid():
    technologies = read_technologies(CONTENT / "technologies.yaml")
    sources = read_sources(CONTENT / "sources.yaml")
    assert len(technologies.technologies) >= 40
    # Korean sources only (overseas sources and translation were dropped).
    assert {s.language for s in sources.sources} == {"ko"}
    assert {s.adapter for s in sources.sources} == {"rss"}
    # Not collected: ITWorld's robots.txt forbids /feed/; Woowahan's site blocks bots;
    # CIO Korea and Digital Daily have no working feed; the rest are new candidates.
    assert {s.slug for s in sources.sources if s.status == "paused"} == {
        "itworld-korea",
        "woowahan-tech",
        "ciokorea",
        "ddaily",
        "aitimes",
        "boho-notice",
        "kurly-tech",
        "outsider-blog",
    }
    # No source's terms are approved yet: nothing is saved or shown with a description.
    assert {s.options["terms"] for s in sources.sources} == {"unverified"}
    assert not any(s.options["excerpt"] or s.ai_summary for s in sources.sources)


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
        (with_source(options={"excerpt": True}), "excerpt needs options.terms: approved"),
        (with_source(options={"terms": "maybe"}), "unverified"),
    ],
)
def test_invalid_sources_are_rejected(data, message):
    with pytest.raises(ValidationError, match=message):
        SourcesFile.model_validate(data)


def test_source_options_get_their_defaults():
    hn = SourcesFile.model_validate(SOURCES).sources[2]
    assert hn.options == {"tags": "front_page", "terms": "approved", "excerpt": True}
    bare = copy.deepcopy(SOURCES["sources"][0]) | {"options": {}}
    assert SourcesFile.model_validate({"sources": [bare]}).sources[0].options == {
        "terms": "unverified",
        "excerpt": False,
    }


def test_ai_summary_needs_approved_terms():
    data = copy.deepcopy(SOURCES)
    data["sources"][0].update(options={}, ai_summary=True)
    with pytest.raises(ValidationError, match="ai_summary needs options.terms: approved"):
        SourcesFile.model_validate(data)


def test_aliases_are_lower_cased_and_unique_across_technologies():
    data = copy.deepcopy(TECHNOLOGIES)
    data["technologies"][0]["aliases"] = ["Python", "PYTHON"]
    with pytest.raises(ValidationError, match="duplicate alias: python"):
        TechnologiesFile.model_validate(data)


# --- tagging with the repository's technologies.yaml (no database) ---------------------


def repository_tagger():
    """The Tagger the collector builds after `content_loader technologies`, with list
    positions standing in for database ids."""
    technologies = read_technologies(CONTENT / "technologies.yaml").technologies
    aliases = [
        (i, alias, tag_only)
        for i, t in enumerate(technologies)
        for names, tag_only in ((t.aliases, False), (t.tag_aliases, True))
        for alias in names
    ]
    slugs = {i: t.slug for i, t in enumerate(technologies)}
    tagger = Tagger.from_aliases(aliases)
    return lambda title, tags=(): {slugs[i] for i in tagger.match(title, None, list(tags))}


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("React 19.2 보안 패치", {"react", "security"}),
        ("React hooks explained", {"react"}),
        ("React.js 상태 관리", {"react"}),
        ("How people react to price changes", set()),
        ("사이드카 컨테이너 구성하기", set()),
        ("컨테이너선 운임 상승", set()),
        ("Docker 이미지 최적화", {"docker"}),
        ("도커 캐시 활용", {"docker"}),
        ("Go 언어로 재작성", {"go"}),
        ("let's go", set()),
        ("JavaScript 비동기 처리", {"javascript"}),
        ("자바스크립트 비동기 처리", {"javascript"}),
        ("자바와 자바스크립트", {"java", "javascript"}),
    ],
)
def test_repository_aliases_tag_free_text(title, expected):
    assert repository_tagger()(title) == expected


def test_repository_source_tags_keep_working():
    tag = repository_tagger()
    assert tag("Untitled", ["#React", "go", "python-3.x"]) == {"react", "go", "python"}
    # css and html stay the frontend field's source-tag aliases.
    assert tag("Untitled", ["css"]) == tag("Untitled", ["html"]) == {"frontend"}
    assert tag("Untitled", ["webdev"]) == {"frontend"}


def test_existing_slugs_remain_and_docker_has_no_generic_container_alias():
    technologies = read_technologies(CONTENT / "technologies.yaml").technologies
    by_slug = {t.slug: t for t in technologies}
    assert {"frontend", "react", "docker", "go", "java", "javascript"} <= set(by_slug)
    assert {"css", "html"} <= set(by_slug["frontend"].tag_aliases)
    assert not {"container", "containers", "컨테이너"} & set(by_slug["docker"].aliases)
