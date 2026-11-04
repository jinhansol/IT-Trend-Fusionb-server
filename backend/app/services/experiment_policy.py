"""Short local experiments: which sources may run, where, until when, and doing what.

An experiment source is marked in its own sources file (content/sources.experiment.*.yaml,
not a subdirectory: those are learning tracks) by options.scope and an
"exp-" slug (both or neither). The YAML only names the scope; everything that grants
something lives in POLICIES below, in code: the one database it may use, the time
window, and per source its exact identity (adapter, kind, language, site and feed URL),
the actions allowed and the fields that may be stored. A source matches only when all
of these agree; anything missing, unknown, expired or different is refused.

POLICIES is empty: no experiment may run until one is added here for a reviewed source
(stage B1). The checks guard against picking the wrong file, copying or renaming it,
dropping the scope or reusing stored options; they do not stop someone who edits this
module. terms: approved is still required for storing (app/services/source_terms.py):
a scope never approves anything by itself, and nothing here is a licence.
"""

import dataclasses
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import Connection

from app.db.safety import selected_database

EXPERIMENT_DATABASE = "devhub_experiment"
POLICY_PREFIX = "experiment policy"  # start of every PolicyError message
EXPERIMENT_PREFIX = "exp-"
ACTIONS = frozenset(
    {
        "metadata_read",  # robots.txt and the feed request, parsing
        "metadata_store",  # saving title, link, date and the allowed fields
        "excerpt_tagging",  # the feed description as tagging input (not stored)
        "excerpt_store",  # storing and showing the feed description
        "ai_input",  # sending article text to an external AI (refused in A1)
        "summary_store",  # storing an AI summary (refused in A1)
        "public_export",  # publishing results beyond the local machine (refused)
    }
)
REQUIRED_FIELDS = frozenset({"title", "url"})
OPTIONAL_FIELDS = frozenset(
    {"published_at", "author", "external_id", "source_tags", "score", "comment_count", "view_count"}
)


class PolicyError(RuntimeError):
    """An experiment step was refused. The message is a short reason code and a slug,
    never a URL with credentials, a key or article text."""

    def __init__(self, code: str, slug: str | None = None) -> None:
        super().__init__(f"{POLICY_PREFIX}: {code}" + (f" ({slug})" if slug else ""))
        self.code = code


@dataclass(frozen=True)
class SourceGrant:
    slug: str
    adapter: str
    kind: str
    language: str
    site_url: str
    feed_url: str | None
    actions: frozenset[str]
    stored_fields: frozenset[str] = frozenset({"title", "url", "published_at"})


@dataclass(frozen=True)
class ExperimentPolicy:
    scope: str
    database: str
    starts_at: datetime  # UTC, inclusive
    expires_at: datetime  # UTC, exclusive
    basis_ref: str  # where the reviewed basis for this use is written down
    sources: dict[str, SourceGrant]


# The trusted registry. Empty until a reviewed experiment is approved (stage B1).
POLICIES: dict[str, ExperimentPolicy] = {}


def now() -> datetime:
    return datetime.now(UTC)


def scope_of(source) -> str | None:
    return (getattr(source, "options", None) or {}).get("scope")


def is_experiment(source) -> bool:
    """Marked as an experiment source by either of its two markers."""
    return bool(scope_of(source)) or str(source.slug).startswith(EXPERIMENT_PREFIX)


def _same_url(a: str | None, b: str | None) -> bool:
    """Exact URL match; only the scheme and host are case-insensitive."""
    if a is None or b is None:
        return a is b
    pa, pb = urlsplit(a), urlsplit(b)
    if pa.username or pa.password or pb.username or pb.password:
        return False

    def canonical(p):
        return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path, p.query, p.fragment))

    return canonical(pa) == canonical(pb)


def _is_feed_url(url: str | None) -> bool:
    if not url:
        return False
    parts = urlsplit(url)
    return (
        parts.scheme in ("http", "https")
        and bool(parts.hostname)
        and not (parts.username or parts.password)
    )


def _valid(policy: ExperimentPolicy) -> bool:
    return (
        policy.database == EXPERIMENT_DATABASE
        and bool(policy.basis_ref.strip())
        and policy.starts_at.tzinfo is not None
        and policy.expires_at.tzinfo is not None
        and policy.starts_at < policy.expires_at
        and all(
            g.actions <= ACTIONS
            and REQUIRED_FIELDS <= g.stored_fields <= REQUIRED_FIELDS | OPTIONAL_FIELDS
            and g.slug.startswith(EXPERIMENT_PREFIX)
            # Experiments read RSS feeds only: an API adapter would bypass robots.txt.
            and g.adapter == "rss"
            and _is_feed_url(g.feed_url)
            for g in policy.sources.values()
        )
    )


def grant_for(source, at: datetime | None = None, policies=None) -> SourceGrant:
    """The grant that covers this experiment source now, or PolicyError."""
    slug = str(source.slug)
    scope = scope_of(source)
    if not scope:
        raise PolicyError("scope_missing", slug)
    if not slug.startswith(EXPERIMENT_PREFIX):
        raise PolicyError("scope_on_non_experiment_slug", slug)
    policy = (POLICIES if policies is None else policies).get(scope)
    if policy is None or policy.scope != scope:
        raise PolicyError("unknown_scope", slug)
    if not _valid(policy):
        raise PolicyError("invalid_policy", slug)
    moment = at or now()
    if not policy.starts_at <= moment < policy.expires_at:
        raise PolicyError("outside_policy_window", slug)
    grant = policy.sources.get(slug)
    if grant is None:
        raise PolicyError("source_not_in_policy", slug)
    for field in ("adapter", "kind", "language"):
        if getattr(source, field) != getattr(grant, field):
            raise PolicyError(f"{field}_mismatch", slug)
    if not _same_url(source.site_url, grant.site_url):
        raise PolicyError("site_url_mismatch", slug)
    if not _same_url(source.feed_url, grant.feed_url):
        raise PolicyError("feed_url_mismatch", slug)
    _check_flags(source, grant)
    return grant


def _check_flags(source, grant: SourceGrant) -> None:
    """Switches in the YAML may narrow what the policy allows, never widen it."""
    options = getattr(source, "options", None) or {}
    if options.get("excerpt") and "excerpt_store" not in grant.actions:
        raise PolicyError("excerpt_store_not_allowed", grant.slug)
    if options.get("tagging_excerpt") and "excerpt_tagging" not in grant.actions:
        raise PolicyError("excerpt_tagging_not_allowed", grant.slug)
    if getattr(source, "ai_summary", False):
        raise PolicyError("ai_not_allowed_in_experiments", grant.slug)


def require(source, *actions: str, at: datetime | None = None, policies=None) -> SourceGrant:
    grant = grant_for(source, at=at, policies=policies)
    for action in actions:
        if action not in ACTIONS:
            raise ValueError(f"unknown action {action!r}")
        if action in ("ai_input", "summary_store", "public_export"):
            raise PolicyError(f"{action}_refused", grant.slug)  # never in A1
        if action not in grant.actions:
            raise PolicyError(f"{action}_not_allowed", grant.slug)
    return grant


# --- the database actually in use -------------------------------------------------------


def database_names(connection: Connection) -> tuple[str | None, str | None]:
    """(configured, actually selected) database of this connection."""
    configured = connection.engine.url.database
    try:
        actual = selected_database(connection)
    except Exception:
        raise PolicyError("database_unverified") from None
    return configured, actual


def require_experiment_connection(connection: Connection) -> None:
    """Both the configured and the selected database must be exactly devhub_experiment."""
    configured, actual = database_names(connection)
    if configured != EXPERIMENT_DATABASE or actual != EXPERIMENT_DATABASE:
        raise PolicyError("not_the_experiment_database")


def is_experiment_connection(connection: Connection) -> bool:
    """True when either name says devhub_experiment: general data must not go there."""
    configured, actual = database_names(connection)
    return EXPERIMENT_DATABASE in (configured, actual)


def check_connection(
    connection: Connection,
    experiment: bool,
    general_code: str = "general_source_in_experiment_database",
) -> None:
    """Experiment work only on exactly devhub_experiment; general work never there.
    Checks this very connection (SELECT DATABASE()), so call it on the connection that
    is about to be written to or read from."""
    if experiment:
        require_experiment_connection(connection)
    elif is_experiment_connection(connection):
        raise PolicyError(general_code)


def check_session(db, experiment: bool, **kwargs) -> None:
    """check_connection on a Session's own connection, before any autoflush or DML."""
    with db.no_autoflush:
        check_connection(db.connection(), experiment, **kwargs)


def check_engine(engine, experiment: bool, **kwargs) -> None:
    """A pre-check on a fresh pooled connection. Later sessions may get another
    connection, so writes still check their own (check_session)."""
    try:
        with engine.connect() as connection:
            check_connection(connection, experiment, **kwargs)
    except PolicyError:
        raise
    except Exception:
        raise PolicyError("database_unverified") from None


def require_experiment_engine(engine) -> None:
    check_engine(engine, experiment=True)


def engine_is_experiment(engine) -> bool:
    """Configured name only (no query); the real check is check_engine/check_session."""
    return engine.url.database == EXPERIMENT_DATABASE


# --- fields ------------------------------------------------------------------------------

_CLEARED = {
    "published_at": None,
    "author": None,
    "external_id": None,
    "source_tags": [],
    "score": None,
    "comment_count": None,
    "view_count": None,
}
_ITEM_FIELD = {"source_tags": "tags"}  # CollectedItem names


def project(items: Iterable, grant: SourceGrant) -> list:
    """Copies of the collected items with every field the grant does not allow cleared.
    The excerpt is left to the excerpt switches (stored / used for tagging or not)."""
    cleared = {
        _ITEM_FIELD.get(field, field): value
        for field, value in _CLEARED.items()
        if field not in grant.stored_fields
    }
    return [dataclasses.replace(item, **cleared) for item in items]
