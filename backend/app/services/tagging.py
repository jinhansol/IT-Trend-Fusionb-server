"""Rule-based technology tagging.

Aliases match whole words only: "java" does not match "javascript", and "ai" does not
match "OpenAI". Hangul is treated as a word separator, so "파이썬은" still matches
"파이썬"; the one exception is a Hangul alias that starts another technology's longer
alias ("자바" in "자바스크립트"), which does not match there.

tag_only aliases are compared with the source's own tags. In free text they count only
through CONTEXT_RULES: an explicit pattern for an ambiguous word ("react" the library vs
the English verb) that requires a technical context around it.
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


_HANGUL = re.compile(r"[\uac00-\ud7a3]")

# Ambiguous tag-only words and the free-text contexts in which they mean the technology,
# keyed by the alias text (the technology is whichever one owns that tag alias).
CONTEXT_RULES: dict[str, re.Pattern[str]] = {
    # "react" is mostly the English verb ("how people react to ..."). It counts as React
    # when followed by a major version ("React 19.2", "react-18", "React v19"), by a
    # development word ("React hooks", "React 컴포넌트"), or directly by a Korean particle
    # ("React로", "React와"), which the verb never is. "React Native" is not included.
    "react": re.compile(
        r"(?<![a-z0-9])react(?:"
        r"[ \-]?v?[12][0-9](?:\.[0-9]+)*(?![0-9a-z])"
        r"|\s+(?:hooks?|components?|router|query|dom|compiler|apps?|컴포넌트|훅|앱)(?![a-z0-9])"
        r"|(?=[\uac00-\ud7a3])"
        r")"
    ),
}


def _word_pattern(word: str, not_followed_by: tuple[str, ...] = ()) -> str:
    """Whole-word match. Edges that are symbols ("c++", "c#") need no boundary, so
    "C++26" still matches "c++". not_followed_by lists the rest of other technologies'
    longer Hangul aliases that start with this word ("스크립트" for "자바")."""
    pattern = re.escape(word)
    if word[0].isalnum():
        pattern = rf"(?<![a-z0-9]){pattern}"
    if word[-1].isalnum():
        pattern = rf"{pattern}(?![a-z0-9])"
    for rest in not_followed_by:
        pattern = rf"{pattern}(?!{re.escape(rest)})"
    return pattern


def _hangul_extensions(word: str, owner: int, free: list[tuple[int, str]]) -> tuple[str, ...]:
    """The rest of every other technology's free alias that is `word` plus Hangul."""
    return tuple(
        sorted(
            other[len(word) :]
            for tech_id, other in free
            if tech_id != owner
            and len(other) > len(word)
            and other.startswith(word)
            and _HANGUL.match(other[len(word)])
        )
    )


@dataclass(frozen=True)
class Tagger:
    text_patterns: tuple[tuple[int, re.Pattern[str]], ...]
    tag_map: dict[str, frozenset[int]]
    context_patterns: tuple[tuple[frozenset[int], re.Pattern[str]], ...] = ()

    @classmethod
    def from_aliases(cls, aliases: list[tuple[int, str, bool]]) -> "Tagger":
        """aliases: (technology_id, alias, tag_only)."""
        words: dict[int, list[str]] = {}
        tag_map: dict[str, set[int]] = {}
        tag_only_ids: dict[str, set[int]] = {}
        for tech_id, alias, tag_only in aliases:
            alias = alias.lower()
            tag_map.setdefault(alias, set()).add(tech_id)
            if tag_only:
                tag_only_ids.setdefault(alias, set()).add(tech_id)
            else:
                words.setdefault(tech_id, []).append(alias)
        free = [(tech_id, w) for tech_id, ws in words.items() for w in ws]
        patterns = []
        for tech_id, tech_words in sorted(words.items()):
            alternatives = "|".join(
                _word_pattern(w, _hangul_extensions(w, tech_id, free))
                for w in sorted(tech_words, key=len, reverse=True)
            )
            patterns.append((tech_id, re.compile(f"(?:{alternatives})")))
        contexts = tuple(
            (frozenset(tag_only_ids[alias]), rule)
            for alias, rule in CONTEXT_RULES.items()
            if alias in tag_only_ids
        )
        return cls(tuple(patterns), {k: frozenset(v) for k, v in tag_map.items()}, contexts)

    def match(self, title: str, excerpt: str | None, tags: list[str]) -> set[int]:
        text = f"{title}\n{excerpt or ''}".lower()
        found = {tech_id for tech_id, pattern in self.text_patterns if pattern.search(text)}
        for ids, rule in self.context_patterns:
            if rule.search(text):
                found |= ids
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
