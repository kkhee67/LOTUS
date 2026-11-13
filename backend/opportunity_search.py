"""Literal, read-only filtering over one validated catalog snapshot."""
from collections.abc import Iterable, Sequence
import unicodedata

from shared.models import Opportunity, OpportunityType


def normalize_search_text(value: str) -> str:
    """Normalize comparison copies only; preserve original opportunity fields."""
    return unicodedata.normalize('NFKC', value).casefold()


def filter_opportunities(
    opportunities: Iterable[Opportunity], *, q: str | None = None,
    types: Sequence[OpportunityType] | None = None,
) -> list[Opportunity]:
    """AND words across fields; OR types; sort before counting and pagination."""
    words = normalize_search_text(q or '').split()
    allowed = set(types or ())
    matches = []
    for opportunity in opportunities:
        if allowed and opportunity.type not in allowed:
            continue
        if words:
            fields = [normalize_search_text(value) for value in (
                opportunity.title, opportunity.organization, opportunity.summary, *opportunity.tags)]
            if not all(any(word in field for field in fields) for word in words):
                continue
        matches.append(opportunity)
    return sorted(matches, key=lambda opportunity: opportunity.id)
