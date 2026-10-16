"""Duplicate detection: the proximity rule and the name rule (contribution-and-moderation
spec, Duplicate detection).

The rules are pure; the query port is what an adapter implements with PostGIS (distances)
and the archive's tables (names). Both thresholds are platform constants, never Instance
configuration, and change only with a release.
"""

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from rapidfuzz import fuzz

from tart.archive.geometry import Geometry
from tart.archive.records import Kind, RecordId

PROXIMITY_METRES = 25
"""A Location is a candidate within this distance, plus the uncertainty radius of each side."""

NAME_THRESHOLD = 90
"""The score, on a 0-100 scale, from which a name is a candidate."""

NAMED_KINDS = frozenset({Kind.ARTIST, Kind.SITE, Kind.SERIES, Kind.AREA, Kind.SOURCE})
"""The kinds the name rule applies to; Artwork titles are excluded."""


def proximity_limit(radius: int | None, other_radius: int | None) -> float:
    """The largest distance, in metres, at which two Locations are candidates."""
    return PROXIMITY_METRES + (radius or 0) + (other_radius or 0)


def within_proximity(distance: float, radius: int | None, other_radius: int | None) -> bool:
    """Whether two Locations at this minimum geometry-to-geometry distance are candidates."""
    return distance <= proximity_limit(radius, other_radius)


def normalise_name(name: str) -> str:
    """Lowercase, no accents, no punctuation, single spaces."""
    decomposed = unicodedata.normalize("NFKD", name.casefold())
    unaccented = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(re.sub(r"[\W_]+", " ", unaccented).split())


def normalise_url(url: str) -> str:
    """A URL as compared: no scheme, `www.`, fragment, or trailing slash; host in lowercase."""
    text = re.sub(r"^[a-z][a-z0-9+.-]*://", "", url.strip(), flags=re.IGNORECASE)
    text = text.partition("#")[0]
    host, slash, rest = text.partition("/")
    host = host.casefold().removeprefix("www.")
    return (host + slash + rest).rstrip("/")


def name_score(name: str, other: str) -> float:
    """How alike two names are, from 0 to 100, after normalisation."""
    a, b = normalise_name(name), normalise_name(other)
    if not a or not b:
        return 0.0
    return float(fuzz.ratio(a, b))


class Match(StrEnum):
    NAME = "name"
    ALIAS = "alias"
    URL = "url"


@dataclass(frozen=True)
class NamedRecord:
    """An existing record with the names it can be known by."""

    id: RecordId
    kind: Kind
    name: str
    aliases: tuple[str, ...] = ()
    url: str | None = None


@dataclass(frozen=True)
class NameCandidate:
    record: NamedRecord
    match: Match
    matched: str
    """The name, Alias, or URL that matched."""
    score: float


def name_candidates(
    name: str, records: Iterable[NamedRecord], *, url: str | None = None
) -> list[NameCandidate]:
    """The records whose name or Alias scores at least the threshold against `name`, or
    whose URL equals `url`; the best match of each record, the best score first."""
    wanted_url = normalise_url(url) if url and url.strip() else None
    found = []
    for record in records:
        best: NameCandidate | None = None
        if wanted_url is not None and record.url and normalise_url(record.url) == wanted_url:
            best = NameCandidate(record, Match.URL, record.url, 100.0)
        names = [(Match.NAME, record.name), *((Match.ALIAS, alias) for alias in record.aliases)]
        for match, candidate in names:
            score = name_score(name, candidate)
            if score >= NAME_THRESHOLD and (best is None or score > best.score):
                best = NameCandidate(record, match, candidate, score)
        if best is not None:
            found.append(best)
    return sorted(found, key=lambda c: (-c.score, c.record.id))


@dataclass(frozen=True)
class NearLocation:
    id: RecordId
    distance: float
    """Metres between the two geometries."""


class DuplicateQuery(Protocol):
    """What the rules need from persistence."""

    async def locations_near(self, geometry: Geometry, radius: int | None) -> list[NearLocation]:
        """The public Locations within the proximity rule of the geometry, nearest first."""
        ...

    async def named_records(self, kind: Kind) -> list[NamedRecord]:
        """The public records of the kind, with their Aliases and, for a Source, URL."""
        ...
