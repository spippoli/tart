"""The read side of the archive: public views of records, by caller (archive-records spec,
Visibility and Public record pages).

    reader = Reader(connection, Viewer(moderator=False))
    view = await reader.view(Kind.ARTWORK, 4821)

A record is *listed* when it exists, is not withdrawn, and is not a merged duplicate:
only listed records appear as links, citations, cards, and in indexes, for every
caller. Withdrawn content disappears without a trace. A Moderator reaches a withdrawn
record at its own URL, and sees redacted values on the pages, marked; the public gets
410 and placeholders. Records hold only approved data: a record that exists only in a
pending Submission has no row here, so it is 404 for everyone.
"""

import json
from collections.abc import Iterable
from dataclasses import dataclass, field, fields, replace
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from geoalchemy2 import Geography
from sqlalchemy import Text, cast, exists, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncConnection

from tart.archive import (
    ApprovedEvent,
    ApprovedItem,
    Area,
    Artist,
    Artwork,
    Certainty,
    ConditionReading,
    DateRange,
    DocumentationItem,
    Kind,
    Location,
    Medium,
    Precision,
    Record,
    RecordId,
    Revision,
    Series,
    Site,
    Source,
    Stratum,
    attribution_readout,
    creation_event,
    derive_condition,
    evidence_level,
    first_documentation,
    last_documented,
    location_title,
    record_path_segment,
    shown_attribution,
    stratigraphy,
    timeline,
)
from tart.archive.codec import encode, encode_period, encode_uncertain_date
from tart.archive_persistence import PostgresArchiveStore
from tart.archive_persistence import tables as t
from tart.archive_read import views as v
from tart.auth.tables import user_account
from tart.discovery.filters import NAME_THRESHOLD, normalise_query
from tart.media.tables import upload

RELATED_LIMIT = 24
"""Artworks per "Related" list; the Artist and Series pages list them all."""
INDEX_PAGE_SIZE = 24
NEARBY_METRES = 500
"""How far the mini-map looks for Locations to show muted (Discovery spec, Mini-map)."""

SLUGGED = frozenset({Kind.ARTWORK, Kind.ARTIST, Kind.SITE, Kind.AREA, Kind.SERIES})
"""The kinds whose route carries a slug; the others are canonical at the bare id."""

_NAMED = {Kind.ARTIST: t.artist, Kind.SITE: t.site, Kind.AREA: t.area, Kind.SERIES: t.series}
"""The kinds that have an index, by their table."""


class RecordNotFoundError(Exception):
    """No record of this kind has the id, or it exists only in a pending Submission."""


class RecordWithdrawnError(Exception):
    """The record is withdrawn: 410 with a neutral page."""


class RecordMergedError(Exception):
    """The id is a merged duplicate or a retired Documentation item: 301 to `target`."""

    def __init__(self, target: RecordId) -> None:
        super().__init__(target)
        self.target = target


@dataclass(frozen=True)
class Viewer:
    """Who is reading. Pending content (for its Submitter and Moderators) comes with
    Submissions; until then only the Moderator role changes a view."""

    moderator: bool = False


@dataclass(frozen=True)
class _State:
    kind: Kind
    withdrawn_at: datetime | None
    merged_into: RecordId | None


def _json_key(collection: str, item: Any) -> Any:
    """The key of a collection item in its JSON form, as `item_key` gives it."""
    match collection:
        case "attributions":
            return item["artist"]
        case "history_events":
            return item["id"]
        case "crew_memberships":
            return json.dumps([item["collective"], item["period"]], sort_keys=True)
    return item


@dataclass
class _History:
    """A record's Revisions walked in order, with what its Redactions hide."""

    revisions: tuple[Revision, ...]
    redacted: dict[tuple[int, int], datetime]
    """(Revision id, operation index) of each redacted operation."""
    current: dict[tuple[str, Any], tuple[int, int]] = field(default_factory=dict)
    """The operation that set each field, or added or last changed each item."""
    old_hidden: set[tuple[int, int]] = field(default_factory=set)
    """Operations whose previous value came from a redacted operation."""
    event_revisions: dict[int, Revision] = field(default_factory=dict)
    """The Revision that introduced each History event."""

    def __post_init__(self) -> None:
        for revision in self.revisions:
            for index, change in enumerate(revision.changes):
                position = (revision.id, index)
                match change["op"]:
                    case "set":
                        key: tuple[str, Any] = (str(change["field"]), None)
                    case "add":
                        collection = str(change["collection"])
                        key = (collection, _json_key(collection, change["item"]))
                        if collection == "history_events":
                            self.event_revisions.setdefault(change["item"]["id"], revision)
                    case "change":
                        collection = str(change["collection"])
                        key = (collection, _json_key(collection, change["new"]))
                    case _:
                        collection = str(change["collection"])
                        self.current.pop((collection, _json_key(collection, change["item"])), None)
                        continue
                if self.current.get(key) in self.redacted:
                    self.old_hidden.add(position)
                self.current[key] = position

    def hidden(self) -> dict[tuple[str, Any], datetime]:
        """The current values and items that a Redaction hides, with its date."""
        return {
            key: self.redacted[position]
            for key, position in self.current.items()
            if position in self.redacted
        }


@dataclass(frozen=True)
class _Shown[R: Record]:
    """A record as the viewer sees it, Redactions applied."""

    record: R
    hidden: dict[tuple[str, Any], datetime]

    @property
    def redacted_fields(self) -> list[str]:
        return sorted({name for (name, key) in self.hidden if key is None})


def _apply_redactions[R: Record](record: R, hidden: dict[tuple[str, Any], datetime]) -> R:
    values: dict[str, Any] = {}
    for record_field in fields(record):  # type: ignore[arg-type]
        name = record_field.name
        value = getattr(record, name)
        if (name, None) in hidden:
            values[name] = () if isinstance(value, tuple) else None
        elif name in record.COLLECTIONS:
            values[name] = tuple(
                item for item in value if (name, _json_key(name, encode(item))) not in hidden
            )
    return replace(record, **values)


def _date(value: Any) -> v.UncertainDate | None:
    return v.UncertainDate.model_validate(encode_uncertain_date(value)) if value else None


def _period(value: Any) -> v.Period | None:
    return v.Period.model_validate(encode_period(value)) if value else None


@dataclass(frozen=True)
class ArtworkFacts:
    """What the public derives from an Artwork, for the Discovery index: the domain rules
    applied to the Artwork's public events and Documentation items."""

    artwork: Artwork
    condition: ConditionReading
    creation: DateRange | None
    """The Creation event's range; `None` without a dated Creation event."""
    documented: tuple[DateRange, ...]
    """The range of each dated public Documentation item."""
    first_documented: datetime | None
    last_documented: datetime | None
    """The chronological keys of the first and the last public Documentation item."""
    added_at: datetime
    """The approval of the Artwork's first Revision."""
    attribution: tuple[str, ...]
    """Any of `unknown`, `attributed`, `disputed`."""
    artists: tuple[str, ...]
    """The names and Aliases of the Artists it is attributed to, publicly."""
    series: tuple[str, ...]
    site: str | None
    areas: tuple[str, ...]


class Reader:
    """The views of one request, over one connection; it caches what it reads."""

    def __init__(self, connection: AsyncConnection, viewer: Viewer) -> None:
        self.connection = connection
        self.store = PostgresArchiveStore(connection)
        self.viewer = viewer
        self._states: dict[RecordId, _State | None] = {}
        self._histories: dict[RecordId, _History] = {}
        self._shown: dict[RecordId, _Shown[Any]] = {}

    # Visibility.

    async def _load_states(self, ids: Iterable[RecordId]) -> None:
        missing = [id_ for id_ in set(ids) if id_ not in self._states]
        if not missing:
            return
        rows = await self.connection.execute(
            select(
                t.record.c.id, t.record.c.kind, t.record.c.withdrawn_at, t.record.c.merged_into
            ).where(t.record.c.id.in_(missing))
        )
        for id_ in missing:
            self._states[id_] = None
        for row in rows:
            self._states[row.id] = _State(Kind(row.kind), row.withdrawn_at, row.merged_into)

    async def listed(self, ids: Iterable[RecordId | None]) -> list[RecordId]:
        """Those of the ids, in order and without repeats, that are listed."""
        wanted = list(dict.fromkeys(id_ for id_ in ids if id_ is not None))
        await self._load_states(wanted)
        return [
            id_
            for id_ in wanted
            if (state := self._states[id_]) is not None
            and state.withdrawn_at is None
            and state.merged_into is None
        ]

    async def resolve(self, kind: Kind, record_id: RecordId, *, merged_ok: bool = False) -> _State:
        """The state of a record the viewer may open, or the error its URL answers."""
        await self._load_states([record_id])
        state = self._states[record_id]
        if state is None or state.kind is not kind:
            raise RecordNotFoundError(record_id)
        if state.merged_into is not None and not merged_ok:
            target, seen = state.merged_into, {record_id}
            while True:  # merged_into is kept final; follow it anyway, never in a loop
                await self._load_states([target])
                next_state = self._states[target]
                if next_state is None or next_state.merged_into is None or target in seen:
                    break
                seen.add(target)
                target = next_state.merged_into
            raise RecordMergedError(target)
        if state.withdrawn_at is not None and not self.viewer.moderator:
            raise RecordWithdrawnError(record_id)
        return state

    async def _history(self, record_id: RecordId) -> _History:
        if record_id not in self._histories:
            revisions = await self.store.revisions_of(record_id)
            rows = await self.connection.execute(
                select(
                    t.redaction.c.revision_id, t.redaction.c.operation, t.redaction.c.redacted_at
                )
                .join(t.revision, t.revision.c.id == t.redaction.c.revision_id)
                .where(t.revision.c.record_id == record_id)
            )
            redacted = {(row.revision_id, row.operation): row.redacted_at for row in rows}
            self._histories[record_id] = _History(revisions, redacted)
        return self._histories[record_id]

    async def shown(self, record_id: RecordId) -> _Shown[Any]:
        if record_id not in self._shown:
            record = await self.store.get(record_id)
            assert record is not None
            hidden = (await self._history(record_id)).hidden()
            if hidden and not self.viewer.moderator:
                record = _apply_redactions(record, hidden)
            self._shown[record_id] = _Shown(record, hidden)
        return self._shown[record_id]

    def _visibility(self, state: _State, shown: _Shown[Any]) -> dict[str, Any]:
        if not self.viewer.moderator:
            return {"redacted_fields": shown.redacted_fields}
        return {
            "redacted_fields": [],
            "withdrawn_at": state.withdrawn_at,
            "redactions": [
                v.Redaction(field=name, item=key, redacted_at=at)
                for (name, key), at in shown.hidden.items()
            ],
        }

    # Links.

    async def _name(self, record_id: RecordId) -> str | None:
        record = (await self.shown(record_id)).record
        match record:
            case Artwork():
                return record.title
            case Artist() | Site() | Area() | Series():
                return record.name
            case Source():
                return record.title
        return None

    async def _path(self, kind: Kind, record_id: RecordId) -> str:
        if kind in SLUGGED:
            return record_path_segment(record_id, await self._name(record_id))
        return str(record_id)

    async def link(self, record_id: RecordId) -> v.RecordLink:
        state = self._states[record_id]
        assert state is not None
        title = await self._location_title(record_id) if state.kind is Kind.LOCATION else None
        return v.RecordLink(
            kind=state.kind,
            id=record_id,
            path=await self._path(state.kind, record_id),
            name=await self._name(record_id),
            location_title=title,
        )

    async def links(self, ids: Iterable[RecordId | None]) -> list[v.RecordLink]:
        return [await self.link(id_) for id_ in await self.listed(ids)]

    async def _areas(self, location_id: RecordId) -> list[RecordId]:
        location = (await self.shown(location_id)).record
        if location.geometry is None:  # redacted: no membership to show
            return []
        return await self.listed(await self.store.areas_of_location(location_id))

    async def _location_title(self, location_id: RecordId) -> v.LocationTitle:
        location = (await self.shown(location_id)).record
        [site] = await self.listed([location.site]) or [None]
        site_name = await self._name(site) if site is not None else None
        area_names = [await self._name(area) for area in await self._areas(location_id)]
        title = location_title(
            location, site_name, sorted(name for name in area_names if name is not None)
        )
        return v.LocationTitle(
            place_description=title.place_description,
            surface_type=title.surface_type,
            place=title.place,
        )

    async def _point(self, location_id: RecordId, location: Location) -> tuple[float, float] | None:
        """Where the Location's sign sits; `None` when the geometry is redacted."""
        if location.geometry is None:
            return None
        stored = await self.connection.scalar(
            select(func.ST_AsGeoJSON(t.location.c.representative_point, 6)).where(
                t.location.c.id == location_id
            )
        )
        longitude, latitude = json.loads(stored)["coordinates"]
        return (longitude, latitude)

    async def _location_summary(self, location_id: RecordId) -> v.LocationSummary:
        location: Location = (await self.shown(location_id)).record
        return v.LocationSummary(
            id=location_id,
            path=str(location_id),
            title=await self._location_title(location_id),
            surface_type=location.surface_type,
            geometry=location.geometry.to_geojson() if location.geometry else None,
            point=await self._point(location_id, location),
            approximate=location.approximate,
            uncertainty_radius=location.uncertainty_radius,
        )

    # Artworks: approved events, documentation, cards.

    async def _approved_events(self, artwork_id: RecordId) -> list[ApprovedEvent]:
        artwork: Artwork = (await self.shown(artwork_id)).record
        history = await self._history(artwork_id)
        return [
            ApprovedEvent(event, history.event_revisions[event.id].provenance.approved_at)
            for event in artwork.history_events
        ]

    async def _documentation(self, artwork_id: RecordId) -> list[ApprovedItem]:
        """The listed Documentation items of the Artwork, with their latest approval."""
        ids = await self.store.documentation_items_of([artwork_id])
        items = []
        for item_id in await self.listed(sorted(ids)):
            item: DocumentationItem = (await self.shown(item_id)).record
            if artwork_id not in item.artworks:  # the link itself is redacted
                continue
            revisions = (await self._history(item_id)).revisions
            items.append(ApprovedItem(item_id, item, revisions[-1].provenance.approved_at))
        return items

    async def _public(self, ids: Iterable[RecordId | None]) -> frozenset[RecordId]:
        return frozenset(await self.listed(ids))

    async def _condition(self, events: list[ApprovedEvent]) -> v.ConditionView:
        reading = derive_condition(events)
        level = None
        if reading.event is not None:
            citations = reading.event.event.citations
            level = evidence_level(citations, await self._public(citations))  # type: ignore[arg-type]
        return v.ConditionView(
            condition=reading.condition,
            group=reading.group,
            since=_date(reading.event.observed_date) if reading.event else None,
            evidence_level=level,
            event=reading.event.id if reading.event else None,
        )

    # What Discovery reads.

    async def facts(self, artwork_id: RecordId, time_zone: ZoneInfo) -> ArtworkFacts:
        """The Artwork's derived facts as the public sees them (Redactions applied)."""
        artwork: Artwork = (await self.shown(artwork_id)).record
        events = await self._approved_events(artwork_id)
        items = await self._documentation(artwork_id)
        history = await self._history(artwork_id)

        def submitted_on(revision: Revision) -> date:
            return revision.provenance.submitted_at.astimezone(time_zone).date()

        # An `unknown` date has no range worth matching: it stays out of the date filters.
        creation = creation_event(events)
        created = None
        if creation is not None and creation.observed_date.precision is not Precision.UNKNOWN:
            revision = history.event_revisions[creation.id]
            created = creation.observed_date.range(submitted_on(revision))
        documented = []
        for item in items:
            if item.observed_date.precision is not Precision.UNKNOWN:
                latest = (await self._history(item.id)).revisions[-1]
                documented.append(item.observed_date.range(submitted_on(latest)))
        first = first_documentation(items)
        last = last_documented(items)

        public = await self._public(a.artist for a in artwork.attributions)  # type: ignore[misc]
        readout = attribution_readout(artwork, public)
        artists: list[str] = []
        for shown in (*readout.attributed, *readout.disputed):
            artist: Artist = (await self.shown(shown.attribution.artist)).record  # type: ignore[arg-type]
            artists += [name for name in (artist.name, *artist.aliases) if name]
        states = [
            state
            for state, present in (
                ("unknown", readout.unknown),
                ("attributed", bool(readout.attributed)),
                ("disputed", bool(readout.disputed)),
            )
            if present
        ]

        site_name = None
        area_names: list[str] = []
        if await self.listed([artwork.location]):  # type: ignore[list-item]
            location: Location = (await self.shown(artwork.location)).record  # type: ignore[arg-type]
            [site] = await self.listed([location.site]) or [None]  # type: ignore[list-item]
            site_name = await self._name(site) if site is not None else None
            area_names = [
                name
                for area in await self._areas(artwork.location)  # type: ignore[arg-type]
                if (name := await self._name(area)) is not None
            ]
        series_names = [
            name
            for series in await self.listed(artwork.series)  # type: ignore[arg-type]
            if (name := await self._name(series)) is not None
        ]
        return ArtworkFacts(
            artwork=artwork,
            condition=derive_condition(events),
            creation=created,
            documented=tuple(documented),
            first_documented=first.observed_date.chronological_key if first else None,
            last_documented=last.observed_date.chronological_key if last else None,
            added_at=history.revisions[0].provenance.approved_at,
            attribution=tuple(states),
            artists=tuple(artists),
            series=tuple(series_names),
            site=site_name,
            areas=tuple(area_names),
        )

    async def stratigraphy_of(self, location_id: RecordId) -> tuple[RecordId, ...]:
        """The listed Artworks on a Location, most recent first."""
        strata = []
        for artwork_id in await self.listed(await self.store.artworks_on_location(location_id)):
            events = await self._approved_events(artwork_id)
            documentation = await self._documentation(artwork_id)
            strata.append(
                Stratum(artwork_id, creation_event(events), first_documentation(documentation))
            )
        return stratigraphy(strata)

    async def entry(self, artwork_id: RecordId) -> v.ListEntry:
        """The Artwork as a list entry: the card, where it is, who by, and its thumbnail."""
        card = await self.card(artwork_id)
        artwork: Artwork = (await self.shown(artwork_id)).record
        where = await self.where(artwork.location)
        public = await self._public(a.artist for a in artwork.attributions)  # type: ignore[misc]
        readout = attribution_readout(artwork, public)
        items = await self._documentation(artwork_id)
        picture = last_documented(
            [
                item
                for item in items
                if item.item.medium in (Medium.IMAGE, Medium.PDF) and item.item.file
            ]
        )
        latest = last_documented(items)
        return v.ListEntry(
            **card.model_dump(),
            location=artwork.location,  # type: ignore[arg-type]
            site=where.site,
            area=where.areas[0] if where.areas else None,
            approximate=bool(where.location and where.location.approximate),
            attributed=[await self.link(a.attribution.artist) for a in readout.attributed],  # type: ignore[arg-type]
            disputed=[await self.link(a.attribution.artist) for a in readout.disputed],  # type: ignore[arg-type]
            probable=[
                a.attribution.artist  # type: ignore[misc]
                for a in readout.attributed
                if a.certainty is Certainty.PROBABLE
            ],
            thumbnail=await self._documentation_summary(picture.id) if picture else None,
            latest_item_medium=latest.item.medium if latest else None,
        )

    async def entries(self, ids: Iterable[RecordId]) -> list[v.ListEntry]:
        return [await self.entry(id_) for id_ in await self.listed(ids)]

    async def card(self, artwork_id: RecordId) -> v.ArtworkCard:
        artwork: Artwork = (await self.shown(artwork_id)).record
        latest = last_documented(await self._documentation(artwork_id))
        return v.ArtworkCard(
            id=artwork_id,
            path=await self._path(Kind.ARTWORK, artwork_id),
            title=artwork.title,
            expression_types=list(artwork.expression_types),
            condition=await self._condition(await self._approved_events(artwork_id)),
            last_documented=_date(latest.observed_date) if latest else None,
        )

    async def cards(self, ids: Iterable[RecordId]) -> list[v.ArtworkCard]:
        return [await self.card(id_) for id_ in await self.listed(ids)]

    async def _renditions(self, file: str | None) -> dict[str, v.Rendition] | None:
        if file is None:
            return None
        sizes = await self.connection.scalar(
            select(upload.c.renditions).where(func.cast(upload.c.id, Text) == file)
        )
        return {name: v.Rendition(width=w, height=h) for name, (w, h) in (sizes or {}).items()}

    async def _documentation_summary(self, item_id: RecordId) -> v.DocumentationSummary:
        item: DocumentationItem = (await self.shown(item_id)).record
        return v.DocumentationSummary(
            id=item_id,
            path=str(item_id),
            medium=item.medium,
            observed_date=_date(item.observed_date),
            file=item.file,
            renditions=await self._renditions(item.file),
            alt_text=item.alt_text,
            creator_credit=item.creator_credit,
            licence=item.licence,
            text=item.text,
            url=item.url,
            language=item.language,
        )

    async def _citations(self, ids: Iterable[RecordId]) -> list[v.Citation]:
        return [v.Citation(**link.model_dump()) for link in await self.links(ids)]

    # Views.

    async def view(self, kind: Kind, record_id: RecordId) -> v.RecordView:
        state = await self.resolve(kind, record_id)
        shown = await self.shown(record_id)
        visibility = self._visibility(state, shown)
        match kind:
            case Kind.ARTWORK:
                return await self._artwork(record_id, shown.record, visibility)
            case Kind.ARTIST:
                return await self._artist(record_id, shown.record, visibility)
            case Kind.LOCATION:
                return await self._location(record_id, shown.record, visibility)
            case Kind.SITE | Kind.AREA | Kind.SERIES:
                return await self._place(kind, record_id, shown.record, visibility)
            case Kind.SOURCE:
                return await self._source(record_id, shown.record, visibility)
        return await self._documentation_item(record_id, shown.record, visibility)

    async def _artwork(
        self, artwork_id: RecordId, artwork: Artwork, visibility: dict[str, Any]
    ) -> v.ArtworkView:
        events = await self._approved_events(artwork_id)
        items = await self._documentation(artwork_id)
        history = await self._history(artwork_id)
        cited = [
            cited
            for claim in (*artwork.attributions, *artwork.history_events)
            for cited in claim.citations
        ]
        public = await self._public([*cited, *(a.artist for a in artwork.attributions)])
        readout = attribution_readout(artwork, public)

        async def shown_attributions(group: tuple[Any, ...]) -> list[v.ShownAttribution]:
            return [
                v.ShownAttribution(
                    artist=await self.link(shown.attribution.artist),  # type: ignore[arg-type]
                    certainty=shown.certainty,
                    alias=shown.attribution.alias,
                    note=shown.attribution.note,
                    evidence_level=shown.evidence_level,
                    citations=await self._citations(shown.attribution.citations),  # type: ignore[arg-type]
                )
                for shown in group
            ]

        entries: dict[str, list[v.TimelineEntry]] = {"dated": [], "undated": []}
        ordered = timeline(events, items)
        for name, group in (("dated", ordered.dated), ("undated", ordered.undated)):
            for entry in group:
                if isinstance(entry, ApprovedEvent):
                    event = entry.event
                    revision = history.event_revisions[entry.id]
                    [covering] = await self.listed([event.covering]) or [None]  # type: ignore[list-item]
                    entries[name].append(
                        v.EventEntry(
                            id=entry.id,
                            type=event.type,
                            observed_date=_date(event.observed_date),
                            condition=event.condition,
                            submitted_at=revision.provenance.submitted_at,
                            approved_at=revision.provenance.approved_at,
                            revision=revision.id,
                            evidence_level=evidence_level(event.citations, public),
                            citations=await self._citations(event.citations),  # type: ignore[arg-type]
                            note=event.note,
                            covering=await self.link(covering) if covering else None,
                        )
                    )
                else:
                    entries[name].append(
                        v.ItemEntry(
                            id=entry.id,
                            path=str(entry.id),
                            medium=entry.item.medium,
                            observed_date=_date(entry.observed_date),
                        )
                    )

        creation = creation_event(events)
        first = first_documentation(items)
        latest = last_documented(items)
        gallery = sorted(
            items,
            key=lambda item: item.observed_date.chronological_key or datetime.min,
            reverse=True,
        )
        return v.ArtworkView(
            id=artwork_id,
            path=await self._path(Kind.ARTWORK, artwork_id),
            title=artwork.title,
            expression_types=list(artwork.expression_types),
            description=artwork.description,
            condition=await self._condition(events),
            last_documented=_date(latest.observed_date) if latest else None,
            first_documentation=_date(first.observed_date) if first else None,
            creation=_date(creation.observed_date) if creation else None,
            attribution=v.AttributionReadout(
                attributed=await shown_attributions(readout.attributed),
                disputed=await shown_attributions(readout.disputed),
            ),
            gallery=[await self._documentation_summary(item.id) for item in gallery],
            where=await self.where(artwork.location),
            series=await self.links(artwork.series),  # type: ignore[arg-type]
            timeline=v.TimelineView(**entries),
            sources=await self.links(artwork.sources),  # type: ignore[arg-type]
            related=await self._related(artwork_id, artwork, public),
            **visibility,
        )

    async def where(self, location_id: Any) -> v.Where:
        if location_id is None or not await self.listed([location_id]):
            # Withdrawn (or redacted): a placeholder, and nothing that would place it.
            return v.Where(location=None, location_withdrawn=True, site=None, areas=[])
        location: Location = (await self.shown(location_id)).record
        [site] = await self.listed([location.site]) or [None]
        return v.Where(
            location=await self._location_summary(location_id),
            location_withdrawn=False,
            site=await self.link(site) if site else None,
            areas=await self.links(await self._areas(location_id)),
            nearby=await self._nearby(location_id),
        )

    async def _nearby(self, location_id: RecordId) -> list[v.NearbyLocation]:
        """The other listed Locations whose representative point is within 500 m."""
        if (await self.shown(location_id)).record.geometry is None:  # redacted: no place to show
            return []
        here = select(t.location.c.representative_point).where(t.location.c.id == location_id)
        there = t.location.c.representative_point
        rows = await self.connection.execute(
            select(t.location.c.id, func.ST_AsGeoJSON(there, 6))
            .join(t.record, t.record.c.id == t.location.c.id)
            .where(
                t.location.c.id != location_id,
                t.record.c.withdrawn_at.is_(None),
                t.record.c.merged_into.is_(None),
                func.ST_DWithin(
                    cast(there, Geography),
                    cast(here.scalar_subquery(), Geography),
                    NEARBY_METRES,
                ),
            )
            .order_by(t.location.c.id)
        )
        return [
            v.NearbyLocation(id=id_, point=tuple(json.loads(point)["coordinates"]))  # type: ignore[arg-type]
            for id_, point in rows
        ]

    async def _related(
        self, artwork_id: RecordId, artwork: Artwork, public: frozenset[RecordId]
    ) -> v.Related:
        async def others(ids: Iterable[RecordId]) -> list[v.ArtworkCard]:
            listed = [id_ for id_ in await self.listed(ids) if id_ != artwork_id]
            return await self.cards(listed[:RELATED_LIMIT])

        same_location: list[RecordId] = []
        if await self.listed([artwork.location]):  # type: ignore[list-item]
            same_location = list(await self.store.artworks_on_location(artwork.location))  # type: ignore[arg-type]
        artists = [a.artist for a in artwork.attributions if a.artist in public]
        by_artist = await self.connection.scalars(
            select(t.attribution.c.artwork_id)
            .where(t.attribution.c.artist_id.in_(artists))
            .order_by(t.attribution.c.artwork_id)
        )
        in_series = await self.connection.scalars(
            select(t.artwork_series.c.artwork_id)
            .where(t.artwork_series.c.series_id.in_(await self.listed(artwork.series)))  # type: ignore[arg-type]
            .order_by(t.artwork_series.c.artwork_id)
        )
        return v.Related(
            same_location=await others(same_location),
            same_artist=await others(list(by_artist)),
            same_series=await others(list(in_series)),
        )

    async def _artist(
        self, artist_id: RecordId, artist: Artist, visibility: dict[str, Any]
    ) -> v.ArtistView:
        collectives = [
            v.Membership(artist=await self.link(crew.collective), period=_period(crew.period))  # type: ignore[arg-type]
            for crew in artist.crew_memberships
            if await self.listed([crew.collective])  # type: ignore[list-item]
        ]
        rows = await self.connection.execute(
            select(t.crew_membership.c.member_id)
            .where(t.crew_membership.c.collective_id == artist_id)
            .order_by(t.crew_membership.c.member_id, t.crew_membership.c.position)
        )
        members = []
        for member_id in await self.listed(row.member_id for row in rows):
            member: Artist = (await self.shown(member_id)).record
            for crew in member.crew_memberships:  # a redacted membership is gone here
                if crew.collective == artist_id:
                    members.append(
                        v.Membership(artist=await self.link(member_id), period=_period(crew.period))
                    )
        attributed = await self.connection.scalars(
            select(t.attribution.c.artwork_id)
            .where(t.attribution.c.artist_id == artist_id)
            .order_by(t.attribution.c.artwork_id)
        )
        artworks = []
        for artwork_id in await self.listed(attributed):
            artwork: Artwork = (await self.shown(artwork_id)).record
            for attribution in artwork.attributions:
                if attribution.artist == artist_id:
                    shown = shown_attribution(
                        attribution,
                        await self._public(attribution.citations),  # type: ignore[arg-type]
                    )
                    artworks.append(
                        v.AttributedArtwork(
                            artwork=await self.card(artwork_id),
                            certainty=shown.certainty,
                            alias=attribution.alias,
                        )
                    )
        return v.ArtistView(
            id=artist_id,
            path=await self._path(Kind.ARTIST, artist_id),
            name=artist.name,
            artist_kind=artist.kind,
            aliases=list(artist.aliases),
            period=_period(artist.period),
            biography=artist.biography,
            areas=await self.links(artist.areas),  # type: ignore[arg-type]
            collectives=collectives,
            members=members,
            artworks=artworks,
            sources=await self.links(artist.sources),  # type: ignore[arg-type]
            **visibility,
        )

    async def _location(
        self, location_id: RecordId, location: Location, visibility: dict[str, Any]
    ) -> v.LocationView:
        disappearances = await self.connection.scalars(
            select(t.documentation_item.c.id)
            .where(t.documentation_item.c.location_id == location_id)
            .order_by(t.documentation_item.c.id)
        )
        [site] = await self.listed([location.site]) or [None]  # type: ignore[list-item]
        return v.LocationView(
            id=location_id,
            path=str(location_id),
            title=await self._location_title(location_id),
            place_description=location.place_description,
            surface_type=location.surface_type,
            geometry=location.geometry.to_geojson() if location.geometry else None,
            point=await self._point(location_id, location),
            approximate=location.approximate,
            uncertainty_radius=location.uncertainty_radius,
            site=await self.link(site) if site else None,
            areas=await self.links(await self._areas(location_id)),
            nearby=await self._nearby(location_id),
            stratigraphy=await self.cards(await self.stratigraphy_of(location_id)),
            disappearances=[
                await self._documentation_summary(item_id)
                for item_id in await self.listed(disappearances)
                if (await self.shown(item_id)).record.location == location_id
            ],
            **visibility,
        )

    async def _place(
        self,
        kind: Kind,
        record_id: RecordId,
        record: Site | Area | Series,
        visibility: dict[str, Any],
    ) -> v.PlaceView:
        geometry = None
        match record:
            case Site():
                locations = await self.connection.scalars(
                    select(t.location.c.id).where(t.location.c.site_id == record_id)
                )
                location_ids = list(locations)
            case Area():
                geometry = record.geometry.to_geojson() if record.geometry else None
                locations = await self.connection.scalars(
                    select(t.location.c.id)
                    .join(t.area, func.ST_Intersects(t.area.c.geometry, t.location.c.geometry))
                    .where(t.area.c.id == record_id)
                )
                location_ids = list(locations) if geometry else []
            case _:
                location_ids = []
        if isinstance(record, Series):
            artworks = await self.connection.scalars(
                select(t.artwork_series.c.artwork_id)
                .where(t.artwork_series.c.series_id == record_id)
                .order_by(t.artwork_series.c.artwork_id)
            )
            artwork_ids = [
                id_
                for id_ in await self.listed(artworks)
                if record_id in (await self.shown(id_)).record.series
            ]
            location_ids = [(await self.shown(id_)).record.location for id_ in artwork_ids]
        else:
            location_ids = await self.listed(sorted(location_ids))
            if isinstance(record, Site):
                location_ids = [
                    id_ for id_ in location_ids if (await self.shown(id_)).record.site == record_id
                ]
            artworks = await self.connection.scalars(
                select(t.artwork.c.id)
                .where(t.artwork.c.location_id.in_(location_ids))
                .order_by(t.artwork.c.id)
            )
            artwork_ids = list(artworks)
        listed_locations = await self.listed(location_ids)
        cards = await self.cards(artwork_ids)
        counts: dict[RecordId, dict[str, int]] = {}
        for card in cards:
            on = (await self.shown(card.id)).record.location
            group = counts.setdefault(on, {})
            group[card.condition.group.value] = group.get(card.condition.group.value, 0) + 1
        return v.PlaceView(
            kind=kind.value,  # type: ignore[arg-type]
            id=record_id,
            path=await self._path(kind, record_id),
            name=record.name,
            description=record.description,
            geometry=geometry,
            locations=[
                v.PlaceLocation(
                    **(await self._location_summary(id_)).model_dump(), **counts.get(id_, {})
                )
                for id_ in listed_locations
            ],
            artworks=cards,
            sources=await self.links(record.sources),  # type: ignore[arg-type]
            **visibility,
        )

    async def _source(
        self, source_id: RecordId, source: Source, visibility: dict[str, Any]
    ) -> v.SourceView:
        candidates = [
            *await self.connection.scalars(
                select(t.record_source.c.record_id).where(t.record_source.c.source_id == source_id)
            ),
            *await self.connection.scalars(
                select(t.attribution_citation.c.artwork_id).where(
                    t.attribution_citation.c.cited_id == source_id
                )
            ),
            *await self.connection.scalars(
                select(t.history_event.c.artwork_id)
                .join(
                    t.history_event_citation,
                    t.history_event_citation.c.event_id == t.history_event.c.id,
                )
                .where(t.history_event_citation.c.cited_id == source_id)
            ),
        ]
        citing = []
        for record_id in await self.listed(sorted(set(candidates))):
            record = (await self.shown(record_id)).record
            claims = [
                *getattr(record, "attributions", ()),
                *getattr(record, "history_events", ()),
            ]
            if source_id in getattr(record, "sources", ()) or any(
                source_id in claim.citations for claim in claims
            ):
                citing.append(record_id)
        return v.SourceView(
            id=source_id,
            path=str(source_id),
            title=source.title,
            author=source.author,
            publication=source.publication,
            date=_date(source.date),
            url=source.url,
            note=source.note,
            language=source.language,
            cited_by=await self.links(citing),
            **visibility,
        )

    async def _documentation_item(
        self, item_id: RecordId, item: DocumentationItem, visibility: dict[str, Any]
    ) -> v.DocumentationItemView:
        created = (await self._history(item_id)).revisions[0].provenance
        location = item.location if item.location and await self.listed([item.location]) else None  # type: ignore[list-item]
        return v.DocumentationItemView(
            id=item_id,
            path=str(item_id),
            medium=item.medium,
            observed_date=_date(item.observed_date),
            submitted_at=created.submitted_at,
            approved_at=created.approved_at,
            file=item.file,
            renditions=await self._renditions(item.file),
            alt_text=item.alt_text,
            creator_credit=item.creator_credit,
            licence=item.licence,
            rights_basis=item.rights_basis,
            origin_url=item.origin_url,
            text=item.text,
            url=item.url,
            language=item.language,
            artworks=await self.cards(item.artworks),  # type: ignore[arg-type]
            location=await self._location_summary(location) if location else None,  # type: ignore[arg-type]
            **visibility,
        )

    # Revisions and indexes.

    async def revisions(self, kind: Kind, record_id: RecordId) -> v.RevisionsView:
        state = await self.resolve(kind, record_id, merged_ok=True)
        history = await self._history(record_id)
        submitters = dict(
            (
                await self.connection.execute(
                    select(user_account.c.id, user_account.c.display_name).where(
                        user_account.c.id.in_(
                            {r.provenance.submitter_id for r in history.revisions}
                        )
                    )
                )
            ).all()
        )
        referenced: set[int] = set()
        revisions = []
        for revision in reversed(history.revisions):
            changes = []
            for index, change in enumerate(revision.changes):
                position = (revision.id, index)
                redacted_at = history.redacted.get(position)
                public = not self.viewer.moderator
                values = {name: change.get(name) for name in ("old", "new", "item")}
                if redacted_at and public:
                    values = {"old": None, "new": None, "item": None}
                old_redacted = position in history.old_hidden
                if old_redacted and public:
                    values["old"] = None
                referenced |= _references(change.get("field") or change.get("collection"), values)
                changes.append(
                    v.Change(
                        op=change["op"],
                        field=change.get("field"),
                        collection=change.get("collection"),
                        redacted=redacted_at is not None,
                        redacted_at=None if public else redacted_at,
                        old_redacted=old_redacted,
                        **values,
                    )
                )
            revisions.append(
                v.RevisionView(
                    id=revision.id,
                    submitter=submitters.get(revision.provenance.submitter_id),
                    submitted_at=revision.provenance.submitted_at,
                    approved_at=revision.provenance.approved_at,
                    changes=changes,
                )
            )
        await self._load_states([record_id])
        merged_into = None
        if state.merged_into is not None:
            try:
                await self.resolve(kind, record_id)
            except RecordMergedError as merged:
                [target] = await self.listed([merged.target]) or [None]
                merged_into = await self.link(target) if target else None
        record = v.RecordLink(
            kind=kind,
            id=record_id,
            path=await self._path(kind, record_id),
            name=await self._name(record_id),
        )
        return v.RevisionsView(
            record=record,
            merged_into=merged_into,
            withdrawn_at=state.withdrawn_at if self.viewer.moderator else None,
            revisions=revisions,
            records={str(link.id): link for link in await self.links(sorted(referenced))},
        )

    async def index(self, kind: Kind, page: int, name: str | None = None) -> v.IndexPage:
        """The listed records of a kind with an index, by name, alphabetically.

        With `name`, only those whose name (or, for an Artist, an Alias) matches it as in
        Search; a name hidden by a Redaction is never found.
        """
        table = _NAMED[kind]
        listed = (
            select(table.c.id)
            .join(t.record, t.record.c.id == table.c.id)
            .where(t.record.c.withdrawn_at.is_(None), t.record.c.merged_into.is_(None))
        )
        wanted = normalise_query(name)
        if wanted is not None:
            folded = func.lower(func.unaccent(literal(wanted)))

            def matches(column: Any) -> Any:
                return func.word_similarity(folded, func.lower(func.unaccent(column))) >= (
                    NAME_THRESHOLD
                )

            condition = matches(table.c.name)
            if kind is Kind.ARTIST:
                alias = t.artist_alias
                condition = or_(
                    condition,
                    exists().where(alias.c.artist_id == table.c.id, matches(alias.c.name)),
                )
            listed = listed.where(condition)
        ordered = listed.order_by(table.c.name.collate("und-x-icu"), table.c.id)
        if wanted is None:
            total = await self.connection.scalar(
                select(func.count()).select_from(listed.subquery())
            )
            ids = list(
                await self.connection.scalars(
                    ordered.limit(INDEX_PAGE_SIZE).offset((page - 1) * INDEX_PAGE_SIZE)
                )
            )
            # A redacted name still sorts by its stored value; the link shows the placeholder.
            items = await self.links(ids)
        else:
            found = await self.links(list(await self.connection.scalars(ordered)))
            found = [link for link in found if link.name is not None]
            total = len(found)
            items = found[(page - 1) * INDEX_PAGE_SIZE :][:INDEX_PAGE_SIZE]
        return v.IndexPage(items=items, page=page, page_size=INDEX_PAGE_SIZE, total=total or 0)


_REFERENCE_KEYS = frozenset(
    {
        "location",
        "site",
        "artist",
        "collective",
        "covering",
        "artworks",
        "series",
        "sources",
        "areas",
        "citations",
    }
)


def _references(name: Any, values: dict[str, Any]) -> set[int]:
    """The record ids a change refers to: the links of fields and items."""
    found: set[int] = set()

    def walk(value: Any, key: str | None) -> None:
        if isinstance(value, dict):
            for name, inner in value.items():
                walk(inner, name)
        elif isinstance(value, list):
            for inner in value:
                walk(inner, key)
        elif isinstance(value, int) and not isinstance(value, bool) and key in _REFERENCE_KEYS:
            found.add(value)

    for value in values.values():
        walk(value, name)
    return found
