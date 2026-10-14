"""The Discovery query's inputs: search text, filters, and order (Discovery spec, Search,
Filters, and Ordering). The frontend's filter state parses the query string; this is what
reaches the backend."""

import json
import re
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from tart.archive import Condition

MIN_QUERY_LENGTH = 2
MAX_QUERY_LENGTH = 100
PAGE_SIZE = 24


class Order(StrEnum):
    RECENT = "recent"
    """Most recently documented."""
    OLDEST = "oldest"
    """First documented, oldest first."""
    ADDED = "added"
    """Recently added to the archive."""
    TITLE = "title"
    RELEVANCE = "relevance"


class AttributionFilter(StrEnum):
    UNKNOWN = "unknown"
    ATTRIBUTED = "attributed"
    """`confirmed` or `probable`."""
    DISPUTED = "disputed"


def normalise_query(text: str | None) -> str | None:
    """Trimmed, inner whitespace collapsed, truncated beyond 100 characters; `None` under 2.

    Accents are folded by the database (`unaccent`), where the names are folded too.
    """
    if text is None:
        return None
    collapsed = re.sub(r"\s+", " ", text).strip()[:MAX_QUERY_LENGTH].strip()
    return collapsed if len(collapsed) >= MIN_QUERY_LENGTH else None


@dataclass(frozen=True)
class Filters:
    """OR within a filter, AND across filters; an empty one does not filter."""

    q: str | None = None
    order: Order | None = None
    conditions: frozenset[Condition] = frozenset()
    """No Condition, or all nine, is no filter."""
    expression_types: frozenset[str] = frozenset()
    areas: frozenset[int] = frozenset()
    attribution: frozenset[AttributionFilter] = frozenset()
    artist: int | None = None
    series: int | None = None
    documented_from: int | None = None
    documented_to: int | None = None
    created_from: int | None = None
    created_to: int | None = None

    @property
    def query(self) -> str | None:
        return normalise_query(self.q)

    @property
    def effective_order(self) -> Order:
        """Relevance with a query by default, and only with one; else most recently documented."""
        if self.query is None:
            return Order.RECENT if self.order in (None, Order.RELEVANCE) else self.order
        return self.order or Order.RELEVANCE

    @property
    def restricts_conditions(self) -> bool:
        return 0 < len(self.conditions) < len(Condition)

    @property
    def creation_dated(self) -> bool:
        return self.created_from is not None or self.created_to is not None

    @property
    def documentation_dated(self) -> bool:
        return self.documented_from is not None or self.documented_to is not None

    def canonical(self) -> str:
        """The normalised query as text, for the ETag: equal queries give equal text."""
        return json.dumps(
            {
                "q": self.query,
                "order": self.effective_order.value,
                "conditions": sorted(c.value for c in self.conditions)
                if self.restricts_conditions
                else [],
                "types": sorted(self.expression_types),
                "areas": sorted(self.areas),
                "attribution": sorted(a.value for a in self.attribution),
                "artist": self.artist,
                "series": self.series,
                "documented": [self.documented_from, self.documented_to],
                "created": [self.created_from, self.created_to],
            },
            sort_keys=True,
        )


def first_day(year: int | None) -> date | None:
    return date(year, 1, 1) if year is not None else None


def last_day(year: int | None) -> date | None:
    return date(year, 12, 31) if year is not None else None
