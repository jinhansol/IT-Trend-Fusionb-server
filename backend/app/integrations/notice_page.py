"""Title and publish time of one fixed notice page, from its HTML before any script runs.

For a single reviewed page in a manual trial (app/jobs/trial.py), not a crawler: no
links are followed and nothing else on the page is read. The page must be a Next.js
page whose embedded __NEXT_DATA__ holds the notice as `{"title": ..., "createdAt": ...}`
under a query keyed by the page's own notice id, and whose rendered markup shows the
same title. Anything missing or different fails (FetchError): the structure is the
contract, and a changed site must be looked at again, not guessed.
"""

import json
import re
from datetime import UTC, datetime
from html import unescape
from html.parser import HTMLParser

from app.integrations.http import FetchError

_NEXT_DATA = re.compile(
    r'<script[^>]*\bid="__NEXT_DATA__"[^>]*>(.*?)</script>', re.DOTALL | re.IGNORECASE
)
TITLE_CHARS = 500


class _VisibleText(HTMLParser):
    """Text outside <script>/<style>, to check the title is really shown."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def _spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _parse_time(value) -> datetime:
    if not isinstance(value, str):
        raise FetchError("notice page: no publish time")
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise FetchError("notice page: unreadable publish time") from None
    if moment.tzinfo is None:
        raise FetchError("notice page: publish time without a time zone")
    return moment.astimezone(UTC).replace(tzinfo=None)  # stored as naive UTC


def parse_notice(html: bytes, notice_id: str) -> tuple[str, datetime]:
    """(title, published_at) of the notice `notice_id`, or FetchError."""
    text = html.decode("utf-8", "replace")
    match = _NEXT_DATA.search(text)
    if not match:
        raise FetchError("notice page: no __NEXT_DATA__")
    try:
        data = json.loads(match.group(1))
    except ValueError:
        raise FetchError("notice page: unreadable __NEXT_DATA__") from None
    if str((data.get("query") or {}).get("noticeId")) != notice_id:
        raise FetchError("notice page: notice id does not match the URL")
    queries = (((data.get("props") or {}).get("pageProps") or {}).get("dehydratedState") or {}).get(
        "queries"
    ) or []
    found = [
        q["state"]["data"]
        for q in queries
        if isinstance(q, dict)
        and any(
            isinstance(part, dict) and str(part.get("noticeId")) == notice_id
            for part in (q.get("queryKey") or [])
        )
        and isinstance((q.get("state") or {}).get("data"), dict)
    ]
    if len(found) != 1:
        raise FetchError("notice page: expected exactly one notice record")
    notice = found[0]
    title = notice.get("title")
    if not isinstance(title, str) or not _spaces(title):
        raise FetchError("notice page: no title")
    title = _spaces(unescape(title))[:TITLE_CHARS]
    visible = _VisibleText()
    visible.feed(text)
    if title not in _spaces(" ".join(visible.parts)):
        raise FetchError("notice page: title is not shown on the page")
    return title, _parse_time(notice.get("createdAt"))


def notice_id_from(url: str) -> str:
    """The trailing numeric id of a notice URL (".../notices/1676" -> "1676")."""
    match = re.search(r"/(\d+)/?$", url)
    if not match:
        raise FetchError("notice URL has no trailing numeric id")
    return match.group(1)
