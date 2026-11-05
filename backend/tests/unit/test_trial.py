"""Manual trial (app/jobs/trial.py) with synthetic fixtures and test doubles only.

No request leaves the process and no database is reached: fetches are answered by
FakeFetcher or httpx.MockTransport, connections and sessions are small fakes.
"""

import contextlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
import yaml
from sqlalchemy.engine import make_url

from app.integrations.http import FetchError, HttpFetcher
from app.integrations.notice_page import notice_id_from, parse_notice
from app.jobs import __main__ as cli
from app.jobs import trial
from app.models.content import ContentSource
from app.services.source_terms import collect_refusal
from tests.collect_helpers import FakeFetcher
from tests.conftest import BACKEND_DIR, make_settings

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "trial"
NOTICE_URL = "https://cloud.example.invalid/more/notices/1001"
FEED_URL = "https://devlog.example.invalid/feed.xml"
TARGET = "https://devlog.example.invalid/posts/kafka-delivery/"
CLOUD_ROBOTS = "https://cloud.example.invalid/robots.txt"
DEVLOG_ROBOTS = "https://devlog.example.invalid/robots.txt"
INSIDE = datetime(2026, 10, 22, tzinfo=UTC)
ALLOW = b"User-agent: *\nAllow: /\n"


def raw_manifest() -> dict:
    return yaml.safe_load((FIXTURES / "manifest.example.yaml").read_text(encoding="utf-8"))


def manifest(**changes) -> trial.Manifest:
    data = raw_manifest()
    data.update(changes)
    return trial.Manifest.model_validate(data)


def item_changed(index: int, **changes) -> dict:
    data = raw_manifest()
    data["items"][index].update(changes)
    return data


def fetch(m, fetcher, clock=lambda: INSIDE):
    """fetch_items inside the example window (it ended on 2026-10-23)."""
    return trial.fetch_items(m, fetcher, clock)


def routes(**overrides) -> dict:
    answers = {
        CLOUD_ROBOTS: ALLOW,
        DEVLOG_ROBOTS: ALLOW,
        NOTICE_URL: (FIXTURES / "notice.html").read_bytes(),
        FEED_URL: (FIXTURES / "feed.atom.xml").read_bytes(),
    }
    answers.update(overrides)
    return answers


# --- the manifest and its window: refused before any request ------------------------------


def test_the_example_manifest_is_valid():
    m = manifest()
    assert [i.kind for i in m.items] == ["notice_page", "atom_entry"]
    assert trial.input_hosts(m) == {"cloud.example.invalid", "devlog.example.invalid"}


@pytest.mark.parametrize(
    ("now", "code"),
    [
        (datetime(2026, 10, 23, tzinfo=UTC), "trial_expired"),
        (datetime(2026, 11, 4, tzinfo=UTC), "trial_expired"),
        (datetime(2026, 10, 20, 23, 59, tzinfo=UTC), "trial_not_started"),
    ],
)
def test_outside_the_window_nothing_is_requested_or_connected(now, code):
    fetcher = FakeFetcher(routes())

    class NoEngine:
        def connect(self):
            raise AssertionError("the database must not be reached")

    with pytest.raises(trial.TrialRefused) as refused:
        trial.run(manifest(), fetcher, engine=NoEngine(), clock=lambda: now)
    assert refused.value.code == code
    assert fetcher.calls == []


@pytest.mark.parametrize(
    "data",
    [
        # the stored URL is not the page read
        item_changed(0, target_url="https://cloud.example.invalid/more/notices/1002"),
        # an Atom entry on another host than its feed
        item_changed(1, target_url="https://elsewhere.example.invalid/posts/kafka-delivery/"),
        # the target is the feed itself
        item_changed(1, target_url=FEED_URL),
        # target missing
        {
            **raw_manifest(),
            "items": [{k: v for k, v in raw_manifest()["items"][0].items() if k != "target_url"}],
        },
        # a notice page has no author or source tags
        item_changed(0, fields=["title", "url", "published_at", "source", "author"]),
        # a required field left out
        item_changed(1, fields=["title", "url", "source"]),
        # a field that does not exist
        item_changed(1, fields=["title", "url", "published_at", "source", "excerpt"]),
        # a notice URL without a numeric id
        item_changed(
            0,
            input_url="https://cloud.example.invalid/n/a",
            target_url="https://cloud.example.invalid/n/a",
        ),
        # plain http, or credentials in the URL
        item_changed(1, input_url="http://devlog.example.invalid/feed.xml"),
        item_changed(1, input_url="https://u:p@devlog.example.invalid/feed.xml"),
        # no usage basis
        item_changed(1, basis=""),
        # longer than 48 hours, or ending before it starts
        {**raw_manifest(), "expires_at": "2026-10-23T00:00:01Z"},
        {**raw_manifest(), "expires_at": "2026-10-21T00:00:00Z"},
        # no time zone
        {**raw_manifest(), "expires_at": "2026-10-22T00:00:00"},
        # another database
        {**raw_manifest(), "database": "devhub_dev"},
        # a slug that is not a trial slug
        item_changed(0, source={**raw_manifest()["items"][0]["source"], "slug": "zdnet-korea"}),
        # an unknown key
        {**raw_manifest(), "extra": 1},
        # three items
        {**raw_manifest(), "items": raw_manifest()["items"] + raw_manifest()["items"][:1]},
    ],
)
def test_invalid_manifests_are_refused(tmp_path, data):
    path = tmp_path / "manifest.yaml"
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    with pytest.raises(trial.TrialRefused) as refused:
        trial.read_manifest(path)
    assert refused.value.code == "invalid_manifest"


def test_a_missing_manifest_file_is_refused(tmp_path):
    with pytest.raises(trial.TrialRefused):
        trial.read_manifest(tmp_path / "absent.yaml")


@pytest.fixture()
def cli_doubles(monkeypatch):
    """The CLI with a recording fetcher and no database: anything reached is recorded."""
    fetcher = FakeFetcher(routes())
    fetcher.close = lambda: None
    reached = []
    monkeypatch.setattr(cli, "HttpFetcher", lambda settings, **kw: fetcher)
    monkeypatch.setattr(cli, "create_db_engine", lambda settings: reached.append("db"))
    monkeypatch.setattr(cli, "get_settings", lambda: make_settings())
    return fetcher, reached


def write(tmp_path, data) -> str:
    path = tmp_path / "manifest.yaml"
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return str(path)


def test_the_cli_refuses_an_expired_manifest_before_anything(tmp_path, cli_doubles, capsys):
    fetcher, reached = cli_doubles  # the example window ended on 2026-10-23
    assert cli.main(["trial", write(tmp_path, raw_manifest())]) == 2
    assert fetcher.calls == [] and reached == []
    assert "trial_expired" in capsys.readouterr().err


def test_the_cli_refuses_a_url_mismatch_before_anything(tmp_path, cli_doubles, capsys):
    fetcher, reached = cli_doubles
    data = item_changed(0, target_url="https://cloud.example.invalid/more/notices/1002")
    assert cli.main(["trial", write(tmp_path, data), "--dry-run"]) == 2
    assert fetcher.calls == [] and reached == []
    assert "invalid_manifest" in capsys.readouterr().err


def test_the_cli_dry_run_reads_without_a_database(tmp_path, cli_doubles, capsys, monkeypatch):
    fetcher, reached = cli_doubles
    now = datetime.now(UTC).replace(microsecond=0)
    data = {
        **raw_manifest(),
        "created_at": (now - timedelta(hours=1)).isoformat(),
        "expires_at": (now + timedelta(hours=1)).isoformat(),
    }
    assert cli.main(["trial", write(tmp_path, data), "--dry-run"]) == 0
    assert reached == []
    assert [url for url, _ in fetcher.calls] == [CLOUD_ROBOTS, NOTICE_URL, DEVLOG_ROBOTS, FEED_URL]
    out = capsys.readouterr().out
    assert "dry run" in out and "4 requests" in out
    assert "Python Rust" not in out and "rebalance" not in out


# --- robots.txt and the request budget ---------------------------------------------------


@pytest.mark.parametrize(
    "robots",
    [
        b"User-agent: *\nDisallow: /more/\n",
        FetchError("HTTP 503", status=503),  # unreachable: refused
        FetchError("ConnectError while fetching", retryable=True),
        FetchError("HTTP 401", status=401),
    ],
)
def test_robots_refusal_requests_no_page_or_feed(robots):
    fetcher = FakeFetcher(routes(**{CLOUD_ROBOTS: robots}))
    with pytest.raises(trial.TrialRefused) as refused:
        fetch(manifest(), fetcher)
    assert refused.value.code == "robots_refused"
    assert [url for url, _ in fetcher.calls] == [CLOUD_ROBOTS]


def test_a_refusal_on_the_second_item_stops_before_its_feed():
    fetcher = FakeFetcher(routes(**{DEVLOG_ROBOTS: b"User-agent: *\nDisallow: /feed.xml\n"}))
    with pytest.raises(trial.TrialRefused):
        fetch(manifest(), fetcher)
    assert FEED_URL not in [url for url, _ in fetcher.calls]


def test_two_requests_per_item_at_most():
    fetcher = FakeFetcher(routes())
    prepared, used = fetch(manifest(), fetcher)
    assert used == 4 == len(fetcher.calls) and len(prepared) == 2

    budget = trial._Budget(FakeFetcher(routes()), 1, before_request=lambda: None)
    budget.get(CLOUD_ROBOTS)
    with pytest.raises(trial.TrialRefused) as refused:
        budget.get(NOTICE_URL)
    assert refused.value.code == "request_limit_reached"


class Server:
    def __init__(self, answers: dict):
        self.answers, self.requests = answers, []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(str(request.url))
        return self.answers[str(request.url)]


@pytest.fixture()
def no_dns(monkeypatch):
    """Host names are synthetic: skip the resolver check made when no proxy is set."""
    monkeypatch.setattr("app.integrations.http.check_resolved", lambda host: None)


def http_fetcher(server) -> HttpFetcher:
    m = manifest()
    return HttpFetcher(
        make_settings(collector_max_response_bytes=1_000_000),
        httpx.MockTransport(server),
        sleep=lambda s: pytest.fail("no retry in a trial"),
        allowed_hosts=trial.input_hosts(m),
        max_attempts=1,
    )


@pytest.mark.usefixtures("no_dns")
def test_a_redirect_of_the_page_is_refused_and_not_followed():
    other = "https://cloud.example.invalid/more/notices/1001/"
    server = Server(
        {
            CLOUD_ROBOTS: httpx.Response(200, content=ALLOW),
            NOTICE_URL: httpx.Response(301, headers={"Location": other}),
        }
    )
    with pytest.raises(FetchError, match="redirect refused"):
        fetch(manifest(), http_fetcher(server))
    assert server.requests == [CLOUD_ROBOTS, NOTICE_URL]


@pytest.mark.usefixtures("no_dns")
def test_a_redirect_of_robots_txt_is_a_refusal():
    server = Server(
        {
            CLOUD_ROBOTS: httpx.Response(
                302, headers={"Location": "https://cloud.example.invalid/r"}
            ),
        }
    )
    with pytest.raises(trial.TrialRefused) as refused:
        fetch(manifest(), http_fetcher(server))
    assert refused.value.code == "robots_refused"
    assert server.requests == [CLOUD_ROBOTS]


@pytest.mark.usefixtures("no_dns")
def test_a_failed_request_is_not_retried():
    server = Server(
        {
            CLOUD_ROBOTS: httpx.Response(200, content=ALLOW),
            NOTICE_URL: httpx.Response(503),
        }
    )
    with pytest.raises(FetchError):
        fetch(manifest(), http_fetcher(server))
    assert server.requests == [CLOUD_ROBOTS, NOTICE_URL]


@pytest.mark.usefixtures("no_dns")
def test_hosts_outside_the_manifest_are_refused_by_the_fetcher():
    server = Server({})
    with pytest.raises(FetchError, match="outside the allowed hosts"):
        http_fetcher(server).get("https://elsewhere.example.invalid/")
    assert server.requests == []


# --- the one target and its allowed fields ----------------------------------------------


def test_the_atom_entry_is_the_one_target_with_only_allowed_fields():
    prepared, _ = fetch(manifest(), FakeFetcher(routes()))
    notice, entry = (collected for _, collected in prepared)

    assert notice.url == NOTICE_URL
    assert notice.title == "'Example Managed Kafka' 버전 추가 안내"
    assert notice.published_at == datetime(2026, 10, 20, 1, 30)

    assert entry.url == TARGET
    assert entry.title and "kafka" in entry.title.lower()
    assert entry.author == "example-author"  # allowed in the example manifest
    assert entry.tags == []  # source_tags not allowed
    assert entry.excerpt is None and entry.external_id is None
    assert (entry.score, entry.comment_count, entry.view_count) == (None, None, None)
    for value in vars(entry).values():
        assert "Python Rust" not in str(value) and "<img" not in str(value)


def test_source_tags_and_author_only_when_allowed():
    data = raw_manifest()
    data["items"][1]["fields"] = ["title", "url", "published_at", "source", "source_tags"]
    m = trial.Manifest.model_validate(data)
    prepared, _ = fetch(m, FakeFetcher(routes()))
    entry = prepared[1][1]
    assert entry.author is None
    assert sorted(entry.tags) == ["Backend", "Kafka"]


def feed_with(entries: list[str]) -> bytes:
    body = "".join(
        f'<entry><title>T{n}</title><link href="{url}"/><id>{url}</id>'
        f"<published>2026-10-01T00:00:00Z</published><updated>2026-10-01T00:00:00Z</updated>"
        f"</entry>"
        for n, url in enumerate(entries)
    )
    return (
        '<?xml version="1.0" encoding="utf-8"?><feed xmlns="http://www.w3.org/2005/Atom">'
        "<title>f</title><id>f</id><updated>2026-10-01T00:00:00Z</updated>"
        f"{body}</feed>"
    ).encode()


@pytest.mark.parametrize(
    "entries",
    [
        ["https://devlog.example.invalid/posts/other/"],  # target missing
        [TARGET, TARGET + "?utm_source=x"],  # two entries normalize to the target
    ],
)
def test_the_target_must_match_exactly_one_entry(entries):
    fetcher = FakeFetcher(routes(**{FEED_URL: feed_with(entries)}))
    with pytest.raises(FetchError, match="exactly one entry"):
        fetch(manifest(), fetcher)


def test_a_tracking_parameter_on_the_entry_still_matches():
    fetcher = FakeFetcher(routes(**{FEED_URL: feed_with([TARGET + "?utm_source=rss"])}))
    prepared, _ = fetch(manifest(), fetcher)
    assert prepared[1][1].url == TARGET


def test_an_entry_without_a_date_fails():
    raw = feed_with([TARGET]).replace(b"<published>2026-10-01T00:00:00Z</published>", b"")
    raw = raw.replace(b"<updated>2026-10-01T00:00:00Z</updated></entry>", b"</entry>")
    with pytest.raises(FetchError, match="no publish time"):
        fetch(manifest(), FakeFetcher(routes(**{FEED_URL: raw})))


# --- the notice page parser -------------------------------------------------------------


def notice_data() -> dict:
    record = {
        "title": "'Example Managed Kafka' 버전 추가 안내",
        "createdAt": "2026-10-20T10:30:00+09:00",
    }
    query = {"queryKey": ["notice", {"noticeId": 1001}], "state": {"data": record}}
    return {
        "query": {"noticeId": "1001"},
        "props": {"pageProps": {"dehydratedState": {"queries": [query]}}},
    }


def notice_html(
    data: dict | None = None,
    shown: str = "'Example Managed Kafka' 버전 추가 안내",
    raw_data: str | None = None,
) -> bytes:
    data = data if data is not None else notice_data()
    script = raw_data if raw_data is not None else json.dumps(data, ensure_ascii=False)
    return (
        f"<html><body><h1>{shown}</h1>"
        f'<script id="__NEXT_DATA__" type="application/json">{script}</script></body></html>'
    ).encode()


def test_the_notice_fixture_parses():
    title, published = parse_notice((FIXTURES / "notice.html").read_bytes(), "1001")
    assert title == "'Example Managed Kafka' 버전 추가 안내"
    assert published == datetime(2026, 10, 20, 1, 30)
    assert parse_notice(notice_html(), "1001")[1] == datetime(2026, 10, 20, 1, 30)


def _with(path: list, value):
    data = notice_data()
    target = data
    for key in path[:-1]:
        target = target[key]
    if value is None:
        del target[path[-1]]
    else:
        target[path[-1]] = value
    return data


_NOTICE = ["props", "pageProps", "dehydratedState", "queries", 0, "state", "data"]


@pytest.mark.parametrize(
    ("html", "message"),
    [
        (b"<html><body><h1>t</h1></body></html>", "no __NEXT_DATA__"),
        (notice_html(raw_data="{not json"), "unreadable"),
        (notice_html(_with(["query", "noticeId"], "1002")), "does not match"),
        (
            notice_html(_with(["props", "pageProps", "dehydratedState", "queries"], [])),
            "exactly one",
        ),
        (notice_html(_with(_NOTICE + ["title"], None)), "no title"),
        (notice_html(_with(_NOTICE + ["title"], "   ")), "no title"),
        (notice_html(_with(_NOTICE + ["createdAt"], None)), "no publish time"),
        (notice_html(_with(_NOTICE + ["createdAt"], "2026-10-20T10:30:00")), "time zone"),
        (notice_html(_with(_NOTICE + ["createdAt"], "yesterday")), "unreadable publish"),
        (notice_html(shown="Another title"), "not shown"),
    ],
)
def test_a_notice_page_without_the_expected_structure_fails(html, message):
    with pytest.raises(FetchError, match=message):
        parse_notice(html, "1001")


def test_two_records_for_the_notice_fail():
    data = _with(["query", "noticeId"], "1001")
    queries = data["props"]["pageProps"]["dehydratedState"]["queries"]
    queries.append(queries[0])
    with pytest.raises(FetchError, match="exactly one"):
        parse_notice(notice_html(data), "1001")


def test_the_title_inside_a_script_does_not_count_as_shown():
    html = notice_html(shown="").replace(
        b"<h1></h1>",
        b"<script>var t=\"'Example Managed Kafka' \xeb\xb2\x84\xec\xa0\x84"
        b' \xec\xb6\x94\xea\xb0\x80 \xec\x95\x88\xeb\x82\xb4"</script>',
    )
    with pytest.raises(FetchError, match="not shown"):
        parse_notice(html, "1001")


@pytest.mark.parametrize(
    ("url", "expected"),
    [("https://a.invalid/notices/1676", "1676"), ("https://a.invalid/notices/1676/", "1676")],
)
def test_notice_ids(url, expected):
    assert notice_id_from(url) == expected


def test_a_url_without_an_id_fails():
    with pytest.raises(FetchError):
        notice_id_from("https://a.invalid/notices/latest")


# --- the database actually connected -----------------------------------------------------


class FakeConnection:
    def __init__(
        self, url: str, database="devhub_experiment", user="devhub_experiment@%", fails=False
    ):
        self.engine = type("E", (), {"url": make_url(url)})()
        self._answers = {"SELECT DATABASE()": database, "SELECT CURRENT_USER()": user}
        self._fails = fails
        self.statements: list[str] = []

    def execute(self, statement):
        self.statements.append(str(statement))
        if self._fails:
            raise RuntimeError("lost connection")
        value = self._answers[str(statement)]
        return type("R", (), {"scalar": lambda self: value})()


GOOD_URL = "mysql+pymysql://devhub_experiment:pw@127.0.0.1:3308/devhub_experiment"


def test_the_experiment_database_and_account_pass():
    connection = FakeConnection(GOOD_URL)
    trial.check_connection(connection)
    assert connection.statements == ["SELECT DATABASE()", "SELECT CURRENT_USER()"]


@pytest.mark.parametrize(
    ("connection", "code"),
    [
        (FakeConnection(GOOD_URL, database="devhub_dev"), "not_the_experiment_database"),
        (FakeConnection(GOOD_URL, database=None), "not_the_experiment_database"),
        (
            FakeConnection(GOOD_URL.replace("/devhub_experiment", "/devhub_test")),
            "not_the_experiment_database",
        ),
        (FakeConnection(GOOD_URL, user="root@localhost"), "not_the_experiment_account"),
        (
            FakeConnection(GOOD_URL.replace("devhub_experiment:pw", "devhub:pw")),
            "not_the_experiment_account",
        ),
        (FakeConnection(GOOD_URL, fails=True), "database_unverified"),
    ],
)
def test_any_other_connection_is_refused(connection, code):
    with pytest.raises(trial.TrialRefused) as refused:
        trial.check_connection(connection)
    assert refused.value.code == code
    assert "pw" not in str(refused.value)


class FakeSession:
    """Records every write-side call; the connection answers like a wrong database."""

    def __init__(self, connection: FakeConnection):
        self._connection = connection
        self.calls: list[str] = []
        self.autoflush_off = False

    @property
    def no_autoflush(self):
        @contextlib.contextmanager
        def off():
            self.autoflush_off = True
            try:
                yield
            finally:
                self.autoflush_off = False

        return off()

    def connection(self):
        self.calls.append(f"connection(autoflush_off={self.autoflush_off})")
        return self._connection

    def __getattr__(self, name):  # add, flush, execute, scalar, scalars ...
        def record(*args, **kwargs):
            self.calls.append(name)
            raise AssertionError(f"{name} reached after a refused connection")

        return record


def test_a_wrong_writing_connection_saves_nothing():
    prepared, _ = fetch(manifest(), FakeFetcher(routes()))
    db = FakeSession(FakeConnection(GOOD_URL, database="devhub_test"))
    taggers = []
    with pytest.raises(trial.TrialRefused) as refused:
        trial.save(db, manifest(), prepared, tagger_for=taggers.append)
    assert refused.value.code == "not_the_experiment_database"
    assert db.calls == ["connection(autoflush_off=True)"]
    assert taggers == []


def test_run_checks_the_database_before_any_request():
    fetcher = FakeFetcher(routes())

    class Engine:
        def connect(self):
            return contextlib.nullcontext(FakeConnection(GOOD_URL, database="devhub_dev"))

    with pytest.raises(trial.TrialRefused) as refused:
        trial.run(manifest(), fetcher, engine=Engine(), sessions=None, clock=lambda: INSIDE)
    assert refused.value.code == "not_the_experiment_database"
    assert fetcher.calls == []


def test_run_treats_an_unreachable_database_as_unverified():
    class Engine:
        def connect(self):
            raise OSError("refused")

    fetcher = FakeFetcher(routes())
    with pytest.raises(trial.TrialRefused) as refused:
        trial.run(manifest(), fetcher, engine=Engine(), sessions=None, clock=lambda: INSIDE)
    assert refused.value.code == "database_unverified"
    assert fetcher.calls == []


# --- the general gate stays as it is -----------------------------------------------------


def test_a_trial_source_row_is_never_collected():
    row = ContentSource(status="paused", options={"terms": "unverified", "trial": "x"})
    assert collect_refusal(row) is not None
    row.status = "active"  # even if someone activates it, the terms gate still refuses
    assert "terms not approved" in collect_refusal(row)


def test_sources_yaml_has_no_trial_entries():
    sources = yaml.safe_load((BACKEND_DIR / "content" / "sources.yaml").read_text("utf-8"))
    assert not [s for s in sources["sources"] if s["slug"].startswith("trial-")]


# --- boundary fixes: URLs and ports, strict robots, expiry during the run ---------------


def window_around_now() -> dict:
    now = datetime.now(UTC).replace(microsecond=0)
    return {
        "created_at": (now - timedelta(hours=1)).isoformat(),
        "expires_at": (now + timedelta(hours=1)).isoformat(),
    }


BAD_URLS = [
    "https://cloud.example.invalid:8443/more/notices/1001",  # not the default port
    "https://cloud.example.invalid:80/more/notices/1001",
    "https://cloud.example.invalid:0/more/notices/1001",
    "https://cloud.example.invalid:99999/more/notices/1001",  # out of range
    "https://cloud.example.invalid:abc/more/notices/1001",  # not a number
    "https://localhost/more/notices/1001",
    "https://127.0.0.1/more/notices/1001",
    "https://10.0.0.8/more/notices/1001",
    "https://[::1]/more/notices/1001",
    "https://2130706433/more/notices/1001",  # 127.0.0.1 in legacy form
    "https://cloud.example.invalid/more/notices /1001",  # whitespace
    "https://cloud.example.invalid/more/notices/1001\n",
    "https:///more/notices/1001",  # no host
]


@pytest.mark.parametrize("url", BAD_URLS)
def test_bad_urls_and_ports_are_refused_before_any_request_or_connection(
    tmp_path, cli_doubles, capsys, url
):
    fetcher, reached = cli_doubles
    data = {**raw_manifest(), **window_around_now()}
    data["items"][0].update(input_url=url, target_url=url)
    assert cli.main(["trial", write(tmp_path, data)]) == 2
    assert fetcher.calls == [] and reached == []
    assert "invalid_manifest" in capsys.readouterr().err


@pytest.mark.parametrize(
    "field", ["input_url", "target_url", "site_url"], ids=["feed", "entry", "site"]
)
def test_a_bad_port_on_any_atom_url_is_refused(field):
    data = raw_manifest()
    item = data["items"][1]
    if field == "site_url":
        item["source"] = {**item["source"], "site_url": "https://devlog.example.invalid:8080/"}
    else:
        item[field] = item[field].replace(".invalid/", ".invalid:8080/")
    with pytest.raises(ValueError):
        trial.Manifest.model_validate(data)


def test_the_default_port_written_out_is_accepted():
    data = raw_manifest()
    url = "https://cloud.example.invalid:443/more/notices/1001"
    data["items"][0].update(input_url=url, target_url=url)
    trial.Manifest.model_validate(data)


@pytest.mark.parametrize(
    "robots",
    [
        FetchError("HTTP 404 from robots", status=404),  # collector: no rules, allowed
        FetchError("HTTP 410 from robots", status=410),
        b"<!DOCTYPE html><html><body>Not found</body></html>",  # an HTML page instead
        b"<html><head></head></html>",
    ],
    ids=["404", "410", "html-doctype", "html"],
)
def test_the_trial_refuses_a_robots_txt_without_rules(robots):
    fetcher = FakeFetcher(routes(**{CLOUD_ROBOTS: robots}))
    with pytest.raises(trial.TrialRefused) as refused:
        fetch(manifest(), fetcher)
    assert refused.value.code == "robots_refused"
    assert [url for url, _ in fetcher.calls] == [CLOUD_ROBOTS]


@pytest.mark.parametrize(
    "robots",
    [FetchError("HTTP 404", status=404), b"<!DOCTYPE html><html></html>"],
    ids=["404", "html"],
)
def test_the_collectors_robots_policy_is_unchanged(robots):
    from app.integrations.robots import RobotsPolicy

    verdict = RobotsPolicy(FakeFetcher({CLOUD_ROBOTS: robots})).check(NOTICE_URL)
    assert verdict.allowed and "unavailable" in verdict.reason


def test_an_empty_robots_txt_still_allows():
    fetcher = FakeFetcher(routes(**{CLOUD_ROBOTS: b"", DEVLOG_ROBOTS: b"# no rules\n"}))
    prepared, used = fetch(manifest(), fetcher)
    assert len(prepared) == 2 and used == 4


def test_a_feed_answered_with_an_html_page_fails():
    page = b"<!DOCTYPE html><html><body><a href='/posts/kafka-delivery/'>x</a></body></html>"
    fetcher = FakeFetcher(routes(**{FEED_URL: page}))
    with pytest.raises(FetchError, match="HTML page"):
        fetch(manifest(), fetcher)


class SteppingClock:
    """Answers the given times one per call, then the last one forever."""

    def __init__(self, *times: datetime):
        self.times, self.calls = list(times), 0

    def __call__(self) -> datetime:
        self.calls += 1
        return self.times.pop(0) if len(self.times) > 1 else self.times[0]


EXPIRED = datetime(2026, 10, 23, tzinfo=UTC)


@pytest.mark.parametrize(
    ("inside_calls", "requested"),
    [
        (1, []),  # expires right after the start check: no request at all
        (2, [CLOUD_ROBOTS]),  # before the notice page
        (3, [CLOUD_ROBOTS, NOTICE_URL]),  # before the second robots.txt
        (4, [CLOUD_ROBOTS, NOTICE_URL, DEVLOG_ROBOTS]),  # before the feed
    ],
)
def test_expiry_during_the_run_stops_the_next_request(inside_calls, requested):
    fetcher = FakeFetcher(routes())
    clock = SteppingClock(*([INSIDE] * inside_calls), EXPIRED)
    with pytest.raises(trial.TrialRefused) as refused:
        trial.run(manifest(), fetcher, clock=clock, dry_run=True)
    assert refused.value.code == "trial_expired"
    assert [url for url, _ in fetcher.calls] == requested


def test_expiry_after_the_last_request_writes_nothing():
    """All four requests made inside the window; the trial expires before the save."""
    fetcher = FakeFetcher(routes())
    clock = SteppingClock(*([INSIDE] * 5), EXPIRED)  # start + 4 requests, then expired
    db = FakeSession(FakeConnection(GOOD_URL))
    opened = []

    class Engine:
        def connect(self):
            return contextlib.nullcontext(FakeConnection(GOOD_URL))

    @contextlib.contextmanager
    def sessions():
        opened.append("session")
        yield _Transactional(db)

    with pytest.raises(trial.TrialRefused) as refused:
        trial.run(manifest(), fetcher, engine=Engine(), sessions=sessions, clock=clock)
    assert refused.value.code == "trial_expired"
    assert len(fetcher.calls) == 4
    assert opened == ["session"]
    # only the connection check happened, inside no_autoflush; no query, add or flush
    assert db.calls == ["connection(autoflush_off=True)"]


class _Transactional:
    """FakeSession plus a no-op begin(), as `with sessions() as db, db.begin()` needs."""

    def __init__(self, db: FakeSession):
        self._db = db

    def begin(self):
        return contextlib.nullcontext()

    def __getattr__(self, name):
        return getattr(self._db, name)


def test_save_checks_the_window_before_the_first_write():
    prepared, _ = fetch(manifest(), FakeFetcher(routes()))
    db = FakeSession(FakeConnection(GOOD_URL))
    with pytest.raises(trial.TrialRefused) as refused:
        trial.save(db, manifest(), prepared, tagger_for=lambda db: None, clock=lambda: EXPIRED)
    assert refused.value.code == "trial_expired"
    assert db.calls == ["connection(autoflush_off=True)"]


def test_the_local_dev_test_server_may_host_the_experiment_database():
    trial.check_connection(FakeConnection(GOOD_URL.replace(":3308", ":3307")))
    trial.check_connection(FakeConnection(GOOD_URL.replace(":3308", "")))


# --- robots.txt in a trial: markup refused; a BOM before real rules is read -------------
# Two separate checks. (1) Markup refusal, trial only: a body that starts with HTML or other
# markup (after any BOM or whitespace) is not robots.txt, so the trial refuses before the
# target; the general collector reads it as "no rules" and allows. (2) BOM support: a UTF-8
# BOM before real rules must not hide them. The general parser handles this since PR #20
# (test_feed_safety.py); the trial also strips the BOM itself before its markup check.

BOM = b"\xef\xbb\xbf"
BOM_HTML = BOM + b"<!DOCTYPE html><html><body>Please enable JavaScript</body></html>"
BODY_PAGE = b"<body><h1>Access denied</h1><p>Request blocked.</p></body>"


@pytest.mark.parametrize("robots", [BOM_HTML, BODY_PAGE], ids=["bom-html", "body-page"])
def test_a_markup_robots_txt_is_refused_before_the_target(robots):
    fetcher = FakeFetcher(routes(**{CLOUD_ROBOTS: robots}))
    with pytest.raises(trial.TrialRefused) as refused:
        fetch(manifest(), fetcher)
    assert refused.value.code == "robots_refused"
    assert [url for url, _ in fetcher.calls] == [CLOUD_ROBOTS]  # no target request


@pytest.mark.parametrize(
    "robots",
    [BOM + b"  \n" + BODY_PAGE, b"\n\n  " + BOM_HTML[3:], b"<?xml version='1.0'?><x/>"],
    ids=["bom-space-body", "space-html", "xml"],
)
def test_markup_after_whitespace_is_refused_too(robots):
    fetcher = FakeFetcher(routes(**{CLOUD_ROBOTS: robots}))
    with pytest.raises(trial.TrialRefused):
        fetch(manifest(), fetcher)
    assert NOTICE_URL not in [url for url, _ in fetcher.calls]


@pytest.mark.parametrize(
    "robots",
    [b"", BOM, b"\n", BOM + b"# no rules\n"],
    ids=["empty", "bom", "newline", "bom-comment"],
)
def test_an_empty_robots_file_still_allows(robots):
    fetcher = FakeFetcher(routes(**{CLOUD_ROBOTS: robots}))
    prepared, used = fetch(manifest(), fetcher)
    assert len(prepared) == 2 and used == 4


def test_a_bom_does_not_hide_the_first_rule_in_a_trial():
    """BOM support, not markup refusal: real rules after a UTF-8 BOM are read and the
    Disallow is honoured, so the target is not requested. (Before PR #20 the general
    parser read the BOM-prefixed first line as an unknown key; the trial stripped the BOM
    itself, and still does before its markup check.)"""
    robots = BOM + b"User-agent: *\nDisallow: /more/\n"
    fetcher = FakeFetcher(routes(**{CLOUD_ROBOTS: robots}))
    with pytest.raises(trial.TrialRefused) as refused:
        fetch(manifest(), fetcher)
    assert refused.value.code == "robots_refused"
    assert [url for url, _ in fetcher.calls] == [CLOUD_ROBOTS]


@pytest.mark.parametrize(
    ("robots", "allowed"),
    [
        (BOM_HTML, True),  # markup is no rules: the collector allows (the trial refuses)
        (BODY_PAGE, True),
        (b"", True),
        (b"User-agent: *\nDisallow: /more/\n", False),
    ],
    ids=["bom-html", "body-page", "empty", "disallow"],
)
def test_the_collectors_robots_policy_is_unchanged_for_these_inputs(robots, allowed):
    """The markup refusal above is trial-only; the general collector's policy for these
    inputs stays as it was. Its BOM handling is tested in test_feed_safety.py."""
    from app.integrations.robots import RobotsPolicy

    assert RobotsPolicy(FakeFetcher({CLOUD_ROBOTS: robots})).check(NOTICE_URL).allowed is allowed
