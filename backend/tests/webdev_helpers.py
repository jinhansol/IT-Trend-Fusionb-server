"""Synthetic web.dev-style pages and the web.dev source entry for the article-body tests.

The page copies only the markup the body provider looks at (title, canonical URL, article
body, author and date blocks, license footer); the article text is the synthetic E1 Dev
fixture. Nothing here is real web.dev content.
"""

import copy
import re

from app.content_loader.taxonomy import read_sources
from tests.collect_helpers import SOURCES
from tests.conftest import BACKEND_DIR
from tests.summary_helpers import article

FEED_URL = "https://web.dev/static/blog/feed.xml"
FIRST = "https://web.dev/blog/sample-virtual-threads?hl=en"
FIRST_PAGE = "https://web.dev/blog/sample-virtual-threads"
FIRST_TITLE = "Virtual threads in a sample Spring service"
SECOND = "https://web.dev/blog/sample-second-post?hl=en"
SECOND_PAGE = "https://web.dev/blog/sample-second-post"
SECOND_TITLE = "A second sample post"
LICENSE = (
    "<p>Except as otherwise noted, the content of this page is licensed under the "
    '<a href="https://creativecommons.org/licenses/by/4.0/">Creative Commons Attribution '
    "4.0 License</a>, and code samples are licensed under the Apache 2.0 License.</p>"
)


def article_body() -> str:
    return re.search(r"<body>(.*)</body>", article("dev_spring.html"), re.S).group(1)


def page(slug: str, title: str, body: str | None = None, license: bool = True) -> bytes:
    text = f"""<!doctype html><html><head>
<title>{title} &nbsp;|&nbsp; Blog &nbsp;|&nbsp; web.dev</title>
<meta property="og:url" content="https://web.dev/blog/{slug}">
<script>window.tracking = "nav";</script></head><body>
<nav>Home Blog Learn Explore</nav>
<article class="devsite-article">
<h1 class="devsite-page-title" tabindex="-1">
  {title}<devsite-actions hidden><span>Save and categorize content</span></devsite-actions></h1>
<div class="devsite-article-body clearfix">
<div class="wd-authors" translate="no"><div class="wd-author"><div><span>Sample Author</span>
<a href="https://social.example.com/sample">Sample Author on X</a></div></div></div>
<p class="wd-pubdates">Published: October 29, 2026</p>
{body if body is not None else article_body()}
<style>.share {{ color: red; }}</style>
</div>
<div class="devsite-floating-action-buttons"></div></article>
<footer>{LICENSE if license else "<p>All rights reserved.</p>"}
<a href="https://social.example.com/share">Share</a></footer>
</body></html>"""
    return text.encode("utf-8")


def webdev_source() -> dict:
    """The web.dev entry exactly as content/sources.yaml has it."""
    sources = read_sources(BACKEND_DIR / "content" / "sources.yaml").sources
    entry = next(s for s in sources if s.slug == "webdev")
    return entry.model_dump()


def sources() -> dict:
    data = copy.deepcopy(SOURCES)
    data["sources"].append(webdev_source())
    return data
