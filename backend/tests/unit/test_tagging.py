import pytest

from app.jobs.store import normalize_url
from app.services.tagging import Tagger

JAVA, JS, AI, PY, GO, CPP, CSHARP, SEC, REACT, K8S = range(1, 11)

TAGGER = Tagger.from_aliases(
    [
        (JAVA, "java", False),
        (JS, "javascript", False),
        (JS, "js", True),
        (AI, "ai", False),
        (AI, "인공지능", False),
        (PY, "python", False),
        (PY, "파이썬", False),
        (GO, "golang", False),
        (GO, "go", True),
        (CPP, "c++", False),
        (CPP, "cpp", True),
        (CSHARP, "c#", False),
        (SEC, "보안", False),
        (REACT, "reactjs", False),
        (REACT, "react", True),
        (K8S, "kubernetes", False),
        (K8S, "k8s", False),
    ]
)


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("JavaScript runtimes compared", {JS}),  # "java" must not match inside "javascript"
        ("Java 25 released", {JAVA}),
        ("OpenAI announces a new model", set()),  # "ai" must not match inside "OpenAI"
        ("AI가 바꾸는 개발 문화", {AI}),  # Hangul particle right after the word
        ("파이썬은 왜 느릴까", {PY}),
        ("Let's go to the conference", set()),  # tag-only alias in free text
        ("Golang generics deep dive", {GO}),
        ("C++26 features", {CPP}),
        ("Modern C# patterns", {CSHARP}),
        ("정보보안 동향", {SEC}),
        ("React hooks explained", set()),  # "react" is tag-only (common English verb)
        ("Running K8s at home", {K8S}),
    ],
)
def test_text_matches_whole_words_only(title, expected):
    assert TAGGER.match(title, None, []) == expected


def test_source_tags_use_tag_only_aliases_and_ignore_versions():
    assert TAGGER.match("Untitled", None, ["go", "#React", "python-3.x", "cpp"]) == {
        GO,
        REACT,
        PY,
        CPP,
    }


def test_excerpt_is_searched_too():
    assert TAGGER.match("Weekly notes", "Kubernetes와 파이썬 이야기", []) == {K8S, PY}


@pytest.mark.parametrize(
    ("url", "normalized"),
    [
        ("https://News.Example.com/a?utm_source=rss&id=3#top", "https://news.example.com/a?id=3"),
        ("https://example.com", "https://example.com/"),
        ("https://example.com/p?fbclid=x", "https://example.com/p"),
    ],
)
def test_normalize_url_drops_tracking_and_fragments(url, normalized):
    assert normalize_url(url) == normalized
