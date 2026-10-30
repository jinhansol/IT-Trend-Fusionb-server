"""normalize_url on synthetic links: pins today's behaviour, including the known risks.

The normalized URL is what contents.url stores and what the card links to, and its
hash is the de-duplication key. Changing the function changes existing hashes, so
these tests fail loudly if it changes by accident.
"""

import pytest

from app.jobs.store import normalize_url, url_hash


@pytest.mark.parametrize(
    ("url", "normalized"),
    [
        # Equivalent rewrites: same page.
        ("https://Example.com/CasePath?X=Y", "https://example.com/CasePath?X=Y"),
        ("https://example.com", "https://example.com/"),
        ("https://example.com/a?", "https://example.com/a"),
        ("https://example.com/a?q=가", "https://example.com/a?q=%EA%B0%80"),
        ("https://example.com/a?q=hello%20world", "https://example.com/a?q=hello+world"),
        # Kept exactly: order, repeated keys, encoded + and /, unknown parameters.
        ("https://example.com/a?b=2&a=1", "https://example.com/a?b=2&a=1"),
        ("https://example.com/a?tag=x&tag=y", "https://example.com/a?tag=x&tag=y"),
        ("https://example.com/a?q=a+b", "https://example.com/a?q=a+b"),
        ("https://example.com/a?q=%2B1", "https://example.com/a?q=%2B1"),
        ("https://example.com/p%2Fq?x=1", "https://example.com/p%2Fq?x=1"),
        ("https://example.com/a?ref=hn", "https://example.com/a?ref=hn"),
        (
            "https://medium.com/daangn/post-1?source=rss----abc---4",
            "https://medium.com/daangn/post-1?source=rss----abc---4",
        ),
        (
            "https://example.com/a?next=https%3A%2F%2Fb.com%2F%3Fz%3D1",
            "https://example.com/a?next=https%3A%2F%2Fb.com%2F%3Fz%3D1",
        ),
        # Tracking parameters and fragments are dropped on purpose.
        ("https://example.com/a?utm_source=rss&id=5", "https://example.com/a?id=5"),
        ("https://example.com/a?REF_SRC=twsrc", "https://example.com/a"),
        ("https://example.com/a#section", "https://example.com/a"),
    ],
)
def test_normalize_url_rewrites(url, normalized):
    assert normalize_url(url) == normalized


@pytest.mark.parametrize(
    ("url", "normalized"),
    [
        # Known risks (design v2, section 6.1). The link may stop working if a site relies on
        # them. Not yet seen in collected data (none collected); kept until measured.
        ("https://example.com/a?flag", "https://example.com/a?flag="),
        ("https://example.com/a?x=1;y=2", "https://example.com/a?x=1%3By%3D2"),
        ("https://example.com/#/post/1", "https://example.com/"),
    ],
)
def test_normalize_url_known_risks_are_unchanged(url, normalized):
    assert normalize_url(url) == normalized


def test_tracking_variants_share_one_hash():
    variants = [
        "https://news.example.com/articles/1",
        "https://NEWS.example.com/articles/1?utm_source=rss&utm_medium=feed",
        "https://news.example.com/articles/1?fbclid=abc#comments",
    ]
    assert len({url_hash(normalize_url(u)) for u in variants}) == 1
