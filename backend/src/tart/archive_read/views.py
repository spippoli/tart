"""The public views of Archive records: what the record pages read (archive-records spec,
Public record pages and Visibility).

Values from vocabularies are keys, and the UI words them; free text is in the Content
language. A value hidden by a Redaction is `null` for the public and named in
`redacted_fields`; a Moderator gets it, with the Redaction in `redactions`.
"""

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

from tart.archive import (
    ArtistKind,
    Certainty,
    Condition,
    ConditionGroup,
    EvidenceLevel,
    HistoryEventType,
    Kind,
    Medium,
    Precision,
    Qualifier,
    RightsBasis,
)


class UncertainDate(BaseModel):
    """As the archive stores it: each value the first day of the unit it names."""

    precision: Precision
    qualifier: Qualifier | None = None
    first: str | None = None
    second: str | None = None


class Period(BaseModel):
    start: UncertainDate | None = None
    end: UncertainDate | None = None


class LocationTitle(BaseModel):
    """What the title is made of; with all three absent the UI shows "Location {id}"."""

    place_description: str | None = None
    surface_type: str | None = None
    place: str | None = None


class RecordLink(BaseModel):
    """A link to a public record page."""

    kind: Kind
    id: int
    path: str
    """The canonical `{id}-{slug}` segment, or the bare id."""
    name: str | None = None
    """A title or name; `null` for an untitled Artwork, a Location, or a Documentation item."""
    location_title: LocationTitle | None = None
    """For a Location."""


class Redaction(BaseModel):
    """For Moderators: a value or item hidden from the public by a Redaction."""

    field: str
    """The field, or the collection of the item."""
    item: Any = None
    """The key of the item: an Artist id, an event id, a linked record id, an Alias."""
    redacted_at: datetime


class Visibility(BaseModel):
    redacted_fields: list[str] = []
    """Fields whose current value the public cannot see; the UI shows a placeholder."""
    withdrawn_at: datetime | None = None
    """For Moderators only: the record is withdrawn and the public gets 410."""
    redactions: list[Redaction] = []
    """For Moderators only."""


class ConditionView(BaseModel):
    condition: Condition
    group: ConditionGroup
    since: UncertainDate | None
    """The Observed date of the event that sets it; `null` only for `unknown`."""
    evidence_level: EvidenceLevel | None
    event: int | None
    """The History event that sets it, on the Timeline."""


class ArtworkCard(BaseModel):
    """An Artwork in a list: its Condition and latest documentation date only."""

    id: int
    path: str
    title: str | None
    expression_types: list[str]
    condition: ConditionView
    last_documented: UncertainDate | None


class Citation(RecordLink):
    """A cited Source or Documentation item."""


class ShownAttribution(BaseModel):
    artist: RecordLink
    certainty: Certainty
    """As the public reads it: `confirmed` without a public citation reads `probable`."""
    alias: str | None
    note: str | None
    evidence_level: EvidenceLevel
    citations: list[Citation]


class AttributionReadout(BaseModel):
    """Both empty: "Unknown artist"."""

    attributed: list[ShownAttribution]
    disputed: list[ShownAttribution]


class Rendition(BaseModel):
    width: int
    height: int


class DocumentationSummary(BaseModel):
    """A Documentation item in a gallery or a list."""

    id: int
    path: str
    medium: Medium
    observed_date: UncertainDate
    file: str | None = None
    """The upload id of an image or PDF: `/api/media/{file}/{rendition}`."""
    renditions: dict[str, Rendition] | None = None
    alt_text: str | None = None
    creator_credit: str | None = None
    licence: str | None = None
    text: str | None = None
    url: str | None = None
    language: str | None = None


class LocationSummary(BaseModel):
    id: int
    path: str
    title: LocationTitle
    surface_type: str
    geometry: dict[str, Any] | None
    """GeoJSON; `null` when redacted."""
    approximate: bool
    uncertainty_radius: int | None


class NearbyLocation(BaseModel):
    """A public Location near the record's, drawn muted on the mini-map."""

    id: int
    point: tuple[float, float]
    """The representative point (longitude, latitude)."""


class Where(BaseModel):
    location: LocationSummary | None
    location_withdrawn: bool
    """The Location is withdrawn: the UI shows "Location removed for legal reasons" and
    no mini-map, Site, or Areas."""
    site: RecordLink | None
    areas: list[RecordLink]
    nearby: list[NearbyLocation] = []
    """The public Locations within 500 m of this one, for the mini-map."""


class ListEntry(ArtworkCard):
    """An Artwork in the Explore list, the Archive view, and a Location's panel
    (Discovery spec, List entries)."""

    location: int
    """The Location it is on: what "Show on map" selects."""
    site: RecordLink | None
    area: RecordLink | None
    """The first of its Areas by name; the "where" line shows the Site, else this."""
    approximate: bool
    attributed: list[RecordLink]
    disputed: list[RecordLink]
    """Both empty: "Unknown artist"."""
    thumbnail: DocumentationSummary | None
    """The most recent public image or PDF preview."""
    latest_item_medium: Medium | None
    """What the neutral box names without a thumbnail; `null`: no public Documentation item."""


class EventEntry(BaseModel):
    entry: Literal["event"] = "event"
    id: int
    type: HistoryEventType
    observed_date: UncertainDate
    condition: Condition | None
    """The Condition a `condition_recorded` event states."""
    submitted_at: datetime
    approved_at: datetime
    revision: int
    """The Revision that introduced it: the anchor on `/revisions`."""
    evidence_level: EvidenceLevel
    citations: list[Citation]
    note: str | None
    covering: RecordLink | None
    """The covering Artwork of a `covered` event, when public."""


class ItemEntry(BaseModel):
    entry: Literal["item"] = "item"
    id: int
    path: str
    medium: Medium
    observed_date: UncertainDate


TimelineEntry = Annotated[EventEntry | ItemEntry, Field(discriminator="entry")]


class TimelineView(BaseModel):
    dated: list[TimelineEntry]
    """Ascending."""
    undated: list[TimelineEntry]


class Related(BaseModel):
    same_location: list[ArtworkCard]
    same_artist: list[ArtworkCard]
    same_series: list[ArtworkCard]


class ArtworkView(Visibility):
    kind: Literal["artwork"] = "artwork"
    id: int
    path: str
    title: str | None
    expression_types: list[str]
    description: str | None
    condition: ConditionView
    last_documented: UncertainDate | None
    first_documentation: UncertainDate | None
    creation: UncertainDate | None
    """The Creation event's Observed date; `null`: unknown, never inferred."""
    attribution: AttributionReadout
    gallery: list[DocumentationSummary]
    where: Where
    series: list[RecordLink]
    timeline: TimelineView
    sources: list[RecordLink]
    related: Related


class Membership(BaseModel):
    artist: RecordLink
    period: Period | None


class AttributedArtwork(BaseModel):
    artwork: ArtworkCard
    certainty: Certainty
    alias: str | None


class ArtistView(Visibility):
    kind: Literal["artist"] = "artist"
    id: int
    path: str
    name: str | None
    artist_kind: ArtistKind
    aliases: list[str]
    period: Period | None
    biography: str | None
    areas: list[RecordLink]
    collectives: list[Membership]
    """The collectives this Artist is a member of."""
    members: list[Membership]
    """The members of this collective."""
    artworks: list[AttributedArtwork]
    sources: list[RecordLink]


class LocationView(Visibility):
    kind: Literal["location"] = "location"
    id: int
    path: str
    title: LocationTitle
    place_description: str | None
    surface_type: str
    geometry: dict[str, Any] | None
    approximate: bool
    uncertainty_radius: int | None
    site: RecordLink | None
    areas: list[RecordLink]
    nearby: list[NearbyLocation] = []
    """The public Locations within 500 m of this one, for the mini-map."""
    stratigraphy: list[ArtworkCard]
    """Most recent first; empty: "No public artworks here"."""
    disappearances: list[DocumentationSummary]
    """The Documentation items of disappearances here."""


class PlaceView(Visibility):
    """A Site, an Area, or a Series."""

    kind: Literal["site", "area", "series"]
    id: int
    path: str
    name: str | None
    description: str | None
    geometry: dict[str, Any] | None = None
    """An Area's polygon."""
    locations: list[LocationSummary]
    """Where its Artworks are, for the map."""
    artworks: list[ArtworkCard]
    sources: list[RecordLink]


class SourceView(Visibility):
    kind: Literal["source"] = "source"
    id: int
    path: str
    title: str | None
    author: str | None
    publication: str | None
    date: UncertainDate | None
    url: str | None
    note: str | None
    language: str | None
    cited_by: list[RecordLink]


class DocumentationItemView(Visibility):
    kind: Literal["documentation_item"] = "documentation_item"
    id: int
    path: str
    medium: Medium
    observed_date: UncertainDate
    submitted_at: datetime
    approved_at: datetime
    """From the Revision that created it."""
    file: str | None
    renditions: dict[str, Rendition] | None
    alt_text: str | None
    creator_credit: str | None
    licence: str | None
    rights_basis: RightsBasis | None
    origin_url: str | None
    text: str | None
    url: str | None
    language: str | None
    artworks: list[ArtworkCard]
    location: LocationSummary | None
    """For the documentation of a disappearance."""


class Change(BaseModel):
    """One operation of a Revision's change list, values as stored."""

    op: Literal["set", "add", "change", "remove"]
    field: str | None = None
    collection: str | None = None
    old: Any = None
    new: Any = None
    item: Any = None
    redacted: bool = False
    """The public sees the field or collection name only."""
    redacted_at: datetime | None = None
    """For Moderators only."""
    old_redacted: bool = False
    """The previous value came from a redacted operation, so it is hidden too."""


class RevisionView(BaseModel):
    id: int
    """The anchor of the Timeline's provenance links."""
    submitter: str | None
    """The Submitter's display name; never the approving Moderator."""
    submitted_at: datetime
    approved_at: datetime
    changes: list[Change]


class RevisionsView(BaseModel):
    record: RecordLink
    merged_into: RecordLink | None
    """A merged duplicate's surviving record: the page shows a "merged into" notice."""
    withdrawn_at: datetime | None = None
    """For Moderators only."""
    revisions: list[RevisionView]
    """Most recent first."""
    records: dict[str, RecordLink]
    """The public records the change lists refer to, by id."""


class IndexPage(BaseModel):
    items: list[RecordLink]
    """Alphabetical in the Content language."""
    page: int
    page_size: int
    total: int


RecordView = (
    ArtworkView | ArtistView | LocationView | PlaceView | SourceView | DocumentationItemView
)
