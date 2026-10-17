"""What a Merge, a Duplicate retirement, or an Unmerge reads from the archive: the plan an
editor starts from and the records the Merge rewrites (ADR 0018).

    plan = await merge_plan(connection, source_id, into_id)
    references = await references_of(connection, source_id)
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncConnection

from tart.archive.records import (
    Area,
    Artist,
    Artwork,
    DocumentationItem,
    Kind,
    Location,
    RecordId,
    Series,
    Site,
    Source,
)
from tart.archive_persistence import PostgresArchiveStore
from tart.archive_persistence import tables as t
from tart.moderation import ModerationError
from tart.moderation.duplicates import name_candidates
from tart.moderation.merge import (
    Plan,
    Referrer,
    UnmergePlan,
    merge_submission,
    plan_merge,
    plan_unmerge,
)
from tart.moderation_persistence.duplicates import PostgresDuplicateQuery


@dataclass(frozen=True)
class Reference:
    """A record that referenced the folded one: it is rewritten, with a Revision of its own."""

    id: RecordId
    kind: Kind


async def merge_plan(connection: AsyncConnection, source_id: RecordId, into_id: RecordId) -> Plan:
    """The default Merge of one record into another of the same kind."""
    store = PostgresArchiveStore(connection)
    source, into = await store.get(source_id), await store.get(into_id)
    if source is None or into is None or source_id == into_id:
        raise ModerationError("moderation.unknown_target")
    return plan_merge(source_id, source, into_id, into)


async def unmerge_plan(
    connection: AsyncConnection, source_id: RecordId
) -> tuple[RecordId, UnmergePlan]:
    """The survivor of a merged record, and the default Unmerge from the Revisions of the
    Merge that folded it."""
    store = PostgresArchiveStore(connection)
    into_id = await store.redirect_of(source_id)
    if into_id is None:
        raise ModerationError("moderation.not_merged")
    into = await store.get(into_id)
    assert into is not None
    revisions = await store.revisions_of(into_id)
    submission = merge_submission(revisions, source_id)
    if submission is None:
        raise ModerationError("moderation.not_merged")
    touched = await connection.scalars(
        select(t.revision.c.record_id)
        .where(
            t.revision.c.submission_id == submission,
            t.revision.c.record_id.not_in([source_id, into_id]),
        )
        .distinct()
    )
    referrers = []
    for record_id, history in (await store.revisions_of_many(list(touched))).items():
        record = await store.get(record_id)
        assert record is not None
        referrers.append(
            Referrer(
                record_id,
                record,
                [r for r in history if r.provenance.submission_id == submission],
            )
        )
    return into_id, plan_unmerge(source_id, into_id, into, revisions, referrers)


async def references_of(connection: AsyncConnection, source_id: RecordId) -> list[Reference]:
    """The records that reference the record now, by id: those a Merge of it would rewrite."""
    store = PostgresArchiveStore(connection)
    ids = sorted(await store.referrers_of(source_id))
    if not ids:
        return []
    rows = await connection.execute(
        select(t.record.c.id, t.record.c.kind).where(t.record.c.id.in_(ids)).order_by(t.record.c.id)
    )
    return [Reference(row.id, Kind(row.kind)) for row in rows]


async def candidates(connection: AsyncConnection, source_id: RecordId) -> list[RecordId]:
    """The public records that may be the survivor of a Merge of this one, likeliest first:
    for a Location the Locations within the proximity rule, for an Artwork those on them, for
    a record with a name the records whose name or Alias is alike, for a Documentation item the
    other items of its Artworks (contribution-and-moderation spec, Merge editor, step 1)."""
    store = PostgresArchiveStore(connection)
    record = await store.get(source_id)
    if record is None:
        raise ModerationError("moderation.unknown_target")
    query = PostgresDuplicateQuery(connection)
    found: list[RecordId] = []
    match record:
        case Location():
            found = [
                near.id
                for near in await query.locations_near(record.geometry, record.uncertainty_radius)
            ]
        case Artwork():
            home = await store.get(record.location)  # type: ignore[arg-type]
            assert isinstance(home, Location)
            for near in await query.locations_near(home.geometry, home.uncertainty_radius):
                found += await store.artworks_on_location(near.id)
        case Artist() | Site() | Series() | Area() | Source():
            name = record.title if isinstance(record, Source) else record.name
            url = record.url if isinstance(record, Source) else None
            alike = name_candidates(name, await query.named_records(record.KIND), url=url)
            found = [candidate.record.id for candidate in alike]
        case DocumentationItem():
            found = sorted(await store.documentation_items_of(record.artworks))  # type: ignore[arg-type]
    unique = [each for each in dict.fromkeys(found) if each != source_id]
    if not unique:
        return []
    listed = await connection.scalars(
        select(t.record.c.id).where(
            t.record.c.id.in_(unique),
            t.record.c.withdrawn_at.is_(None),
            t.record.c.merged_into.is_(None),
        )
    )
    public = set(listed)
    return [each for each in unique if each in public]
