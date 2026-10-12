"""The Account page's own settings: the display name and the preferred UI language
(Foundations spec, 2. Account). They belong to TART whatever the authentication
method; the email address changes through `Authentication`.

Revisions keep the submitter's User number, never a copy of the name, so a new
display name shows on every `/revisions` entry of the User, past ones included.
"""

from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncConnection

from tart.auth.tables import user_account


@dataclass(frozen=True)
class Account:
    number: int
    email: str
    display_name: str
    preferred_language: str


async def read(connection: AsyncConnection, user_id: int) -> Account:
    row = (
        await connection.execute(
            select(
                user_account.c.id,
                user_account.c.email,
                user_account.c.display_name,
                user_account.c.preferred_language,
            ).where(user_account.c.id == user_id)
        )
    ).one()
    return Account(row.id, row.email, row.display_name, row.preferred_language)


async def change(
    connection: AsyncConnection,
    user_id: int,
    *,
    display_name: str | None = None,
    preferred_language: str | None = None,
) -> None:
    """Store the settings given, already checked; the others stay as they are."""
    values = {
        name: value
        for name, value in (
            ("display_name", display_name),
            ("preferred_language", preferred_language),
        )
        if value is not None
    }
    if values:
        await connection.execute(
            update(user_account).where(user_account.c.id == user_id).values(**values)
        )
