"""Upkeep of the Discovery index: rebuild an Artwork's row from the public archive.

    await refresh(connection, artwork_ids, rules)

Every write to the public archive settles the Artworks it affects through here (see
`PostgresArchiveStore.settle`), and so must any later change of what the public sees,
such as a Withdrawal or a Redaction. The facts come from the archive's read side, so
the index applies the same rules the record pages do, once.
"""

import asyncio
from collections.abc import Iterable

from sqlalchemy import bindparam, cast, delete, func, insert, select
from sqlalchemy.dialects.postgresql import REGCONFIG, Range
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from tart.archive import DateRange, InstanceRules, RecordId
from tart.archive_persistence import tables as archive
from tart.archive_read import ArtworkFacts, Reader, Viewer
from tart.discovery import tables as t
from tart.discovery.language import text_search_configuration

# How much a match on each kind of name counts (Search, Matching and relevance). Platform
# constants, tuned against the ranking test, not Instance configuration.
TITLE_WEIGHT = 1.0
ARTIST_WEIGHT = 0.9
SERIES_WEIGHT = 0.8
SITE_WEIGHT = 0.7
AREA_WEIGHT = 0.6


def date_range(value: DateRange) -> Range:
    """The range as PostgreSQL holds it, both ends inclusive, `None` unbounded."""
    return Range(value.earliest, value.latest, bounds="[]")


def _names(facts: ArtworkFacts) -> list[tuple[str, float]]:
    return [
        *([(facts.artwork.title, TITLE_WEIGHT)] if facts.artwork.title else []),
        *[(name, ARTIST_WEIGHT) for name in facts.artists],
        *[(name, SERIES_WEIGHT) for name in facts.series],
        *([(facts.site, SITE_WEIGHT)] if facts.site else []),
        *[(name, AREA_WEIGHT) for name in facts.areas],
    ]


async def refresh(
    connection: AsyncConnection, artwork_ids: Iterable[RecordId], rules: InstanceRules
) -> None:
    """Rebuild the rows of these Artworks, dropping those of records that are not Artworks."""
    ids = sorted(set(artwork_ids))
    if not ids:
        return
    for table in (t.discovery_artwork, t.discovery_documented, t.discovery_name):
        await connection.execute(delete(table).where(table.c.artwork_id.in_(ids)))
    artworks = sorted(
        await connection.scalars(select(archive.artwork.c.id).where(archive.artwork.c.id.in_(ids)))
    )
    configuration = cast(text_search_configuration(rules.content_language), REGCONFIG)
    reader = Reader(connection, Viewer())
    for artwork_id in artworks:
        facts = await reader.facts(artwork_id, rules.time_zone)
        description = facts.artwork.description
        await connection.execute(
            insert(t.discovery_artwork).values(
                artwork_id=artwork_id,
                condition=facts.condition.condition.value,
                condition_group=facts.condition.group.value,
                created_during=date_range(facts.creation) if facts.creation else None,
                first_documented=facts.first_documented,
                last_documented=facts.last_documented,
                added_at=facts.added_at,
                attribution=list(facts.attribution),
                title=facts.artwork.title,
                # Unaccented like the query, so that a stem matches however it is written.
                description=(
                    func.to_tsvector(configuration, func.unaccent(description))
                    if description
                    else None
                ),
            )
        )
        if facts.documented:
            await connection.execute(
                insert(t.discovery_documented),
                [
                    {"artwork_id": artwork_id, "during": date_range(during)}
                    for during in facts.documented
                ],
            )
        if names := _names(facts):
            await connection.execute(
                insert(t.discovery_name).values(
                    artwork_id=bindparam("artwork_id"),
                    name=func.lower(func.unaccent(bindparam("name"))),
                    weight=bindparam("weight"),
                ),
                [
                    {"artwork_id": artwork_id, "name": name, "weight": weight}
                    for name, weight in names
                ],
            )


async def rebuild(
    engine: AsyncEngine, rules: InstanceRules, *, chunk: int = 250, workers: int = 8
) -> None:
    """Rebuild the whole index, in chunks over several connections: after a bulk load, or
    to bring it up to date with a changed Content language."""
    async with engine.connect() as connection:
        ids = list(
            await connection.scalars(select(archive.artwork.c.id).order_by(archive.artwork.c.id))
        )
    gate = asyncio.Semaphore(workers)

    async def one(artworks: list[RecordId]) -> None:
        async with gate, engine.begin() as connection:
            await refresh(connection, artworks, rules)

    await asyncio.gather(*(one(ids[start : start + chunk]) for start in range(0, len(ids), chunk)))
