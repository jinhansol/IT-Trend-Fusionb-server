"""Test doubles for the collector: answers fetches from stored sample files."""

from pathlib import Path

from app.integrations.http import FetchError

FIXTURES = Path(__file__).parent / "fixtures" / "collect"


def fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


class FakeFetcher:
    """routes: {url: file name | bytes | Exception | callable(params) -> bytes}."""

    def __init__(self, routes: dict) -> None:
        self.routes = routes
        self.calls: list[tuple[str, dict | None]] = []

    def get(self, url: str, params: dict | None = None) -> bytes:
        self.calls.append((url, params))
        answer = self.routes.get(url)
        if answer is None:
            raise FetchError(f"HTTP 404 from {url}")
        if isinstance(answer, Exception):
            raise answer
        if callable(answer):
            return answer(params)
        return fixture(answer) if isinstance(answer, str) else answer


# --- a small catalog for integration tests ------------------------------------------------

TECHNOLOGIES = {
    "technologies": [
        {"slug": "python", "name": "Python", "kind": "language", "aliases": ["python", "파이썬"]},
        {"slug": "java", "name": "Java", "kind": "language", "aliases": ["java"]},
        {"slug": "kotlin", "name": "Kotlin", "kind": "language", "aliases": ["kotlin"]},
        {
            "slug": "javascript",
            "name": "JavaScript",
            "kind": "language",
            "aliases": ["javascript"],
            "tag_aliases": ["js"],
        },
        {
            "slug": "react",
            "name": "React",
            "kind": "library",
            "aliases": ["reactjs"],
            "tag_aliases": ["react"],
        },
        {"slug": "rust", "name": "Rust", "kind": "language", "aliases": ["rust"]},
        {
            "slug": "kubernetes",
            "name": "Kubernetes",
            "kind": "tool",
            "aliases": ["kubernetes", "쿠버네티스"],
        },
        {"slug": "security", "name": "보안", "kind": "field", "aliases": ["보안", "랜섬웨어"]},
        {"slug": "backend", "name": "백엔드", "kind": "field", "aliases": ["backend", "rest api"]},
    ]
}

SOURCES = {
    "sources": [
        {
            "slug": "sample-news",
            "name": "Sample News",
            "kind": "news",
            "adapter": "rss",
            "language": "ko",
            "site_url": "https://news.example.com/",
            "feed_url": "https://news.example.com/rss",
        },
        {
            "slug": "devto",
            "name": "DEV Community",
            "kind": "blog",
            "adapter": "devto",
            "language": "en",
            "site_url": "https://dev.to/",
            "options": {"top_days": 7},
            "channel": "devto",
            "channel_name": "DEV Community",
        },
        {
            "slug": "hackernews",
            "name": "Hacker News",
            "kind": "community",
            "adapter": "hackernews",
            "language": "en",
            "site_url": "https://news.ycombinator.com/",
            "channel": "hackernews",
            "channel_name": "Hacker News",
        },
        {
            "slug": "stackoverflow",
            "name": "Stack Overflow",
            "kind": "qna",
            "adapter": "stackoverflow",
            "language": "en",
            "site_url": "https://stackoverflow.com/",
            "channel": "stackoverflow",
            "channel_name": "Stack Overflow",
        },
        {
            "slug": "sample-blog",
            "name": "Sample Blog",
            "kind": "blog",
            "adapter": "rss",
            "language": "ko",
            "site_url": "https://blog.example.com/",
            "feed_url": "https://blog.example.com/atom",
            "channel": "kr-techblog",
            "channel_name": "국내 기술블로그",
        },
    ]
}


def sample_routes() -> dict:
    from app.integrations.sources import DEVTO_ARTICLES, HN_SEARCH, SE_QUESTIONS

    return {
        "https://news.example.com/rss": "news.rss.xml",
        "https://blog.example.com/atom": "blog.atom.xml",
        DEVTO_ARTICLES: lambda params: fixture(
            "devto_top.json" if "top" in params else "devto_latest.json"
        ),
        HN_SEARCH: "hn_front_page.json",
        SE_QUESTIONS: "so_hot.json",
    }


def seed_catalog(engine, technologies=TECHNOLOGIES, sources=SOURCES) -> None:
    from app.content_loader.taxonomy import (
        SourcesFile,
        TechnologiesFile,
        apply_sources,
        apply_technologies,
    )
    from app.db.session import create_session_factory

    with create_session_factory(engine).begin() as db:
        apply_technologies(db, TechnologiesFile.model_validate(technologies))
        apply_sources(db, SourcesFile.model_validate(sources))


def collect_all(engine, routes=None):
    from app.integrations.sources import adapters
    from app.jobs.runner import Collector

    collector = Collector(engine, FakeFetcher(routes or sample_routes()), adapters())
    return {s.slug: collector.run(s) for s in collector.sources()}
