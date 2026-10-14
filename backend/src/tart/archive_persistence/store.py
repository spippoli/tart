"""The PostgreSQL + PostGIS adapter of the archive's port, plus the archive's spatial queries.

It works on one `AsyncConnection` inside a transaction its caller owns.
"""

import json
from collections.abc import Iterable, Sequence
from typing import Any

from sqlalchemy import Table, delete, func, insert, select, union, update
from sqlalchemy.exc import NoResultFound
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
from tart.archive.rules import InstanceRules
from tart.archive_persistence import tables as t
from tart.discovery.tables import archive_change


def _geometry(value: str) -> Geometry:
    return Geometry.from_geojson(json.loads(value))


def _to_postgis(geometry: Geometry) -> Any:
    return func.ST_GeomFromGeoJSON(json.dumps(geometry.to_geojson()))


class PostgresArchiveStore:
    """`ArchiveStore` over PostgreSQL + PostGIS, and the read queries of the archive."""

    def __init__(self, connection: AsyncConnection, *, index: bool = True) -> None:
        self.connection = connection
        self._watched: set[RecordId] = set()
        # A bulk writer (the fictional dataset) leaves the Discovery index to one rebuild
        # of its own after many changesets, instead of refreshing it after each.
        self._index = index

    # The port of the write operation.

    async def allocate_id(self, kind: Kind) -> RecordId:
        return await self._one(insert(t.record).values(kind=kind.value).returning(t.record.c.id))

    async def allocate_history_event_id(self) -> int:
        return await self._one(select(t.history_event_id.next_value()))

    async def get(self, record_id: RecordId, kind: Kind | None = None) -> Record | None:
        """The record; a caller that already knows its kind spares the lookup."""
        if kind is None:
            stored = await self.connection.scalar(
                select(t.record.c.kind).where(t.record.c.id == record_id)
            )
            if stored is None:
                return None
            kind = Kind(stored)
        return await _READERS[kind](self, record_id)

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
        result = await self.connection.scalars(
            select(t.record.c.id).where(
                t.record.c.id.in_(list(record_ids)), t.record.c.withdrawn_at.is_(None)
            )
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

    async def documentation_items_by_artwork(
        self, artwork_ids: Iterable[RecordId]
    ) -> dict[RecordId, frozenset[RecordId]]:
        """`documentation_items_of` for several Artworks at once, by Artwork."""
        link = t.documentation_item_artwork
        rows = await self.connection.execute(
            select(link.c.artwork_id, link.c.item_id).where(
                link.c.artwork_id.in_(list(artwork_ids))
            )
        )
        found: dict[RecordId, set[RecordId]] = {}
        for row in rows:
            found.setdefault(row.artwork_id, set()).add(row.item_id)
        return {artwork_id: frozenset(items) for artwork_id, items in found.items()}

    async def watch(self, record_ids: Iterable[RecordId]) -> None:
        self._watched |= await self._artworks_affected_by(record_ids)

    async def settle(self, record_ids: Iterable[RecordId], rules: InstanceRules) -> None:
        ids = list(record_ids)
        if self._index:
            # One settling at a time: two writers refreshing the same Artwork would both
            # delete its index rows and insert them again. The second waits for the first
            # to commit, and then reads what it committed.
            await self.connection.execute(
                select(archive_change.c.counter).where(archive_change.c.id == 1).with_for_update()
            )
        affected = self._watched | await self._artworks_affected_by(ids)
        self._watched = set()
        if self._index:
            # Discovery reads through this store's own read side, so it is imported on use.
            from tart.discovery.index import refresh

            await refresh(self.connection, affected, rules)
        if ids:
            await self.connection.execute(
                update(archive_change)
                .where(archive_change.c.id == 1)
                .values(counter=archive_change.c.counter + 1)
            )

    async def _artworks_affected_by(self, record_ids: Iterable[RecordId]) -> set[RecordId]:
        """The Artworks whose search names or Area membership change with these records:
        themselves, those on a Location or Site, in a Series or an Area, by an Artist, or
        documented by an item."""
        ids = list(set(record_ids))
        if not ids:
            return set()
        artwork, location = t.artwork, t.location
        sites = select(location.c.id).where(location.c.site_id.in_(ids))
        areas = (
            select(location.c.id)
            .join(t.area, func.ST_Intersects(t.area.c.geometry, location.c.geometry))
            .where(t.area.c.id.in_(ids))
        )
        found = union(
            select(artwork.c.id).where(artwork.c.id.in_(ids)),
            select(artwork.c.id).where(artwork.c.location_id.in_(ids)),
            select(artwork.c.id).where(artwork.c.location_id.in_(sites)),
            select(artwork.c.id).where(artwork.c.location_id.in_(areas)),
            select(t.artwork_series.c.artwork_id).where(t.artwork_series.c.series_id.in_(ids)),
            select(t.attribution.c.artwork_id).where(t.attribution.c.artist_id.in_(ids)),
            select(t.documentation_item_artwork.c.artwork_id).where(
                t.documentation_item_artwork.c.item_id.in_(ids)
            ),
        )
        return set(await self.connection.scalars(found))

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

    async def areas_of_locations(
        self, location_ids: Iterable[RecordId]
    ) -> dict[RecordId, tuple[RecordId, ...]]:
        """`areas_of_location` for several Locations at once, by Location."""
        rows = await self.connection.execute(
            select(t.location.c.id.label("location_id"), t.area.c.id.label("area_id"))
            .join(t.area, func.ST_Intersects(t.area.c.geometry, t.location.c.geometry))
            .where(t.location.c.id.in_(list(location_ids)))
            .order_by(t.area.c.name, t.area.c.id)
        )
        found: dict[RecordId, list[RecordId]] = {}
        for row in rows:
            found.setdefault(row.location_id, []).append(row.area_id)
        return {location_id: tuple(areas) for location_id, areas in found.items()}

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
        return (await self.revisions_of_many([record_id]))[record_id]

    async def revisions_of_many(
        self, record_ids: Iterable[RecordId]
    ) -> dict[RecordId, tuple[Revision, ...]]:
        """The Revisions of each record, oldest first, in two queries."""
        ids = list(set(record_ids))
        kinds = {
            row.id: Kind(row.kind)
            for row in await self.connection.execute(
                select(t.record.c.id, t.record.c.kind).where(t.record.c.id.in_(ids))
            )
        }
        found: dict[RecordId, list[Revision]] = {record_id: [] for record_id in ids}
        rows = await self.connection.execute(
            select(t.revision).where(t.revision.c.record_id.in_(ids)).order_by(t.revision.c.id)
        )
        for row in rows:
            found[row.record_id].append(
                Revision(
                    row.id,
                    row.record_id,
                    kinds[row.record_id],
                    Provenance(
                        row.submission_id,
                        row.submitter_id,
                        row.moderator_id,
                        row.submitted_at,
                        row.approved_at,
                    ),
                    tuple(row.changes),
                )
            )
        for record_id in ids:
            if record_id not in kinds:
                raise NoResultFound
        return {record_id: tuple(revisions) for record_id, revisions in found.items()}

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

    async def _collections(
        self, table: Table, owner: str, owner_ids: Sequence[RecordId], *columns: str
    ) -> dict[RecordId, list[Any]]:
        """`_collection` for several owners at once, by owner."""
        result = await self.connection.execute(
            select(table.c[owner].label("owner"), *(table.c[column] for column in columns))
            .where(table.c[owner].in_(list(owner_ids)))
            .order_by(table.c.position)
        )
        found: dict[RecordId, list[Any]] = {owner_id: [] for owner_id in owner_ids}
        for row in result:
            found[row.owner].append(row)
        return found

    async def get_many(self, kinds: dict[RecordId, Kind]) -> dict[RecordId, Record]:
        """The records of known kinds: Artworks, Locations, and Documentation items in a few
        queries for all of them, the others one by one."""
        found: dict[RecordId, Record] = {}
        for kind, batch in _BATCH_READERS.items():
            ids = [id_ for id_, k in kinds.items() if k is kind]
            if ids:
                found.update(await batch(self, ids))
        for id_, kind in kinds.items():
            if id_ not in found:
                found[id_] = await _READERS[kind](self, id_)
        return found

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


async def _read_artworks(
    store: PostgresArchiveStore, ids: Sequence[RecordId]
) -> dict[RecordId, Artwork]:
    rows = {
        row.id: row
        for row in await store.connection.execute(select(t.artwork).where(t.artwork.c.id.in_(ids)))
    }
    attributions = await store._collections(
        t.attribution, "artwork_id", ids, "artist_id", "certainty", "alias", "note"
    )
    cited: dict[tuple[RecordId, RecordId], list[RecordId]] = {}
    cite = t.attribution_citation
    for row in await store.connection.execute(
        select(cite.c.artwork_id, cite.c.artist_id, cite.c.cited_id)
        .where(cite.c.artwork_id.in_(ids))
        .order_by(cite.c.position)
    ):
        cited.setdefault((row.artwork_id, row.artist_id), []).append(row.cited_id)
    events = await _read_history_events(store, ids)
    series = await store._collections(t.artwork_series, "artwork_id", ids, "series_id")
    sources = await store._collections(t.record_source, "record_id", ids, "source_id")
    return {
        id_: Artwork(
            location=rows[id_].location_id,
            expression_types=tuple(rows[id_].expression_types),
            title=rows[id_].title,
            description=rows[id_].description,
            attributions=tuple(
                Attribution(
                    attribution.artist_id,
                    Certainty(attribution.certainty),
                    attribution.alias,
                    attribution.note,
                    tuple(cited.get((id_, attribution.artist_id), ())),
                )
                for attribution in attributions[id_]
            ),
            history_events=events[id_],
            series=tuple(row.series_id for row in series[id_]),
            sources=tuple(row.source_id for row in sources[id_]),
        )
        for id_ in ids
    }


async def _read_artwork(store: PostgresArchiveStore, record_id: RecordId) -> Artwork:
    return (await _read_artworks(store, [record_id]))[record_id]


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
    store: PostgresArchiveStore, artwork_ids: Sequence[RecordId]
) -> dict[RecordId, tuple[HistoryEvent, ...]]:
    owned = await store._collections(
        t.history_event,
        "artwork_id",
        artwork_ids,
        "id",
        "type",
        "observed_date",
        "condition",
        "note",
        "covering_artwork_id",
    )
    citations: dict[int, list[RecordId]] = {
        event.id: [] for events in owned.values() for event in events
    }
    rows = await store.connection.execute(
        select(t.history_event_citation.c.event_id, t.history_event_citation.c.cited_id)
        .where(t.history_event_citation.c.event_id.in_(list(citations)))
        .order_by(t.history_event_citation.c.position)
    )
    for event_id, cited_id in rows:
        citations[event_id].append(cited_id)
    return {
        artwork_id: tuple(
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
        for artwork_id, events in owned.items()
    }


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


async def _read_locations(
    store: PostgresArchiveStore, ids: Sequence[RecordId]
) -> dict[RecordId, Location]:
    result = await store.connection.execute(
        select(t.location, func.ST_AsGeoJSON(t.location.c.geometry).label("geojson")).where(
            t.location.c.id.in_(ids)
        )
    )
    return {
        row.id: Location(
            geometry=_geometry(row.geojson),
            surface_type=row.surface_type,
            approximate=row.approximate,
            uncertainty_radius=row.uncertainty_radius,
            site=row.site_id,
            place_description=row.place_description,
        )
        for row in result
    }


async def _read_location(store: PostgresArchiveStore, record_id: RecordId) -> Location:
    return (await _read_locations(store, [record_id]))[record_id]


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


async def _read_documentation_items(
    store: PostgresArchiveStore, ids: Sequence[RecordId]
) -> dict[RecordId, DocumentationItem]:
    rows = await store.connection.execute(
        select(t.documentation_item).where(t.documentation_item.c.id.in_(ids))
    )
    artworks = await store._collections(t.documentation_item_artwork, "item_id", ids, "artwork_id")
    return {
        row.id: DocumentationItem(
            medium=Medium(row.medium),
            observed_date=decode_uncertain_date(row.observed_date),
            artworks=tuple(link.artwork_id for link in artworks[row.id]),
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
        for row in rows
    }


async def _read_documentation_item(
    store: PostgresArchiveStore, record_id: RecordId
) -> DocumentationItem:
    return (await _read_documentation_items(store, [record_id]))[record_id]


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
_BATCH_READERS: dict[Kind, Any] = {
    Kind.ARTWORK: _read_artworks,
    Kind.LOCATION: _read_locations,
    Kind.DOCUMENTATION_ITEM: _read_documentation_items,
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
