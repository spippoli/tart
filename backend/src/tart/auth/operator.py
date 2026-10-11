"""What the Operator does to Users from the CLI (Foundations spec, 2. Roles and Suspension).

Roles and Suspensions have no UI in the MVP. Both are read on every request
(`tart.auth.sessions.resolve`), so a revoked role or a Suspension takes effect on
the User's next request, open sessions included. A Suspension also deletes every
session of the User; a code request for their address then sends nothing.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import delete, exists, func, insert, select, update
from sqlalchemy.dialects.postgresql import insert as upsert
from sqlalchemy.ext.asyncio import AsyncConnection

from tart.auth import sessions
from tart.auth.tables import MODERATOR, user_account, user_role
from tart.auth.users import normalise_email

SUSPENSION_EMAIL = "suspension"


class OperatorError(Exception):
    """An action the CLI refuses, with the message it prints."""


@dataclass(frozen=True)
class User:
    id: int
    """The User number."""
    email: str
    display_name: str
    preferred_language: str
    suspended_at: datetime | None


def address(value: str) -> str:
    """The normalised address, or `OperatorError`."""
    email = normalise_email(value)
    if email is None:
        raise OperatorError(f"{value!r} is not an email address")
    return email


_USER_COLUMNS = (
    user_account.c.id,
    user_account.c.email,
    user_account.c.display_name,
    user_account.c.preferred_language,
    user_account.c.suspended_at,
)


async def find(connection: AsyncConnection, email: str) -> User | None:
    row = (
        await connection.execute(select(*_USER_COLUMNS).where(user_account.c.email == email))
    ).one_or_none()
    return User(*row) if row is not None else None


async def _existing(connection: AsyncConnection, email: str) -> User:
    user = await find(connection, email)
    if user is None:
        raise OperatorError(f"no User has the address {email}")
    return user


async def create(
    connection: AsyncConnection, email: str, display_name: str, language: str, now: datetime
) -> User:
    """A User created by the Operator, without the registration step."""
    user_id = await connection.scalar(
        insert(user_account)
        .values(email=email, display_name=display_name, preferred_language=language, created_at=now)
        .returning(user_account.c.id)
    )
    return User(user_id, email, display_name, language, None)


async def grant_moderator(connection: AsyncConnection, user: User) -> bool:
    """Give the User the Moderator role; False if they already held it."""
    result = await connection.execute(
        upsert(user_role).values(user_id=user.id, role=MODERATOR).on_conflict_do_nothing()
    )
    return result.rowcount == 1


async def revoke_moderator(connection: AsyncConnection, email: str) -> bool:
    """Take the Moderator role away; False if the User did not hold it.

    Past decisions, Moderation notes, and Invitations stay attributed to them."""
    user = await _existing(connection, email)
    result = await connection.execute(
        delete(user_role).where(user_role.c.user_id == user.id, user_role.c.role == MODERATOR)
    )
    return result.rowcount == 1


async def moderators(connection: AsyncConnection) -> Sequence[User]:
    """The Users holding the Moderator role, suspended ones included, by User number."""
    rows = await connection.execute(
        select(*_USER_COLUMNS)
        .join(user_role, user_role.c.user_id == user_account.c.id)
        .where(user_role.c.role == MODERATOR)
        .order_by(user_account.c.id)
    )
    return [User(*row) for row in rows]


async def suspend(connection: AsyncConnection, email: str, reason: str, now: datetime) -> User:
    """Suspend the User and end every session of theirs; the caller sends the email.

    Drafts, open Submissions, and approved contributions are left as they are."""
    reason = reason.strip()
    if not reason:
        raise OperatorError("the reason may not be empty: the User receives it")
    user = await _existing(connection, email)
    if user.suspended_at is not None:
        raise OperatorError(
            f"#{user.id} is already suspended since {user.suspended_at:%Y-%m-%d}; "
            "unsuspend first to change the reason"
        )
    await connection.execute(
        update(user_account)
        .where(user_account.c.id == user.id)
        .values(suspended_at=now, suspension_reason=reason)
    )
    await sessions.revoke_all(connection, user.id)
    return user


async def unsuspend(connection: AsyncConnection, email: str) -> User:
    """Lift the Suspension, clearing its date and reason. No email is sent."""
    user = await _existing(connection, email)
    if user.suspended_at is None:
        raise OperatorError(f"#{user.id} is not suspended")
    await connection.execute(
        update(user_account)
        .where(user_account.c.id == user.id)
        .values(suspended_at=None, suspension_reason=None)
    )
    return user


async def moderator_warnings(connection: AsyncConnection, self_approval: bool) -> list[str]:
    """The warnings of `tart config check --database` and startup, which never fail.

    A suspended Moderator keeps the role but cannot act, so only the others count."""
    count = await connection.scalar(
        select(func.count())
        .select_from(user_account)
        .where(
            exists().where(user_role.c.user_id == user_account.c.id, user_role.c.role == MODERATOR),
            user_account.c.suspended_at.is_(None),
        )
    )
    if count == 0:
        return [
            "no User holds the Moderator role, so nobody can moderate; "
            "grant it with `tart users grant moderator <email>`"
        ]
    if count == 1 and not self_approval:
        return [
            "only one User holds the Moderator role and self_approval is false, "
            "so nobody can decide on that Moderator's own Submissions"
        ]
    return []
