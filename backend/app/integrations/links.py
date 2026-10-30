"""The one link check shared by the collector and the summarizer. Pure: no network."""

from urllib.parse import urlsplit

URL_CHARS = 2048  # contents.url; a longer link is skipped, never cut


class SkipEntry(Exception):
    """This entry cannot be stored; the reason is counted, the rest of the feed goes on."""


def checked_url(value) -> str:
    """The link as given, if it is an absolute http(s) address that fits the column."""
    if not isinstance(value, str) or not value.strip():
        raise SkipEntry("no link")
    url = value.strip()
    if len(url) > URL_CHARS:
        raise SkipEntry("link too long")
    if any(ch.isspace() or ord(ch) < 32 or ord(ch) == 127 for ch in url):
        raise SkipEntry("invalid link")
    try:
        parts = urlsplit(url)
    except ValueError:
        raise SkipEntry("invalid link") from None
    if parts.scheme.lower() not in ("http", "https") or not parts.hostname:
        raise SkipEntry("link is not http(s)")
    return url
