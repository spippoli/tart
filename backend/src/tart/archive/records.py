"""The Archive record kinds (archive-records spec, Artwork to Documentation item).

Each record is an immutable value. Links to other records are `Ref`s: the id of an
existing record, or `New` for a record created by the same changeset, which the
write operation replaces with the new id before anything is stored.

Fields not listed here do not exist: there is no field for whether an Artwork was
authorised, no image of an Artist, and no link between an Artist and a User
(ADR 0014).
"""

from dataclasses import dataclass, fields
from enum import StrEnum
from typing import Any, ClassVar

from tart.archive.geometry import Geometry
from tart.archive.uncertain_date import Period, UncertainDate

type RecordId = int


@dataclass(frozen=True)
class New:
    """A record created by the same changeset, named by a key unique within it."""

    key: str


type Ref = RecordId | New


class Kind(StrEnum):
    ARTWORK = "artwork"
    LOCATION = "location"
    SITE = "site"
    AREA = "area"
    SERIES = "series"
    ARTIST = "artist"
    SOURCE = "source"
    DOCUMENTATION_ITEM = "documentation_item"


class Certainty(StrEnum):
    CONFIRMED = "confirmed"
    PROBABLE = "probable"
    DISPUTED = "disputed"


class ArtistKind(StrEnum):
    INDIVIDUAL = "individual"
    COLLECTIVE = "collective"


class Medium(StrEnum):
    IMAGE = "image"
    PDF = "pdf"
    TEXT = "text"
    LINK = "link"


class RightsBasis(StrEnum):
    OWN_WORK = "own_work"
    """Own work of the file's creator."""
    THIRD_PARTY = "third_party"
    """A third party's work, already published under an allowlisted licence."""


@dataclass(frozen=True)
class Attribution:
    """A Claim linking the Artwork to an Artist; one per Artist on an Artwork."""

    artist: Ref
    certainty: Certainty
    alias: str | None = None
    """The Artist's Alias the Artwork was signed with."""
    note: str | None = None
    citations: tuple[Ref, ...] = ()
    """Sources and Documentation items."""

    @property
    def key(self) -> Ref:
        return self.artist


@dataclass(frozen=True)
class CrewMembership:
    """The Artist holding it is a member of `collective`; one per collective."""

    collective: Ref
    period: Period | None = None

    @property
    def key(self) -> Ref:
        return self.collective


class Record:
    """What every record kind shares: its kind, and which of its fields are collections.

    A collection is a tuple of items addressed by key: an item's `key` property, or
    the item itself for links and Aliases.
    """

    KIND: ClassVar[Kind]
    COLLECTIONS: ClassVar[tuple[str, ...]] = ()

    @classmethod
    def field_names(cls) -> tuple[str, ...]:
        return tuple(field.name for field in fields(cls))  # type: ignore[arg-type]


def item_key(item: Any) -> Any:
    return getattr(item, "key", item)


@dataclass(frozen=True)
class Artwork(Record):
    KIND = Kind.ARTWORK
    COLLECTIONS = ("attributions", "series", "sources")

    location: Ref
    """Changes only to correct wrong data, never for a physical move."""
    expression_types: tuple[str, ...]
    title: str | None = None
    description: str | None = None
    attributions: tuple[Attribution, ...] = ()
    series: tuple[Ref, ...] = ()
    sources: tuple[Ref, ...] = ()
    """Record-level citations: background, never an Evidence level."""


@dataclass(frozen=True)
class Location(Record):
    KIND = Kind.LOCATION

    geometry: Geometry
    """The only position the archive holds for the surface: there is no hidden one."""
    surface_type: str
    approximate: bool = False
    uncertainty_radius: int | None = None
    """In metres; only for an approximate point."""
    site: Ref | None = None
    place_description: str | None = None


@dataclass(frozen=True)
class Site(Record):
    KIND = Kind.SITE
    COLLECTIONS = ("sources",)

    name: str
    description: str | None = None
    sources: tuple[Ref, ...] = ()


@dataclass(frozen=True)
class Area(Record):
    KIND = Kind.AREA
    COLLECTIONS = ("sources",)

    name: str
    geometry: Geometry
    description: str | None = None
    sources: tuple[Ref, ...] = ()


@dataclass(frozen=True)
class Series(Record):
    KIND = Kind.SERIES
    COLLECTIONS = ("sources",)

    name: str
    description: str | None = None
    sources: tuple[Ref, ...] = ()


@dataclass(frozen=True)
class Artist(Record):
    KIND = Kind.ARTIST
    COLLECTIONS = ("aliases", "areas", "crew_memberships", "sources")

    name: str
    kind: ArtistKind
    biography: str | None = None
    period: Period | None = None
    """The period of activity."""
    aliases: tuple[str, ...] = ()
    areas: tuple[Ref, ...] = ()
    """Areas of activity."""
    crew_memberships: tuple[CrewMembership, ...] = ()
    sources: tuple[Ref, ...] = ()


@dataclass(frozen=True)
class Source(Record):
    KIND = Kind.SOURCE

    title: str
    author: str | None = None
    publication: str | None = None
    date: UncertainDate | None = None
    url: str | None = None
    note: str | None = None
    language: str | None = None


@dataclass(frozen=True)
class DocumentationItem(Record):
    KIND = Kind.DOCUMENTATION_ITEM
    COLLECTIONS = ("artworks",)
    IMMUTABLE: ClassVar[tuple[str, ...]] = (
        "medium",
        "file",
        "licence",
        "creator_credit",
        "rights_basis",
        "origin_url",
    )
    """Fields that never change once the item exists."""

    medium: Medium
    observed_date: UncertainDate
    artworks: tuple[Ref, ...]
    location: Ref | None = None
    """Set only for documentation of a disappearance."""
    file: str | None = None
    """The storage key of the immutable file of an `image` or `pdf` item."""
    licence: str | None = None
    creator_credit: str | None = None
    rights_basis: RightsBasis | None = None
    origin_url: str | None = None
    alt_text: str | None = None
    text: str | None = None
    url: str | None = None
    language: str | None = None


RECORD_TYPES: dict[Kind, type[Record]] = {
    record_type.KIND: record_type
    for record_type in (
        Artwork,
        Location,
        Site,
        Area,
        Series,
        Artist,
        Source,
        DocumentationItem,
    )
}


@dataclass(frozen=True)
class LocationTitle:
    """What a Location's title is made of; the UI composes the words.

    The Place description when there is one; else the Surface type with the Site's
    name, or with the first Area by name; else neither, and the UI shows
    "Location {id}".
    """

    place_description: str | None = None
    surface_type: str | None = None
    """A Surface type key, shown with its label for the UI language."""
    place: str | None = None
    """The Site's name, else the first Area's name."""


def location_title(
    location: Location, site_name: str | None, area_names: list[str]
) -> LocationTitle:
    """The title of a Location, given its Site's name and the names of its Areas, by name."""
    if location.place_description is not None:
        return LocationTitle(place_description=location.place_description)
    place = site_name if site_name is not None else (area_names[0] if area_names else None)
    if place is None:
        return LocationTitle()
    return LocationTitle(surface_type=location.surface_type, place=place)
