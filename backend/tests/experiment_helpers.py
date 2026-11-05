"""Synthetic experiment policies and fake database handles for the A1 tests.

The real registry (app.services.experiment_policy.POLICIES) is empty; tests that need
an allowed path patch it with policies built here. No experiment database exists in
the test environment: the "allowed" database path is exercised with fake connections.
"""

import copy
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.services import experiment_policy as ep

SCOPE = "trial-1"
NOW = datetime(2026, 11, 12, 9, 0, tzinfo=UTC)
WINDOW = (NOW - timedelta(days=2), NOW + timedelta(days=12))


def exp_source(slug="exp-blog", **changes) -> dict:
    """An experiment RSS blog source definition (YAML shape)."""
    values = {
        "slug": slug,
        "name": f"Experiment {slug}",
        "kind": "blog",
        "adapter": "rss",
        "language": "ko",
        "site_url": f"https://{slug}.example.invalid/",
        "feed_url": f"https://{slug}.example.invalid/feed.xml",
        "channel": "exp-blogs",
        "channel_name": "Experiment blogs",
        "options": {"scope": SCOPE, "terms": "approved"},
    }
    return values | changes


def exp_news(slug="exp-news", **changes) -> dict:
    values = exp_source(slug, kind="news", channel=None, channel_name=None)
    return values | changes


def policy_for(
    sources: list[dict],
    actions=("metadata_read", "metadata_store"),
    stored_fields=("title", "url", "published_at"),
    window=WINDOW,
    scope=SCOPE,
) -> dict:
    grants = {
        s["slug"]: ep.SourceGrant(
            slug=s["slug"],
            adapter=s["adapter"],
            kind=s["kind"],
            language=s["language"],
            site_url=s["site_url"],
            feed_url=s.get("feed_url"),
            actions=frozenset(actions),
            stored_fields=frozenset(stored_fields),
        )
        for s in sources
    }
    return {
        scope: ep.ExperimentPolicy(
            scope=scope,
            database=ep.EXPERIMENT_DATABASE,
            starts_at=window[0],
            expires_at=window[1],
            basis_ref="tests/synthetic-basis",
            sources=grants,
        )
    }


def install(monkeypatch, policies: dict, at: datetime = NOW) -> None:
    monkeypatch.setattr(ep, "POLICIES", policies)
    monkeypatch.setattr(ep, "now", lambda: at)


class FakeConnection:
    def __init__(self, configured="devhub_experiment", actual="devhub_experiment"):
        self.engine = SimpleNamespace(url=SimpleNamespace(database=configured))
        self.actual = actual
        self.queries = 0

    def execute(self, statement, *params):
        self.queries += 1
        return SimpleNamespace(scalar=lambda: self.actual)


class FakeSession:
    """Enough of a Session for apply_sources / store_items preflights: records writes."""

    def __init__(self, connection: FakeConnection, rows=()):
        self._connection = connection
        self.rows = list(rows)
        self.added: list = []
        self.flushes = 0
        self.autoflush_disabled = 0

    @property
    @contextmanager
    def no_autoflush(self):
        self.autoflush_disabled += 1
        yield self

    def connection(self):
        return self._connection

    def scalars(self, statement):
        return list(self.rows)

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        self.flushes += 1


def as_file(*sources: dict) -> dict:
    return {"sources": [copy.deepcopy(s) for s in sources]}


class FakeEngine:
    """An engine whose connections report the given database names; counts connects."""

    def __init__(self, configured="devhub_experiment", actual="devhub_experiment"):
        self.url = SimpleNamespace(database=configured)
        self.actual = actual
        self.connects = 0

    @contextmanager
    def connect(self):
        self.connects += 1
        yield FakeConnection(self.url.database, self.actual)


class NoDatabase:
    """An engine that must never be used (general diagnose)."""

    url = SimpleNamespace(database="devhub_dev")

    def connect(self):
        raise AssertionError("a general diagnose opened a database connection")


# --- scripted handles: each new connection or session may see a different database ---


class ScriptedConnection(FakeConnection):
    def __init__(self, configured, actual, log):
        super().__init__(configured, actual)
        self.log = log

    def scalar(self, statement, params=None):
        self.log.append(str(statement).split("(")[0])  # e.g. "SELECT GET_LOCK"
        return 1

    def commit(self):
        pass


class ScriptedEngine:
    """connect() hands out connections whose selected database follows `actuals` in
    order (the last one repeats). `log` records lock statements."""

    def __init__(self, configured, actuals):
        self.url = SimpleNamespace(database=configured)
        self.actuals = list(actuals)
        self.log: list[str] = []
        self.connects = 0

    @contextmanager
    def connect(self):
        actual = self.actuals[min(self.connects, len(self.actuals) - 1)]
        self.connects += 1
        yield ScriptedConnection(self.url.database, actual, self.log)

    def dispose(self):
        pass


class ScriptedSession(FakeSession):
    """A FakeSession that also answers get(), execute() and queued scalars()."""

    def __init__(self, connection, objects=None, results=()):
        super().__init__(connection)
        self.objects = objects or {}
        self.results = list(results)
        self.gets: list = []

    def get(self, model, key):
        self.gets.append(model.__name__)
        return self.objects.get(model.__name__)

    def scalars(self, statement):
        return self.results.pop(0) if self.results else []

    def execute(self, statement, *args, **kwargs):
        return SimpleNamespace(all=lambda: [], scalars=lambda: [])


class ScriptedSessions:
    """Stands in for a sessionmaker: session n uses connection n (the last repeats)."""

    def __init__(self, connections, objects=None, results=None):
        self.connections = list(connections)
        self.objects = objects or {}
        self.results = results or {}
        self.opened: list[ScriptedSession] = []

    def _next(self):
        n = len(self.opened)
        connection = self.connections[min(n, len(self.connections) - 1)]
        session = ScriptedSession(connection, self.objects, self.results.get(n, ()))
        self.opened.append(session)
        return session

    @contextmanager
    def begin(self):
        yield self._next()

    @contextmanager
    def __call__(self):
        yield self._next()
