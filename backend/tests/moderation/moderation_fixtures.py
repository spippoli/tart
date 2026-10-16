"""Builders and a database handle for the moderation tests. Every record is fictional."""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

import pytest
from archive_fixtures import RULES as ARCHIVE_RULES
from archive_fixtures import artwork, image, location
from sqlalchemy.ext.asyncio import AsyncConnection

from tart.archive import Condition, Create, Kind, New, Operation, Provenance
from tart.archive.codec import Json
from tart.archive.write import apply_changeset
from tart.archive_persistence import PostgresArchiveStore
from tart.auth import operator
from tart.db import create_engine
from tart.moderation import Content, Decision, DecisionRules, encode_content
from tart.moderation_persistence import service, store

NOW = datetime(2026, 9, 1, 10, 0, tzinfo=UTC)
RULES = DecisionRules(self_approval=False, reasons=frozenset({"incomplete", "duplicate"}))
REASON = Decision("incomplete", "The second photo does not show the stencil.")

LOCATION, ARTWORK, IMAGE = New("location"), New("artwork"), New("image")


def run[T](database: str, work: Callable[[AsyncConnection], Awaitable[T]]) -> T:
    """`work` in a transaction of its own, committed when it returns."""

    async def go() -> T:
        engine = create_engine(database)
        try:
            async with engine.begin() as connection:
                return await work(connection)
        finally:
            await engine.dispose()

    return asyncio.run(go())


def refusal(database: str, work: Callable[[AsyncConnection], Awaitable[object]]) -> str:
    """The stable code of the refusal `work` ends in."""
    with pytest.raises(ValueError) as error:
        run(database, work)
    return error.value.code  # type: ignore[attr-defined, no-any-return]


async def user(connection: AsyncConnection, name: str, *, moderator: bool = False) -> int:
    created = await operator.create(connection, f"{name}@example.org", name.title(), "it", NOW)
    if moderator:
        await operator.grant_moderator(connection, created)
    return created.id


def new_artwork_operations(**values: Any) -> tuple[Operation, ...]:
    """A new Artwork on a new Location with one image; its Condition comes from the content."""
    return (
        Create(LOCATION, location()),
        Create(ARTWORK, artwork(LOCATION, **{"history_events": (), **values})),
        Create(IMAGE, image(ARTWORK)),
    )


def snapshot(*operations: Operation, condition: Condition | None = None) -> Json:
    return encode_content(Content(operations, condition))


def new_artwork_snapshot(**values: Any) -> Json:
    return snapshot(*new_artwork_operations(**values), condition=Condition.INTACT)


async def submitted(
    connection: AsyncConnection,
    submitter: int,
    content: Json | None = None,
    *,
    kind: Kind = Kind.ARTWORK,
    target_id: int | None = None,
    base_revisions: tuple[int, ...] = (),
    at: datetime = NOW,
) -> int:
    """A Submission in `submitted`; by default a valid new Artwork."""
    draft = await store.create_draft(
        connection, submitter, kind, at, target_id=target_id, base_revisions=base_revisions
    )
    await service.submit(
        connection,
        draft.id,
        submitter,
        new_artwork_snapshot() if content is None else content,
        at,
        ARCHIVE_RULES,
        note="Hello",
    )
    return draft.id


async def write(connection: AsyncConnection, *changeset: Operation) -> list[int]:
    """Create or change records straight through the write operation, as the archive's
    own tests do; returns the ids of the records the revisions touched."""
    provenance = Provenance(1, 1, 1, NOW, NOW)
    revisions = await apply_changeset(
        PostgresArchiveStore(connection), changeset, provenance, ARCHIVE_RULES
    )
    return [revision.record_id for revision in revisions]
