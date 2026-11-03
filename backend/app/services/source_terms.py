"""What a source's checked terms allow (options.terms / options.excerpt in sources.yaml).

Rows loaded before these options existed have neither key and read as "unverified":
the safe default is to store nothing new and to show title, source, date and link only.
"""

from app.models.content import ContentSource


def terms_approved(source: ContentSource) -> bool:
    return (source.options or {}).get("terms") == "approved"


def shows_excerpt(source: ContentSource) -> bool:
    return terms_approved(source) and bool((source.options or {}).get("excerpt"))


def collect_refusal(source: ContentSource) -> str | None:
    """Why a source must not be collected into the database, or None when it may be."""
    if source.status != "active":
        return f"{source.status} (read-only check: python -m app.jobs diagnose)"
    if not terms_approved(source):
        return "terms not approved (options.terms in content/sources.yaml)"
    return None
