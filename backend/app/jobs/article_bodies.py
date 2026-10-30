"""Article bodies for the summary job, fetched from the one source whose pages may be used.

Only web.dev blog posts (CC BY 4.0, checked on every page) are fetched. The address
comes from the stored item, never from a user, and must be https://web.dev/blog/<slug>
(optionally ?hl=en); the fetcher refuses any other host, redirects included. A page is
used only when it carries the CC BY 4.0 notice, its canonical URL is the item's address
and its title is the item's title. Anything else returns None: nothing is sent to the
model and the card stays as it is.

Items whose summary is already final (done, skipped, or failed MAX_ATTEMPTS times) are not
fetched again.
"""

import html
import re
from collections.abc import Callable
from urllib.parse import urlsplit

from sqlalchemy import Engine, or_, select

from app.integrations.http import Fetcher, FetchError
from app.jobs.summarize import MAX_ATTEMPTS, Body
from app.models.content import Content, ContentSummary

WEBDEV_HOSTS = frozenset({"web.dev"})
_WEBDEV_PATH = re.compile(r"^/blog/[a-z0-9][a-z0-9-]{0,150}$")
_LICENSE = re.compile(
    r'licensed under the <a href="https://creativecommons\.org/licenses/by/4\.0/">'
    r"Creative Commons Attribution 4\.0 License</a>"
)
_TITLE = re.compile(r'<h1 class="devsite-page-title"[^>]*>(.*?)(?:<devsite-actions|</h1>)', re.S)
_CANONICAL = re.compile(r'<meta property="og:url" content="([^"]+)"')
_BODY_START = '<div class="devsite-article-body'
_BODY_END = '<div class="devsite-floating-action-buttons">'
_DROP = (
    re.compile(r'<div class="wd-authors".*?(?=<p class="wd-pubdates")', re.S),
    re.compile(r'<p class="wd-pubdates".*?</p>', re.S),
    re.compile(r"<(script|style)\b.*?</\1>", re.S | re.I),
)


def _plain(text: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", text)).split())


def webdev_address(url: str) -> str | None:
    """The page to fetch for a stored web.dev item, or None if the address is not one."""
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.netloc != "web.dev" or parts.fragment:
        return None
    if not _WEBDEV_PATH.match(parts.path) or parts.query not in ("", "hl=en"):
        return None
    return f"https://web.dev{parts.path}"


def webdev_body(page: str, url: str, title: str) -> str | None:
    """The article body of a saved web.dev page, if it is the item's article and licensed."""
    if not _LICENSE.search(page):
        return None
    canonical = _CANONICAL.search(page)
    if canonical is None or webdev_address(html.unescape(canonical.group(1))) != url:
        return None
    heading = _TITLE.search(page)
    if heading is None or _plain(heading.group(1)).casefold() != _plain(title).casefold():
        return None
    start = page.find(_BODY_START)
    end = page.find(_BODY_END, start)
    if start < 0 or end < 0:
        return None
    body = page[start:end]
    for pattern in _DROP:
        body = pattern.sub("", body)
    return body


def finished_ids(engine: Engine) -> set[int]:
    with engine.connect() as connection:
        return set(
            connection.scalars(
                select(ContentSummary.content_id).where(
                    or_(
                        ContentSummary.status.in_(("done", "skipped")),
                        ContentSummary.attempts >= MAX_ATTEMPTS,
                    )
                )
            )
        )


def webdev_bodies(
    fetcher: Fetcher, finished: set[int], log: Callable[[str], None] = print
) -> Callable[[Content], Body | None]:
    """A BodyProvider for summarize_contents. fetcher must be limited to WEBDEV_HOSTS."""

    def body(item: Content) -> Body | None:
        if item.source.slug != "webdev" or item.id in finished:
            return None
        address = webdev_address(item.url)
        if address is None:
            log(f"  skipped (address not allowed): {item.url}")
            return None
        try:
            page = fetcher.get(address).decode("utf-8", errors="replace")
        except FetchError as exc:
            log(f"  body not fetched: {exc}")
            return None
        found = webdev_body(page, address, item.title)
        if found is None:
            log(f"  body not used (license, address or title check failed): {address}")
            return None
        return ("html", found)

    return body
