"""What the Discovery endpoints return (Discovery spec, Modules: Discovery query and
Location panel)."""

from typing import Any, Literal

from pydantic import BaseModel

from tart.archive import Kind
from tart.archive_read import views as v


class AlsoMatch(BaseModel):
    record: v.RecordLink
    alias: str | None
    """For an Artist matched through an Alias: "(also: <alias>)"."""


class AlsoMatchingKind(BaseModel):
    kind: Kind
    items: list[AlsoMatch]
    """At most three."""
    total: int
    """The matches of this kind: more than three ends with "Show all (N)"."""


class AlsoMatching(BaseModel):
    kinds: list[AlsoMatchingKind]
    """Artists, Series, Sites, Areas, in this order; kinds without a match are absent."""


class ArtworkPage(BaseModel):
    entries: list[v.ListEntry]
    total: int
    page: int
    page_size: int
    also_matching: AlsoMatching | None
    """Only with a search that matches some record."""
    left_out: int
    """With "Created between": the matching Artworks without a creation date, left out."""


class LocationPanel(BaseModel):
    location: v.LocationSummary
    site: v.RecordLink | None
    areas: list[v.RecordLink]
    entries: list[v.ListEntry]
    """The matching Artworks, in stratigraphy order; with none matching, all of them."""
    matches: bool
    """False: no Artwork here matches the filters ("No artworks here match the current
    filters"), or, with no entries, there is no public Artwork here."""
    other: int
    """The Artworks on this surface that do not match: "N more artworks don't match"."""


class MapProperties(BaseModel):
    id: int
    present: int
    unknown: int
    disappeared: int
    """The matching Artworks of the Location, by Condition group."""
    group: Literal["present", "unknown", "disappeared"]
    """The prevailing group: present, else unknown, else disappeared."""
    count: int
    point: list[float]
    """The representative point, where the sign sits: longitude, latitude."""
    approximate: bool
    radius: int | None


class MapFeature(BaseModel):
    type: Literal["Feature"]
    geometry: dict[str, Any]
    properties: MapProperties


class SiteLabel(BaseModel):
    id: int
    name: str
    path: str
    """The Site's `{id}-{slug}` segment."""
    point: list[float]
    """The centroid of its matching Locations' representative points."""


class AreaLabel(BaseModel):
    name: str
    point: list[float]


class MapLocations(BaseModel):
    type: Literal["FeatureCollection"]
    features: list[MapFeature]
    sites: list[SiteLabel]
    areas: list[AreaLabel]
