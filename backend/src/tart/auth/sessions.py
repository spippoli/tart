"""Sessions: an opaque id in a cookie, stored in PostgreSQL as a keyed hash (ADR 0005).

A session ends 30 days after its last request (idle) or 90 days after sign-in
(absolute), whichever comes first; a request extends the idle expiry, written at
most once a day. Revoking deletes the row, so it takes effect on the next request.
Roles are read on every request, so a revoked role stops working at once.
"""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import delete, exists, insert, select, update
from sqlalchemy.ext.asyncio import AsyncConnection

from tart.auth import (
    SESSION_ABSOLUTE_LIFETIME,
    SESSION_IDLE_LIFETIME,
    SESSION_IDLE_WRITE_INTERVAL,
)
from tart.auth.tables import MODERATOR, user_account, user_role, user_session
from tart.auth.tokens import keyed_hash, new_session_token

COOKIE = "tart_session"


@dataclass(frozen=True)
class SessionUser:
    """The signed-in User of a request."""

    id: int
    """The User number."""
    display_name: str
    preferred_language: str
    moderator: bool


async def create(connection: AsyncConnection, user_id: int, now: datetime, key: bytes) -> str:
    """A new session for the User; returns the token for the cookie."""
    token = new_session_token()
    await connection.execute(
        insert(user_session).values(
            id_hash=keyed_hash(key, token), user_id=user_id, created_at=now, last_seen_at=now
        )
    )
    return token


async def resolve(
    connection: AsyncConnection, token: str, now: datetime, key: bytes
) -> SessionUser | None:
    """The User of a live session, extending its idle expiry; None for anything else."""
    id_hash = keyed_hash(key, token)
    is_moderator = exists().where(
        user_role.c.user_id == user_account.c.id, user_role.c.role == MODERATOR
    )
    row = (
        await connection.execute(
            select(
                user_session.c.last_seen_at,
                user_account.c.id,
                user_account.c.display_name,
                user_account.c.preferred_language,
                is_moderator.label("moderator"),
            )
            .join(user_account, user_account.c.id == user_session.c.user_id)
            .where(
                user_session.c.id_hash == id_hash,
                user_session.c.created_at > now - SESSION_ABSOLUTE_LIFETIME,
                user_session.c.last_seen_at > now - SESSION_IDLE_LIFETIME,
                user_account.c.suspended_at.is_(None),
            )
        )
    ).one_or_none()
    if row is None:
        return None
    if now - row.last_seen_at >= SESSION_IDLE_WRITE_INTERVAL:
        await connection.execute(
            update(user_session).where(user_session.c.id_hash == id_hash).values(last_seen_at=now)
        )
    return SessionUser(row.id, row.display_name, row.preferred_language, row.moderator)


async def revoke(connection: AsyncConnection, token: str, key: bytes) -> None:
    await connection.execute(
        delete(user_session).where(user_session.c.id_hash == keyed_hash(key, token))
    )


async def revoke_all(connection: AsyncConnection, user_id: int) -> None:
    """Sign out everywhere: end every session of the User, the current one included."""
    await connection.execute(delete(user_session).where(user_session.c.user_id == user_id))


async def delete_expired(connection: AsyncConnection, now: datetime) -> None:
    """Delete the sessions past either expiry (the hourly sweep)."""
    await connection.execute(
        delete(user_session).where(
            (user_session.c.created_at <= now - SESSION_ABSOLUTE_LIFETIME)
            | (user_session.c.last_seen_at <= now - SESSION_IDLE_LIFETIME)
        )
    )
