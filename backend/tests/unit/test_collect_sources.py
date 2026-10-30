import json
from datetime import datetime

import pytest

from app.integrations.http import FetchError
from app.integrations.sources import (
    DEVTO_ARTICLES,
    HN_SEARCH,
    SE_QUESTIONS,
    SkipEntry,
    SourceConfig,
    checked_url,
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
    batch = parse_feed(fixture("news.rss.xml"), limit=30)
    items = batch.items

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
    assert batch.skipped == {"no link": 1}


def test_atom_feed_and_limit():
    items = parse_feed(fixture("blog.atom.xml"), limit=30).items
    assert items[0].title == "쿠버네티스 위에서 Spring Boot 무중단 배포하기"
    assert items[0].author == "김개발"
    assert items[0].excerpt.startswith("Kubernetes와 Spring Boot로")
    assert len(parse_feed(fixture("news.rss.xml"), limit=2).items) == 2


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
    items = collect_devto(fetcher, config("devto", {"top_days": 7}, max_items=20)).items

    assert [c[1] for c in fetcher.calls] == [{"per_page": 20}, {"per_page": 20, "top": 7}]
    by_id = {i.external_id: i for i in items}
    assert set(by_id) == {"1001", "1002", "1003"}
    assert by_id["1002"].score == 42  # the later (top) response wins
    assert by_id["1001"].score == 3 and by_id["1001"].comment_count == 0  # real zero, not None
    assert by_id["1003"].tags == ["react", "javascript", "webdev"]
    assert by_id["1003"].published_at == datetime(2026, 10, 22, 9, 0)


def test_hackernews_uses_the_discussion_page_for_text_posts():
    fetcher = FakeFetcher({HN_SEARCH: "hn_front_page.json"})
    items = collect_hackernews(fetcher, config("hackernews", {"tags": "front_page"})).items

    assert fetcher.calls[0][1] == {"tags": "front_page", "hitsPerPage": 30}
    show, ask = items
    assert show.url == "https://github.com/example/tinydb" and show.score == 312
    assert ask.url == "https://news.ycombinator.com/item?id=45000002"
    assert ask.excerpt == "I keep starting with Go & Python tutorials..."


def test_stackoverflow_decodes_titles_and_keeps_the_key_out_of_results():
    fetcher = FakeFetcher({SE_QUESTIONS: "so_hot.json"})
    items = collect_stackoverflow(
        fetcher, config("stackoverflow", {"sort": "hot"}, 10), key="k"
    ).items

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


# --- one bad entry never costs the rest ---------------------------------------------------

BAD_FEED = (
    b"""<?xml version="1.0"?>
<rss version="2.0"><channel><title>t</title>
  <item><title>good one</title><link>https://news.example.com/a/1</link></item>
  <item><title>script link</title><link>javascript:alert(1)</link></item>
  <item><title>data link</title><link>data:text/html,hi</link></item>
  <item><title>ftp link</title><link>ftp://news.example.com/a/2</link></item>
  <item><title>relative link</title><link>/a/3</link></item>
  <item><title></title><link>https://news.example.com/a/4</link></item>
  <item><title>too long</title><link>https://news.example.com/"""
    + b"x" * 2100
    + b"""</link></item>
  <item><title>good two</title><link>https://news.example.com/a/5</link></item>
</channel></rss>"""
)


def test_rss_skips_unusable_entries_and_counts_why():
    batch = parse_feed(BAD_FEED, limit=30)

    assert [i.title for i in batch.items] == ["good one", "good two"]
    assert batch.skipped == {
        "link is not http(s)": 4,
        "no title": 1,
        "link too long": 1,
    }


def test_the_limit_counts_usable_entries_only():
    batch = parse_feed(BAD_FEED, limit=2)
    assert [i.title for i in batch.items] == ["good one", "good two"]


def devto(*articles):
    return FakeFetcher({DEVTO_ARTICLES: json.dumps(list(articles)).encode()})


def article(i, **overrides):
    base = {
        "id": i,
        "title": f"Post {i}",
        "url": f"https://dev.to/u/post-{i}",
        "description": "d",
        "published_at": "2026-10-22T09:00:00Z",
        "tag_list": ["python"],
        "public_reactions_count": 1,
        "comments_count": 0,
        "user": {"name": "Writer"},
    }
    base.update(overrides)
    return {k: v for k, v in base.items() if v is not ...}


def test_devto_skips_broken_articles_and_keeps_the_rest():
    batch = collect_devto(
        devto(
            article(1),
            article(2, url=...),  # field missing
            article(3, url="javascript:alert(1)"),
            article(4, id=...),
            article(5, title=None),
            "not an object",
            article(6, user="someone", published_at="yesterday", public_reactions_count="many"),
        ),
        config("devto"),
    )

    assert [i.external_id for i in batch.items] == ["1", "6"]
    odd = batch.items[1]
    # Unreadable optional fields become "not provided" instead of failing the entry.
    assert (odd.author, odd.published_at, odd.score) == (None, None, None)
    assert batch.skipped == {
        "no link": 1,
        "link is not http(s)": 1,
        "no id": 1,
        "no title": 1,
        "malformed entry": 1,
    }


def test_devto_error_object_instead_of_a_list_fails_the_source():
    fetcher = FakeFetcher({DEVTO_ARTICLES: b'{"error": "rate limited", "status": 429}'})
    with pytest.raises(FetchError, match="unexpected response"):
        collect_devto(fetcher, config("devto"))


def test_hackernews_skips_hits_without_id_or_title():
    body = {
        "hits": [
            {"objectID": "1", "title": "Show HN: ok", "url": "https://example.org/x"},
            {"title": "no id and no url"},
            {"objectID": "3", "title": None},
            {"objectID": "4", "title": "bad link", "url": "javascript:void(0)"},
        ]
    }
    fetcher = FakeFetcher({HN_SEARCH: json.dumps(body).encode()})
    batch = collect_hackernews(fetcher, config("hackernews"))

    assert [i.external_id for i in batch.items] == ["1"]
    assert batch.skipped == {"no id": 1, "no title": 1, "link is not http(s)": 1}


def test_hackernews_without_a_hit_list_fails_the_source():
    fetcher = FakeFetcher({HN_SEARCH: b'{"hits": "oops"}'})
    with pytest.raises(FetchError, match="unexpected response"):
        collect_hackernews(fetcher, config("hackernews"))


def test_stackoverflow_keeps_negative_scores_and_skips_questions_without_a_link():
    body = {
        "items": [
            {"question_id": 1, "title": "q1", "link": "https://stackoverflow.com/q/1", "score": -2},
            {"question_id": 2, "title": "q2"},
        ]
    }
    fetcher = FakeFetcher({SE_QUESTIONS: json.dumps(body).encode()})
    batch = collect_stackoverflow(fetcher, config("stackoverflow"))

    assert [(i.external_id, i.score) for i in batch.items] == [("1", -2)]
    assert batch.skipped == {"no link": 1}


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "JAVASCRIPT:alert(1)",
        "data:text/html,x",
        "vbscript:x",
        "ftp://example.com/a",
        "mailto:a@example.com",
        "//example.com/a",
        "/a/b",
        "https://",
        "https://exa mple.com/a",
        "https://example.com/a\nb",
        "",
        None,
        42,
    ],
)
def test_checked_url_refuses_anything_but_absolute_http_links(url):
    with pytest.raises(SkipEntry):
        checked_url(url)


def test_checked_url_keeps_the_link_as_given():
    url = "  HTTPS://Example.com/a?utm_source=x#frag  "
    assert checked_url(url) == url.strip()  # normalizing is the store's job
