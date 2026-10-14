"""Writes that settle at the same time do not collide on the Discovery index. Every record is
fictional."""

# ruff: noqa: F401, F811
# The fixtures are imported for pytest and named again as parameters.
import asyncio

from archive_fixtures import RULES
from discovery_fixtures import Discovery, World, discovery, world
from sqlalchemy.ext.asyncio import create_async_engine

from tart.archive_persistence import PostgresArchiveStore


def test_settling_at_the_same_time_does_not_collide_on_the_index(
    world: World, discovery: Discovery
) -> None:
    artwork = world.artwork("Gatto sul muro")

    async def settle_together() -> None:
        engine = create_async_engine(world.archive.url)

        async def settle() -> None:
            async with engine.begin() as connection:
                store = PostgresArchiveStore(connection)
                await store.settle([artwork], RULES)
                await asyncio.sleep(0.2)  # hold the transaction open, as a long write would

        try:
            await asyncio.gather(*(settle() for _ in range(4)))
        finally:
            await engine.dispose()

    asyncio.run(settle_together())

    assert discovery.ids(q="gatto") == [artwork]
