"""Which `terms.version` each User accepted (contribution spec, Terms of use)."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncConnection

from tart.moderation_persistence.tables import user_terms_acceptance as acceptance


async def accepted_version(connection: AsyncConnection, user_id: int) -> int | None:
    return await connection.scalar(
        select(acceptance.c.version).where(acceptance.c.user_id == user_id)
    )


def acceptance_needed(accepted: int | None, current: int) -> bool:
    """The Review step asks when the User never accepted, or accepted a lower version."""
    return accepted is None or accepted < current


async def accept(connection: AsyncConnection, user_id: int, version: int, now: datetime) -> None:
    """Store the version the User accepted; a version never goes down."""
    statement = insert(acceptance).values(user_id=user_id, version=version, accepted_at=now)
    await connection.execute(
        statement.on_conflict_do_update(
            index_elements=[acceptance.c.user_id],
            set_={
                "version": func.greatest(acceptance.c.version, statement.excluded.version),
                "accepted_at": now,
            },
        )
    )
