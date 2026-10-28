"""Rule-based technology tagging.

Aliases match whole words only: "java" does not match "javascript", and "ai" does not
match "OpenAI". Hangul is treated as a word separator, so "파이썬은" still matches
"파이썬". tag_only aliases are compared with the source's own tags, never free text.
"""

import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import Technology, TechnologyAlias

# A version suffix on a source tag ("python-3.x", "angular-17") is ignored.
_TAG_VERSION = re.compile(r"-[0-9][0-9.x]*$")


def _normalize_tag(tag: str) -> str:
    tag = tag.strip().lower().lstrip("#")
    return _TAG_VERSION.sub("", tag)


def _word_pattern(word: str) -> str:
    """Whole-word match. Edges that are symbols ("c++", "c#") need no boundary, so
    "C++26" still matches "c++"."""
    pattern = re.escape(word)
    if word[0].isalnum():
        pattern = rf"(?<![a-z0-9]){pattern}"
    if word[-1].isalnum():
        pattern = rf"{pattern}(?![a-z0-9])"
    return pattern


@dataclass(frozen=True)
class Tagger:
    text_patterns: tuple[tuple[int, re.Pattern[str]], ...]
    tag_map: dict[str, frozenset[int]]

    @classmethod
    def from_aliases(cls, aliases: list[tuple[int, str, bool]]) -> "Tagger":
        """aliases: (technology_id, alias, tag_only)."""
        words: dict[int, list[str]] = {}
        tag_map: dict[str, set[int]] = {}
        for tech_id, alias, tag_only in aliases:
            alias = alias.lower()
            tag_map.setdefault(alias, set()).add(tech_id)
            if not tag_only:
                words.setdefault(tech_id, []).append(alias)
        patterns = []
        for tech_id, tech_words in sorted(words.items()):
            alternatives = "|".join(
                _word_pattern(w) for w in sorted(tech_words, key=len, reverse=True)
            )
            patterns.append((tech_id, re.compile(f"(?:{alternatives})")))
        return cls(tuple(patterns), {k: frozenset(v) for k, v in tag_map.items()})

    def match(self, title: str, excerpt: str | None, tags: list[str]) -> set[int]:
        text = f"{title}\n{excerpt or ''}".lower()
        found = {tech_id for tech_id, pattern in self.text_patterns if pattern.search(text)}
        for tag in tags:
            found |= self.tag_map.get(_normalize_tag(tag), frozenset())
        return found


def load_tagger(db: Session) -> Tagger:
    rows = db.execute(
        select(TechnologyAlias.technology_id, TechnologyAlias.alias, TechnologyAlias.tag_only)
        .join(Technology, Technology.id == TechnologyAlias.technology_id)
        .where(Technology.status == "published")
    ).all()
    return Tagger.from_aliases([tuple(row) for row in rows])
