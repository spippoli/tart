"""The PostgreSQL + PostGIS adapter of the archive's port, plus the archive's spatial queries.

It works on one `AsyncConnection` inside a transaction its caller owns.
"""

import json
from collections.abc import Iterable, Sequence
from typing import Any

from sqlalchemy import Table, delete, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncConnection

from tart.archive.codec import (
    Json,
    decode_period,
    decode_uncertain_date,
    encode_period,
    encode_uncertain_date,
)
from tart.archive.geometry import Geometry
from tart.archive.records import (
    Area,
    Artist,
    ArtistKind,
    Artwork,
    Attribution,
    Certainty,
    Condition,
    CrewMembership,
    DocumentationItem,
    HistoryEvent,
    HistoryEventType,
    Kind,
    Location,
    Medium,
    Record,
    RecordId,
    RightsBasis,
    Series,
    Site,
    Source,
)
from tart.archive.revisions import Provenance, Revision
from tart.archive_persistence import tables as t


def _geometry(value: str) -> Geometry:
    return Geometry.from_geojson(json.loads(value))


def _to_postgis(geometry: Geometry) -> Any:
    return func.ST_GeomFromGeoJSON(json.dumps(geometry.to_geojson()))


class PostgresArchiveStore:
    """`ArchiveStore` over PostgreSQL + PostGIS, and the read queries of the archive."""

    def __init__(self, connection: AsyncConnection) -> None:
        self.connection = connection

    # The port of the write operation.

    async def allocate_id(self, kind: Kind) -> RecordId:
        return await self._one(insert(t.record).values(kind=kind.value).returning(t.record.c.id))

    async def allocate_history_event_id(self) -> int:
        return await self._one(select(t.history_event_id.next_value()))

    async def get(self, record_id: RecordId) -> Record | None:
        kind = await self.connection.scalar(
            select(t.record.c.kind).where(t.record.c.id == record_id)
        )
        if kind is None:
            return None
        return await _READERS[Kind(kind)](self, record_id)

    async def save(self, record_id: RecordId, record: Record, *, new: bool) -> None:
        # The record row exists from `allocate_id`; `new` says whether the kind's row does.
        await _WRITERS[record.KIND](self, record_id, record, new)

    async def add_revision(
        self,
        record_id: RecordId,
        kind: Kind,
        provenance: Provenance,
        changes: tuple[dict[str, Json], ...],
    ) -> Revision:
        revision_id = await self._one(
            insert(t.revision)
            .values(
                record_id=record_id,
                submission_id=provenance.submission_id,
                submitter_id=provenance.submitter_id,
                moderator_id=provenance.moderator_id,
                submitted_at=provenance.submitted_at,
                approved_at=provenance.approved_at,
                changes=list(changes),
            )
            .returning(t.revision.c.id)
        )
        return Revision(revision_id, record_id, kind, provenance, changes)

    async def public_records(self, record_ids: Iterable[RecordId]) -> frozenset[RecordId]:
        # Every stored record is public until Withdrawal (Rights and legal actions) exists.
        result = await self.connection.scalars(
            select(t.record.c.id).where(t.record.c.id.in_(list(record_ids)))
        )
        return frozenset(result)

    async def members_of(self, collective_id: RecordId) -> frozenset[RecordId]:
        result = await self.connection.scalars(
            select(t.crew_membership.c.member_id).where(
                t.crew_membership.c.collective_id == collective_id
            )
        )
        return frozenset(result)

    async def artworks_signed_with(self, artist_id: RecordId, alias: str) -> frozenset[RecordId]:
        result = await self.connection.scalars(
            select(t.attribution.c.artwork_id).where(
                t.attribution.c.artist_id == artist_id, t.attribution.c.alias == alias
            )
        )
        return frozenset(result)

    async def documentation_items_of(self, artwork_ids: Iterable[RecordId]) -> frozenset[RecordId]:
        result = await self.connection.scalars(
            select(t.documentation_item_artwork.c.item_id).where(
                t.documentation_item_artwork.c.artwork_id.in_(list(artwork_ids))
            )
        )
        return frozenset(result)

    # Read queries.

    async def areas_of_location(self, location_id: RecordId) -> tuple[RecordId, ...]:
        """The Areas the Location falls within by geometry, by name.

        Membership is computed, never stored: a Location belongs to every Area its
        geometry touches, so a surface on the edge of two Areas is in both.
        """
        result = await self.connection.scalars(
            select(t.area.c.id)
            .join(t.location, func.ST_Intersects(t.area.c.geometry, t.location.c.geometry))
            .where(t.location.c.id == location_id)
            .order_by(t.area.c.name, t.area.c.id)
        )
        return tuple(result)

    async def artworks_on_location(self, location_id: RecordId) -> tuple[RecordId, ...]:
        """The Artworks whose Location is this one, by id."""
        result = await self.connection.scalars(
            select(t.artwork.c.id)
            .where(t.artwork.c.location_id == location_id)
            .order_by(t.artwork.c.id)
        )
        return tuple(result)

    async def revisions_of(self, record_id: RecordId) -> tuple[Revision, ...]:
        """The record's Revisions, oldest first."""
        kind = Kind(await self._one(select(t.record.c.kind).where(t.record.c.id == record_id)))
        rows = await self.connection.execute(
            select(t.revision).where(t.revision.c.record_id == record_id).order_by(t.revision.c.id)
        )
        return tuple(
            Revision(
                row.id,
                record_id,
                kind,
                Provenance(
                    row.submission_id,
                    row.submitter_id,
                    row.moderator_id,
                    row.submitted_at,
                    row.approved_at,
                ),
                tuple(row.changes),
            )
            for row in rows
        )

    # Helpers.

    async def _one(self, statement: Any) -> Any:
        return (await self.connection.execute(statement)).scalar_one()

    async def _row(self, table: Table, record_id: RecordId, *extra: Any) -> Any:
        result = await self.connection.execute(select(table, *extra).where(table.c.id == record_id))
        return result.one()

    async def _collection(
        self, table: Table, owner: str, owner_id: RecordId, *columns: str
    ) -> list[Any]:
        result = await self.connection.execute(
            select(*(table.c[column] for column in columns))
            .where(table.c[owner] == owner_id)
            .order_by(table.c.position)
        )
        return list(result)

    async def _links(self, table: Table, owner: str, owner_id: RecordId, column: str) -> tuple:
        return tuple(row[0] for row in await self._collection(table, owner, owner_id, column))

    async def _sources(self, record_id: RecordId) -> tuple[RecordId, ...]:
        return await self._links(t.record_source, "record_id", record_id, "source_id")

    async def _upsert(self, table: Table, record_id: RecordId, new: bool, **values: Any) -> None:
        if new:
            await self.connection.execute(insert(table).values(id=record_id, **values))
        else:
            await self.connection.execute(
                update(table).where(table.c.id == record_id).values(**values)
            )

    async def _replace(
        self, table: Table, owner: str, owner_id: RecordId, rows: Sequence[dict[str, Any]]
    ) -> None:
        """Replace the rows of one record's collection; links go, records stay."""
        await self.connection.execute(delete(table).where(table.c[owner] == owner_id))
        if rows:
            await self.connection.execute(
                insert(table),
                [{owner: owner_id, "position": index, **row} for index, row in enumerate(rows)],
            )

    async def _replace_sources(self, record_id: RecordId, sources: tuple) -> None:
        await self._replace(
            t.record_source, "record_id", record_id, [{"source_id": id_} for id_ in sources]
        )


# Readers and writers per record kind.


async def _read_artwork(store: PostgresArchiveStore, record_id: RecordId) -> Artwork:
    row = await store._row(t.artwork, record_id)
    attributions = []
    for attribution in await store._collection(
        t.attribution, "artwork_id", record_id, "artist_id", "certainty", "alias", "note"
    ):
        citations = await store.connection.scalars(
            select(t.attribution_citation.c.cited_id)
            .where(
                t.attribution_citation.c.artwork_id == record_id,
                t.attribution_citation.c.artist_id == attribution.artist_id,
            )
            .order_by(t.attribution_citation.c.position)
        )
        attributions.append(
            Attribution(
                attribution.artist_id,
                Certainty(attribution.certainty),
                attribution.alias,
                attribution.note,
                tuple(citations),
            )
        )
    return Artwork(
        location=row.location_id,
        expression_types=tuple(row.expression_types),
        title=row.title,
        description=row.description,
        attributions=tuple(attributions),
        history_events=await _read_history_events(store, record_id),
        series=await store._links(t.artwork_series, "artwork_id", record_id, "series_id"),
        sources=await store._sources(record_id),
    )


async def _write_artwork(
    store: PostgresArchiveStore, record_id: RecordId, record: Artwork, new: bool
) -> None:
    await store._upsert(
        t.artwork,
        record_id,
        new,
        location_id=record.location,
        expression_types=list(record.expression_types),
        title=record.title,
        description=record.description,
    )
    await store._replace(
        t.attribution,
        "artwork_id",
        record_id,
        [
            {
                "artist_id": attribution.artist,
                "certainty": attribution.certainty.value,
                "alias": attribution.alias,
                "note": attribution.note,
            }
            for attribution in record.attributions
        ],
    )
    citations = [
        {
            "artwork_id": record_id,
            "artist_id": attribution.artist,
            "cited_id": cited,
            "position": index,
        }
        for attribution in record.attributions
        for index, cited in enumerate(attribution.citations)
    ]
    if citations:  # the old ones went with their Attributions (ON DELETE CASCADE)
        await store.connection.execute(insert(t.attribution_citation), citations)
    await _write_history_events(store, record_id, record.history_events)
    await store._replace(
        t.artwork_series, "artwork_id", record_id, [{"series_id": id_} for id_ in record.series]
    )
    await store._replace_sources(record_id, record.sources)


async def _read_history_events(
    store: PostgresArchiveStore, artwork_id: RecordId
) -> tuple[HistoryEvent, ...]:
    events = await store._collection(
        t.history_event,
        "artwork_id",
        artwork_id,
        "id",
        "type",
        "observed_date",
        "condition",
        "note",
        "covering_artwork_id",
    )
    citations: dict[int, list[RecordId]] = {event.id: [] for event in events}
    rows = await store.connection.execute(
        select(t.history_event_citation.c.event_id, t.history_event_citation.c.cited_id)
        .where(t.history_event_citation.c.event_id.in_(list(citations)))
        .order_by(t.history_event_citation.c.position)
    )
    for event_id, cited_id in rows:
        citations[event_id].append(cited_id)
    return tuple(
        HistoryEvent(
            id=event.id,
            type=HistoryEventType(event.type),
            observed_date=decode_uncertain_date(event.observed_date),
            condition=Condition(event.condition) if event.condition else None,
            note=event.note,
            citations=tuple(citations[event.id]),
            covering=event.covering_artwork_id,
        )
        for event in events
    )


async def _write_history_events(
    store: PostgresArchiveStore, artwork_id: RecordId, events: tuple[HistoryEvent, ...]
) -> None:
    # The citations of the replaced events go with them (ON DELETE CASCADE).
    await store._replace(
        t.history_event,
        "artwork_id",
        artwork_id,
        [
            {
                "id": event.id,
                "type": event.type.value,
                "observed_date": encode_uncertain_date(event.observed_date),
                "condition": event.condition.value if event.condition else None,
                "note": event.note,
                "covering_artwork_id": event.covering,
            }
            for event in events
        ],
    )
    citations = [
        {"event_id": event.id, "cited_id": cited, "position": index}
        for event in events
        for index, cited in enumerate(event.citations)
    ]
    if citations:
        await store.connection.execute(insert(t.history_event_citation), citations)


async def _read_location(store: PostgresArchiveStore, record_id: RecordId) -> Location:
    row = await store._row(
        t.location, record_id, func.ST_AsGeoJSON(t.location.c.geometry).label("geojson")
    )
    return Location(
        geometry=_geometry(row.geojson),
        surface_type=row.surface_type,
        approximate=row.approximate,
        uncertainty_radius=row.uncertainty_radius,
        site=row.site_id,
        place_description=row.place_description,
    )


async def _write_location(
    store: PostgresArchiveStore, record_id: RecordId, record: Location, new: bool
) -> None:
    await store._upsert(
        t.location,
        record_id,
        new,
        geometry=_to_postgis(record.geometry),
        surface_type=record.surface_type,
        approximate=record.approximate,
        uncertainty_radius=record.uncertainty_radius,
        site_id=record.site,
        place_description=record.place_description,
    )


async def _read_site(store: PostgresArchiveStore, record_id: RecordId) -> Site:
    row = await store._row(t.site, record_id)
    return Site(row.name, row.description, await store._sources(record_id))


async def _write_site(
    store: PostgresArchiveStore, record_id: RecordId, record: Site, new: bool
) -> None:
    await store._upsert(t.site, record_id, new, name=record.name, description=record.description)
    await store._replace_sources(record_id, record.sources)


async def _read_area(store: PostgresArchiveStore, record_id: RecordId) -> Area:
    row = await store._row(t.area, record_id, func.ST_AsGeoJSON(t.area.c.geometry).label("geojson"))
    return Area(row.name, _geometry(row.geojson), row.description, await store._sources(record_id))


async def _write_area(
    store: PostgresArchiveStore, record_id: RecordId, record: Area, new: bool
) -> None:
    await store._upsert(
        t.area,
        record_id,
        new,
        name=record.name,
        description=record.description,
        geometry=_to_postgis(record.geometry),
    )
    await store._replace_sources(record_id, record.sources)


async def _read_series(store: PostgresArchiveStore, record_id: RecordId) -> Series:
    row = await store._row(t.series, record_id)
    return Series(row.name, row.description, await store._sources(record_id))


async def _write_series(
    store: PostgresArchiveStore, record_id: RecordId, record: Series, new: bool
) -> None:
    await store._upsert(t.series, record_id, new, name=record.name, description=record.description)
    await store._replace_sources(record_id, record.sources)


async def _read_artist(store: PostgresArchiveStore, record_id: RecordId) -> Artist:
    row = await store._row(t.artist, record_id)
    crews = await store._collection(
        t.crew_membership, "member_id", record_id, "collective_id", "period"
    )
    return Artist(
        name=row.name,
        kind=ArtistKind(row.kind),
        biography=row.biography,
        period=decode_period(row.period) if row.period else None,
        aliases=await store._links(t.artist_alias, "artist_id", record_id, "name"),
        areas=await store._links(t.artist_area, "artist_id", record_id, "area_id"),
        crew_memberships=tuple(
            CrewMembership(crew.collective_id, decode_period(crew.period) if crew.period else None)
            for crew in crews
        ),
        sources=await store._sources(record_id),
    )


async def _write_artist(
    store: PostgresArchiveStore, record_id: RecordId, record: Artist, new: bool
) -> None:
    await store._upsert(
        t.artist,
        record_id,
        new,
        name=record.name,
        kind=record.kind.value,
        biography=record.biography,
        period=encode_period(record.period) if record.period else None,
    )
    await store._replace(
        t.artist_alias, "artist_id", record_id, [{"name": alias} for alias in record.aliases]
    )
    await store._replace(
        t.artist_area, "artist_id", record_id, [{"area_id": area} for area in record.areas]
    )
    await store._replace(
        t.crew_membership,
        "member_id",
        record_id,
        [
            {
                "collective_id": crew.collective,
                "period": encode_period(crew.period) if crew.period else None,
            }
            for crew in record.crew_memberships
        ],
    )
    await store._replace_sources(record_id, record.sources)


async def _read_source(store: PostgresArchiveStore, record_id: RecordId) -> Source:
    row = await store._row(t.source, record_id)
    return Source(
        title=row.title,
        author=row.author,
        publication=row.publication,
        date=decode_uncertain_date(row.date) if row.date else None,
        url=row.url,
        note=row.note,
        language=row.language,
    )


async def _write_source(
    store: PostgresArchiveStore, record_id: RecordId, record: Source, new: bool
) -> None:
    await store._upsert(
        t.source,
        record_id,
        new,
        title=record.title,
        author=record.author,
        publication=record.publication,
        date=encode_uncertain_date(record.date) if record.date else None,
        url=record.url,
        note=record.note,
        language=record.language,
    )


async def _read_documentation_item(
    store: PostgresArchiveStore, record_id: RecordId
) -> DocumentationItem:
    row = await store._row(t.documentation_item, record_id)
    return DocumentationItem(
        medium=Medium(row.medium),
        observed_date=decode_uncertain_date(row.observed_date),
        artworks=await store._links(
            t.documentation_item_artwork, "item_id", record_id, "artwork_id"
        ),
        location=row.location_id,
        file=row.file,
        licence=row.licence,
        creator_credit=row.creator_credit,
        rights_basis=RightsBasis(row.rights_basis) if row.rights_basis else None,
        origin_url=row.origin_url,
        alt_text=row.alt_text,
        text=row.text,
        url=row.url,
        language=row.language,
    )


async def _write_documentation_item(
    store: PostgresArchiveStore, record_id: RecordId, record: DocumentationItem, new: bool
) -> None:
    await store._upsert(
        t.documentation_item,
        record_id,
        new,
        medium=record.medium.value,
        observed_date=encode_uncertain_date(record.observed_date),
        location_id=record.location,
        file=record.file,
        licence=record.licence,
        creator_credit=record.creator_credit,
        rights_basis=record.rights_basis.value if record.rights_basis else None,
        origin_url=record.origin_url,
        alt_text=record.alt_text,
        text=record.text,
        url=record.url,
        language=record.language,
    )
    await store._replace(
        t.documentation_item_artwork,
        "item_id",
        record_id,
        [{"artwork_id": artwork} for artwork in record.artworks],
    )


_READERS: dict[Kind, Any] = {
    Kind.ARTWORK: _read_artwork,
    Kind.LOCATION: _read_location,
    Kind.SITE: _read_site,
    Kind.AREA: _read_area,
    Kind.SERIES: _read_series,
    Kind.ARTIST: _read_artist,
    Kind.SOURCE: _read_source,
    Kind.DOCUMENTATION_ITEM: _read_documentation_item,
}
_WRITERS: dict[Kind, Any] = {
    Kind.ARTWORK: _write_artwork,
    Kind.LOCATION: _write_location,
    Kind.SITE: _write_site,
    Kind.AREA: _write_area,
    Kind.SERIES: _write_series,
    Kind.ARTIST: _write_artist,
    Kind.SOURCE: _write_source,
    Kind.DOCUMENTATION_ITEM: _write_documentation_item,
}
