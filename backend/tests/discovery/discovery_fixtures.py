"""A small fictional archive to search and filter, and the API over it.

Every name, title, and text here is fictional and describes no real artwork or artist.
"""

import asyncio
import json
from collections.abc import Iterator
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime
from typing import Any

import asyncpg
import pytest
from archive_fixtures import (
    OBSERVED,
    PROVENANCE,
    RULES,
    Archive,
    event,
    image,
    location,
    point,
    square,
)
from auth_fixtures import Api, open_api

from tart.archive import (
    Area,
    Artist,
    ArtistKind,
    Artwork,
    Attribution,
    Certainty,
    Condition,
    Create,
    HistoryEventType,
    New,
    Precision,
    Qualifier,
    RecordId,
    Series,
    Site,
    UncertainDate,
)
from tart.archive_persistence import PostgresArchiveStore

WITHDRAWN_AT = datetime(2026, 5, 4, 9, 0, tzinfo=UTC)


def year(value: int, qualifier: Qualifier = Qualifier.EXACT) -> UncertainDate:
    return UncertainDate(Precision.YEAR, qualifier, date(value, 1, 1))


def provenance(approved: datetime | None = None, submitted: datetime | None = None):
    return replace(
        PROVENANCE,
        approved_at=approved or PROVENANCE.approved_at,
        submitted_at=submitted or PROVENANCE.submitted_at,
    )


@dataclass
class World:
    """Records of a fictional archive, written through the archive's write operation."""

    archive: Archive

    def site(self, name: str) -> RecordId:
        return self.archive.ids(self.archive.write(Create(New("s"), Site(name=name))))[0]

    def area(self, name: str, west: float, south: float, east: float, north: float) -> RecordId:
        shape = square(west, south, east, north)
        return self.archive.ids(
            self.archive.write(Create(New("a"), Area(name=name, geometry=shape)))
        )[0]

    def series(self, name: str) -> RecordId:
        return self.archive.ids(self.archive.write(Create(New("s"), Series(name=name))))[0]

    def artist(self, name: str, *aliases: str) -> RecordId:
        artist = Artist(name=name, kind=ArtistKind.INDIVIDUAL, aliases=aliases)
        return self.archive.ids(self.archive.write(Create(New("a"), artist)))[0]

    def place(
        self, longitude: float = 12.4823, latitude: float = 41.8955, **values: Any
    ) -> RecordId:
        record = location(geometry=point(longitude, latitude), **values)
        return self.archive.ids(self.archive.write(Create(New("l"), record)))[0]

    def artwork(
        self,
        title: str | None = None,
        *,
        at: RecordId | None = None,
        condition: Condition = Condition.INTACT,
        condition_date: UncertainDate = OBSERVED,
        created: UncertainDate | None = None,
        documented: tuple[UncertainDate, ...] = (OBSERVED,),
        artists: tuple[RecordId, ...] = (),
        certainty: Certainty = Certainty.PROBABLE,
        series: tuple[RecordId, ...] = (),
        approved: datetime | None = None,
        **values: Any,
    ) -> RecordId:
        """A new Artwork, on a new Location unless `at`, with an image for each date."""
        where: Any = at if at is not None else New("l")
        events = [event(condition=condition, observed_date=condition_date)]
        if created is not None:
            events.append(event(HistoryEventType.CREATED, observed_date=created))
        attributions = tuple(Attribution(artist, certainty) for artist in artists)
        changeset: list[Any] = []
        if at is None:
            changeset.append(Create(New("l"), location()))
        changeset.append(
            Create(
                New("w"),
                Artwork(
                    **{
                        "location": where,
                        "expression_types": ("stencil",),
                        "title": title,
                        "history_events": tuple(events),
                        "attributions": attributions,
                        "series": series,
                        **values,
                    }
                ),
            )
        )
        for number, observed in enumerate(documented):
            changeset.append(Create(New(f"d{number}"), image(New("w"), observed_date=observed)))
        revisions = self.archive.write(*changeset, provenance=provenance(approved))
        return next(r.record_id for r in revisions if r.kind.value == "artwork")

    def withdraw(self, record_id: RecordId) -> None:
        self.query("UPDATE record SET withdrawn_at = now() WHERE id = $1", record_id)

    def merge(self, duplicate: RecordId, survivor: RecordId) -> None:
        self.query("UPDATE record SET merged_into = $1 WHERE id = $2", survivor, duplicate)

    def redact(self, record_id: RecordId, field: str) -> None:
        """Redact every operation of the record's Revisions that sets the field."""
        for revision in self.query(
            "SELECT id, changes FROM revision WHERE record_id = $1", record_id
        ):
            for index, change in enumerate(json.loads(revision["changes"])):
                if change.get("field") == field:
                    self.query(
                        "INSERT INTO redaction (revision_id, operation, redacted_at) "
                        "VALUES ($1, $2, $3)",
                        revision["id"],
                        index,
                        WITHDRAWN_AT,
                    )

    def query(self, sql: str, *args: object) -> list[asyncpg.Record]:
        async def run() -> list[asyncpg.Record]:
            connection = await asyncpg.connect(self.archive.url.replace("+asyncpg", ""))
            try:
                return await connection.fetch(sql, *args)
            finally:
                await connection.close()

        return asyncio.run(run())

    def settle(self, *record_ids: RecordId) -> None:
        """What Withdrawal and Redaction do after changing what the public sees."""

        async def settle(store: PostgresArchiveStore) -> None:
            await store.settle(record_ids, RULES)

        async def run(engine: Any) -> None:
            async with engine.begin() as connection:
                await settle(PostgresArchiveStore(connection))

        self.archive._run(run)


@pytest.fixture
def world(migrated_database: str) -> World:
    return World(Archive(migrated_database))


@dataclass
class Discovery:
    api: Api

    def artworks(self, **params: Any) -> dict[str, Any]:
        response = self.api.client.get("/api/discovery/artworks", params=params)
        assert response.status_code == 200, response.text
        return response.json()

    def titles(self, **params: Any) -> list[str | None]:
        return [entry["title"] for entry in self.artworks(**params)["entries"]]

    def ids(self, **params: Any) -> list[int]:
        return [entry["id"] for entry in self.artworks(**params)["entries"]]

    def locations(self, **params: Any) -> dict[str, Any]:
        response = self.api.client.get("/api/discovery/locations", params=params)
        assert response.status_code == 200, response.text
        return response.json()


@pytest.fixture
def discovery(world: World, migrated_database: str) -> Iterator[Discovery]:
    """The API over the archive. Written to before the first request, as the app reads it."""
    with open_api(migrated_database) as api:
        yield Discovery(api)
