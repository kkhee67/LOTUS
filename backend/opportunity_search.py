"""Literal and topic search over one validated catalog snapshot."""
from collections.abc import Iterable, Sequence
import json
from pathlib import Path
import re
import unicodedata

from shared.models import Opportunity, OpportunityType


def normalize_search_text(value: str) -> str:
    """Normalize comparison copies only; preserve original opportunity fields."""
    return unicodedata.normalize('NFKC', value).casefold()


TOPICS = [[normalize_search_text(term) for term in group] for group in json.loads(
    (Path(__file__).resolve().parents[1] / 'shared/search_topics.json').read_text(encoding='utf-8')
)]


def term_patterns(word: str):
    related = {term for topic in TOPICS if len(word) >= 2 and any(alias.startswith(word) for alias in topic)
               for term in topic if term != word}
    # Short English abbreviations should not match inside unrelated words.
    return [re.compile(r'(?<![a-z0-9])' + re.escape(term) + r'(?![a-z0-9])'
                       if term.isascii() else re.escape(term)) for term in related if term != '개발']


def filter_opportunities(
    opportunities: Iterable[Opportunity], *, q: str | None = None,
    types: Sequence[OpportunityType] | None = None,
) -> list[Opportunity]:
    """AND words across fields; OR types; sort before counting and pagination."""
    words = [(word, term_patterns(word)) for word in normalize_search_text(q or '').split()]
    allowed = set(types or ())
    matches = []
    for opportunity in opportunities:
        if allowed and opportunity.type not in allowed:
            continue
        if words:
            fields = [normalize_search_text(value) for value in (
                opportunity.title, opportunity.organization, opportunity.summary, opportunity.type,
                opportunity.subtype or '', *opportunity.tags, *opportunity.fields,
                *opportunity.activities, *opportunity.related_majors, *opportunity.requirements)]
            if not all(any(word in field or any(pattern.search(field) for pattern in patterns)
                           for field in fields) for word, patterns in words):
                continue
        matches.append(opportunity)
    return sorted(matches, key=lambda opportunity: opportunity.id)
