from datetime import datetime

import pytest

from app.integrations.http import FetchError
from app.integrations.sources import (
    DEVTO_ARTICLES,
    HN_SEARCH,
    SE_QUESTIONS,
    SourceConfig,
    collect_devto,
    collect_hackernews,
    collect_stackoverflow,
    parse_feed,
    plain_text,
)
from tests.collect_helpers import FakeFetcher, fixture


def config(adapter="rss", options=None, max_items=30, feed_url="https://x.test/feed"):
    return SourceConfig(
        adapter=adapter, feed_url=feed_url, options=options or {}, max_items=max_items
    )


def test_rss_items_are_plain_text_with_utc_dates():
    items = parse_feed(fixture("news.rss.xml"), limit=30)

    first = items[0]
    assert first.title == '파이썬 3.14 출시, "free-threaded" 정식 지원'
    assert first.excerpt == "Python 3.14가 정식 출시됐다. 새 버전은 GIL 없는 빌드를 지원한다."
    assert first.author == "홍길동"
    assert first.published_at == datetime(2026, 10, 27, 0, 30)  # 09:30 KST
    assert first.tags == ["개발"]
    assert first.score is None and first.comment_count is None  # feeds have no metrics

    titles = [i.title for i in items]
    assert "링크 없는 항목은 건너뜀" not in titles
    undated = next(i for i in items if i.title.startswith("발행일 없는"))
    assert undated.published_at is None


def test_atom_feed_and_limit():
    items = parse_feed(fixture("blog.atom.xml"), limit=30)
    assert items[0].title == "쿠버네티스 위에서 Spring Boot 무중단 배포하기"
    assert items[0].author == "김개발"
    assert items[0].excerpt.startswith("Kubernetes와 Spring Boot로")
    assert len(parse_feed(fixture("news.rss.xml"), limit=2)) == 2


def test_unreadable_feed_is_an_error():
    with pytest.raises(FetchError):
        parse_feed(fixture("broken.xml"), limit=30)


def test_plain_text_shortens_on_a_word_boundary():
    text = plain_text("<p>" + "word " * 100 + "</p>", limit=30)
    assert len(text) <= 31 and text.endswith("…") and "  " not in text


def test_devto_merges_latest_and_top_without_duplicates():
    fetcher = FakeFetcher(
        {
            DEVTO_ARTICLES: lambda params: fixture(
                "devto_top.json" if "top" in params else "devto_latest.json"
            )
        }
    )
    items = collect_devto(fetcher, config("devto", {"top_days": 7}, max_items=20))

    assert [c[1] for c in fetcher.calls] == [{"per_page": 20}, {"per_page": 20, "top": 7}]
    by_id = {i.external_id: i for i in items}
    assert set(by_id) == {"1001", "1002", "1003"}
    assert by_id["1002"].score == 42  # the later (top) response wins
    assert by_id["1001"].score == 3 and by_id["1001"].comment_count == 0  # real zero, not None
    assert by_id["1003"].tags == ["react", "javascript", "webdev"]
    assert by_id["1003"].published_at == datetime(2026, 10, 22, 9, 0)


def test_hackernews_uses_the_discussion_page_for_text_posts():
    fetcher = FakeFetcher({HN_SEARCH: "hn_front_page.json"})
    items = collect_hackernews(fetcher, config("hackernews", {"tags": "front_page"}))

    assert fetcher.calls[0][1] == {"tags": "front_page", "hitsPerPage": 30}
    show, ask = items
    assert show.url == "https://github.com/example/tinydb" and show.score == 312
    assert ask.url == "https://news.ycombinator.com/item?id=45000002"
    assert ask.excerpt == "I keep starting with Go & Python tutorials..."


def test_stackoverflow_decodes_titles_and_keeps_the_key_out_of_results():
    fetcher = FakeFetcher({SE_QUESTIONS: "so_hot.json"})
    items = collect_stackoverflow(fetcher, config("stackoverflow", {"sort": "hot"}, 10), key="k")

    assert fetcher.calls[0][1] == {
        "site": "stackoverflow",
        "sort": "hot",
        "order": "desc",
        "pagesize": 10,
        "key": "k",
    }
    first = items[0]
    assert first.title == 'Why does asyncio.gather "hang" with a semaphore?'
    assert first.author == "Frank & Co"
    assert (first.score, first.comment_count, first.view_count) == (27, 3, 1520)
    assert first.tags == ["python-3.x", "asyncio"]


def test_stackexchange_error_body_is_an_error():
    fetcher = FakeFetcher({SE_QUESTIONS: b'{"error_id": 502, "error_name": "throttle_violation"}'})
    with pytest.raises(FetchError, match="throttle_violation"):
        collect_stackoverflow(fetcher, config("stackoverflow"))
