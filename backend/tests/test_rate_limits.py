"""The rate-limit module: sliding windows, and actions that cost more than one (bytes)."""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncConnection

from tart import rate_limits
from tart.db import create_engine
from tart.rate_limits import Limit

KEY = b"test-key"
NOW = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)
BYTES = Limit("test_bytes", 100, timedelta(hours=24))
HOURS = timedelta(hours=1)


def _run[T](database: str, work: Callable[[AsyncConnection], Awaitable[T]]) -> T:
    async def go() -> T:
        engine = create_engine(database)
        try:
            async with engine.begin() as connection:
                return await work(connection)
        finally:
            await engine.dispose()

    return asyncio.run(go())


def test_an_action_costs_its_weight_against_the_limit(migrated_database: str) -> None:
    async def work(connection: AsyncConnection) -> list[timedelta | None]:
        async def hit(cost: int, at: timedelta) -> timedelta | None:
            return await rate_limits.hit(connection, [(BYTES, "ada", cost)], NOW + at, KEY)

        return [
            await hit(60, timedelta(0)),
            await hit(30, HOURS),
            await hit(11, 2 * HOURS),  # 101 in all: refused, and not counted
            await hit(10, 2 * HOURS),
            await hit(1, 3 * HOURS),
        ]

    results = _run(migrated_database, work)

    assert results[:2] == [None, None]
    # The first 60 leave the window after 24 hours; at 2 hours that is 22 hours away.
    assert results[2] == 22 * HOURS
    assert results[3] is None
    assert results[4] == 21 * HOURS


def test_an_action_costing_more_than_the_limit_is_never_allowed(migrated_database: str) -> None:
    async def work(connection: AsyncConnection) -> timedelta | None:
        return await rate_limits.hit(connection, [(BYTES, "ada", 101)], NOW, KEY)

    assert _run(migrated_database, work) == BYTES.window


def test_an_action_without_a_cost_counts_once(migrated_database: str) -> None:
    once = Limit("test_once", 2, timedelta(hours=24))

    async def work(connection: AsyncConnection) -> list[timedelta | None]:
        return [
            await rate_limits.hit(connection, [(once, "ada")], NOW + n * HOURS, KEY)
            for n in range(3)
        ]

    assert _run(migrated_database, work) == [None, None, 22 * HOURS]
