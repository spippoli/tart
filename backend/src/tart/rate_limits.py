"""Rate limits: count an action against named limits for a key, with counters in PostgreSQL.

    wait = await hit(connection, [(CODE_PER_EMAIL_MINUTE, email), ...], now, key)
    if wait is not None: ...   # refused: nothing was counted; retry after `wait`

Each limit is a sliding window: an action is allowed while fewer than `count`
actions were counted for the key in the last `window`. A refused action counts
for nothing. Keys (email addresses, IP addresses, User numbers) are stored only as
keyed hashes, and each counted action is deleted by the hourly sweep once its
window has ended, so nothing is kept longer than the longest window (Foundations
spec, 2. Rate limits and spam protection). No limit ever locks an account.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Identity,
    Index,
    LargeBinary,
    Table,
    Text,
    delete,
    func,
    insert,
    select,
)
from sqlalchemy.ext.asyncio import AsyncConnection

from tart.auth.tokens import keyed_hash
from tart.db import Base

rate_limit_event = Table(
    "rate_limit_event",
    Base.metadata,
    Column("id", BigInteger, Identity(), primary_key=True),
    Column("name", Text, nullable=False),
    Column("key_hash", LargeBinary, nullable=False),
    Column("at", DateTime(timezone=True), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False, index=True),
    Index(None, "name", "key_hash", "at"),
)


@dataclass(frozen=True)
class Limit:
    name: str
    count: int
    window: timedelta


async def hit(
    connection: AsyncConnection,
    checks: Sequence[tuple[Limit, str]],
    now: datetime,
    key: bytes,
) -> timedelta | None:
    """Count one action against every `(limit, key)` pair, or refuse it.

    Returns None when every limit allows the action, which is then counted for
    each; otherwise the longest wait before all of them would allow it.
    """
    hashed = [(limit, keyed_hash(key, limit.name, value)) for limit, value in checks]
    # Serialise concurrent actions on the same keys, so that two requests cannot
    # both take the last place in a window.
    for _, key_hash in sorted(hashed, key=lambda pair: pair[1]):
        await connection.execute(
            select(func.pg_advisory_xact_lock(func.hashtextextended(key_hash.hex(), 0)))
        )
    waits = [await _wait(connection, limit, key_hash, now) for limit, key_hash in hashed]
    refused = [wait for wait in waits if wait is not None]
    if refused:
        return max(refused)
    await connection.execute(
        insert(rate_limit_event),
        [
            {"name": limit.name, "key_hash": key_hash, "at": now, "expires_at": now + limit.window}
            for limit, key_hash in hashed
        ],
    )
    return None


async def _wait(
    connection: AsyncConnection, limit: Limit, key_hash: bytes, now: datetime
) -> timedelta | None:
    # The `count` most recent actions in the window; when there are that many, the
    # oldest of them must leave the window before another action is allowed.
    recent = (
        await connection.scalars(
            select(rate_limit_event.c.at)
            .where(
                rate_limit_event.c.name == limit.name,
                rate_limit_event.c.key_hash == key_hash,
                rate_limit_event.c.at > now - limit.window,
            )
            .order_by(rate_limit_event.c.at.desc())
            .limit(limit.count)
        )
    ).all()
    if len(recent) < limit.count:
        return None
    return recent[-1] + limit.window - now


async def delete_expired(connection: AsyncConnection, now: datetime) -> None:
    """Delete every counted action whose window has ended (the hourly sweep)."""
    await connection.execute(delete(rate_limit_event).where(rate_limit_event.c.expires_at <= now))
