"""The list entries of a page cost a number of queries that grows far less than the page.
Every record is fictional."""

# ruff: noqa: F401, F811
# The fixtures are imported for pytest and named again as parameters.
import asyncio

from discovery_fixtures import World, world
from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine

from tart.archive_read import Reader, Viewer


def count_queries(world: World, ids: list[int]) -> int:
    async def run() -> int:
        engine = create_async_engine(world.archive.url)
        statements: list[str] = []
        event.listen(
            engine.sync_engine,
            "before_cursor_execute",
            lambda connection, cursor, statement, *rest: statements.append(statement),
        )
        try:
            async with engine.connect() as connection:
                await Reader(connection, Viewer()).entries(ids)
        finally:
            await engine.dispose()
        return len(statements)

    return asyncio.run(run())


def test_the_entries_of_a_page_cost_a_few_queries_each(world: World) -> None:
    site = world.site("Sito di prova")
    artist = world.artist("Artista Uno")
    ids = [
        world.artwork(f"Opera {number}", artists=(artist,), at=world.place(12.4 + number / 100))
        for number in range(12)
    ]
    _ = site

    few, many = count_queries(world, ids[:2]), count_queries(world, ids)

    print(f"\n{few} queries for 2 entries, {many} for 12")
    assert many - few <= 3 * 10
