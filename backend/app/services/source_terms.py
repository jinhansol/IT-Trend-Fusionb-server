"""What a source's checked terms allow (options.terms / options.excerpt in sources.yaml).

Three separate permissions, each explicit; none implies the next:
- options.terms: approved   collect and show title, source, date and link;
- options.excerpt: true     also store and show the feed's own description;
- ai_summary: true          also summarize the article body with an external AI and show
                            the summary (a separate review of the terms).
excerpt and ai_summary count only together with terms: approved (checked when the file
is loaded and again here, for rows that are older than these options).

Rows loaded before these options existed have neither key and read as "unverified":
the safe default is to store nothing new and to show title, source, date and link only.
"""

from sqlalchemy import ColumnElement, func

from app.models.content import ContentSource
from app.services.experiment_policy import EXPERIMENT_PREFIX, is_experiment


def terms_approved(source: ContentSource) -> bool:
    return (source.options or {}).get("terms") == "approved"


def shows_excerpt(source: ContentSource) -> bool:
    return terms_approved(source) and bool((source.options or {}).get("excerpt"))


def tags_with_excerpt(source: ContentSource) -> bool:
    """Whether the feed description may be used as tagging input (never stored for that).
    Unset means yes for general sources, as before, and no for experiment sources."""
    flag = (source.options or {}).get("tagging_excerpt")
    return flag is True if is_experiment(source) else flag is not False


def allows_ai_summary(source: ContentSource) -> bool:
    """Experiment sources never get AI summaries (A1), whatever their switches say."""
    return bool(source.ai_summary) and terms_approved(source) and not is_experiment(source)


def ai_summary_allowed() -> ColumnElement[bool]:
    """allows_ai_summary as a SQL condition on ContentSource."""
    return (
        ContentSource.ai_summary.is_(True)
        & (ContentSource.options["terms"].as_string() == "approved")
        & ~ContentSource.slug.startswith(EXPERIMENT_PREFIX)
        & (func.coalesce(ContentSource.options["scope"].as_string(), "") == "")
    )


def collect_refusal(source: ContentSource) -> str | None:
    """Why a source must not be collected into the database, or None when it may be."""
    if source.status != "active":
        return f"{source.status} (read-only check: python -m app.jobs diagnose)"
    if not terms_approved(source):
        return "terms not approved (options.terms in content/sources.yaml)"
    return None
