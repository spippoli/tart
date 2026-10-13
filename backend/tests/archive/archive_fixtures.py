"""Builders of fictional archive records and a synchronous handle on a test archive.

Every name and text here is fictional and describes no real artwork or artist.
"""

import asyncio
import itertools
from collections.abc import Awaitable, Callable
from dataclasses import replace
from datetime import UTC, date, datetime
from typing import Any

from conftest import VALID_CONFIG

from tart.archive import (
    Artwork,
    Condition,
    DocumentationItem,
    Geometry,
    GeometryKind,
    HistoryEvent,
    HistoryEventType,
    Location,
    Medium,
    New,
    Operation,
    Precision,
    Provenance,
    Qualifier,
    Record,
    RecordId,
    Ref,
    Revision,
    RightsBasis,
    UncertainDate,
)
from tart.archive_persistence import PostgresArchiveStore, rules_from_instance, write_changeset
from tart.config import load_instance
from tart.db import create_engine

RULES = rules_from_instance(load_instance(VALID_CONFIG))
"""The test configuration's rules: its boundary is 12.40-12.56 E, 41.85-41.95 N."""

PROVENANCE = Provenance(
    submission_id=1,
    submitter_id=2,
    moderator_id=3,
    submitted_at=datetime(2026, 9, 1, 10, 0, tzinfo=UTC),
    approved_at=datetime(2026, 9, 3, 16, 30, tzinfo=UTC),
)

IN_ROME = (12.4823, 41.8955)
OBSERVED = UncertainDate(Precision.YEAR, Qualifier.EXACT, date(2024, 1, 1))


def point(longitude: float = IN_ROME[0], latitude: float = IN_ROME[1]) -> Geometry:
    return Geometry(GeometryKind.POINT, ((longitude, latitude),))


def square(west: float, south: float, east: float, north: float) -> Geometry:
    return Geometry(
        GeometryKind.POLYGON,
        ((west, south), (east, south), (east, north), (west, north), (west, south)),
    )


def location(**values: Any) -> Location:
    return Location(**{"geometry": point(), "surface_type": "building_wall", **values})


_event_keys = itertools.count(1)


def event(
    event_type: HistoryEventType = HistoryEventType.CONDITION_RECORDED, **values: Any
) -> HistoryEvent:
    """A new History event; a Condition record of `intact` unless told otherwise."""
    if event_type is HistoryEventType.CONDITION_RECORDED:
        values.setdefault("condition", Condition.INTACT)
    return HistoryEvent(
        **{
            "id": New(f"event-{next(_event_keys)}"),
            "type": event_type,
            "observed_date": OBSERVED,
            **values,
        }
    )


def artwork(location_ref: Ref, **values: Any) -> Artwork:
    """A new Artwork with the Condition record every new Artwork needs."""
    return Artwork(
        **{
            "location": location_ref,
            "expression_types": ("stencil",),
            "history_events": (event(),),
            **values,
        }
    )


def without_event_ids(record: Record | None) -> Record | None:
    """The record with its History events' ids blanked, to compare a stored record with
    what a builder made: the write operation gives each new event its id."""
    if not isinstance(record, Artwork):
        return record
    events = tuple(replace(event, id=0) for event in record.history_events)
    return replace(record, history_events=events)


def image(*artworks: Ref, **values: Any) -> DocumentationItem:
    return DocumentationItem(
        **{
            "medium": Medium.IMAGE,
            "observed_date": OBSERVED,
            "artworks": artworks,
            "file": "originals/fictional.jpg",
            "licence": "CC-BY-SA-4.0",
            "creator_credit": "Fictional photographer",
            "rights_basis": RightsBasis.OWN_WORK,
            "alt_text": "A fictional stencil of a cat on a grey plastered wall.",
            **values,
        }
    )


class Archive:
    """The archive in one test database, driven synchronously."""

    def __init__(self, url: str) -> None:
        self.url = url

    def _run[T](self, action: Callable[[Any], Awaitable[T]]) -> T:
        async def run() -> T:
            engine = create_engine(self.url)
            try:
                return await action(engine)
            finally:
                await engine.dispose()

        return asyncio.run(run())

    def write(
        self, *changeset: Operation, provenance: Provenance = PROVENANCE
    ) -> tuple[Revision, ...]:
        return self._run(lambda engine: write_changeset(engine, changeset, provenance, RULES))

    def read[T](self, query: Callable[[PostgresArchiveStore], Awaitable[T]]) -> T:
        async def action(engine: Any) -> T:
            async with engine.connect() as connection:
                return await query(PostgresArchiveStore(connection))

        return self._run(action)

    def get(self, record_id: RecordId) -> Record | None:
        return self.read(lambda store: store.get(record_id))

    def ids(self, revisions: tuple[Revision, ...]) -> list[RecordId]:
        return [revision.record_id for revision in revisions]
