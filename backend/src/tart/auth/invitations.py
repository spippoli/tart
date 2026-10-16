"""Invitations (Contribution and moderation spec, Invitations; Foundations spec, Registration).

Under `community.registration = invite` only an address with a pending Invitation may
register. An Invitation is issued by a Moderator or, from the CLI, by the Operator; it is
bound to one email address, single-use, and expires after 14 days. It is redeemed by
registering with the ordinary email code at that address, which creates a User without
any role (`redeem`). Revoking a Moderator's role leaves their Invitations as they were.

An Invitation is never deleted: a used, expired, or revoked one stays in the list.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any

from sqlalchemy import and_, exists, insert, select, update
from sqlalchemy.ext.asyncio import AsyncConnection

from tart.auth.tables import invitation, user_account

INVITATION_LIFETIME = timedelta(days=14)
"""A platform constant."""

# Error codes, which the frontend translates.
REGISTRATION_NOT_INVITE = "registration_not_invite"
INVITATION_PENDING = "invitation_pending"
INVITATION_NOT_FOUND = "invitation_not_found"
INVITATION_NOT_PENDING = "invitation_not_pending"


class Status(StrEnum):
    PENDING = "pending"
    USED = "used"
    EXPIRED = "expired"
    REVOKED = "revoked"


class InvitationError(Exception):
    """A request the Invitation rules refuse; `code` is stable."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class Issuer:
    number: int
    display_name: str


@dataclass(frozen=True)
class Invitation:
    id: int
    email: str
    status: Status
    issuer: Issuer | None
    """None when the Operator issued it from the CLI."""
    created_at: datetime
    expires_at: datetime
    used_at: datetime | None
    revoked_at: datetime | None


def _status(row: Any, now: datetime) -> Status:
    if row.used_at is not None:
        return Status.USED
    if row.revoked_at is not None:
        return Status.REVOKED
    if row.expires_at <= now:
        return Status.EXPIRED
    return Status.PENDING


def _is_pending(now: datetime):
    return and_(
        invitation.c.used_at.is_(None),
        invitation.c.revoked_at.is_(None),
        invitation.c.expires_at > now,
    )


async def issue(
    connection: AsyncConnection, email: str, issued_by: int | None, now: datetime
) -> int:
    """Invite the (normalised) address; the id of the Invitation.

    One pending Invitation per address: a second one is refused until the first is
    used, expires, or is revoked. The caller has checked that registration is `invite`."""
    if await connection.scalar(
        select(exists().where(invitation.c.email == email, _is_pending(now)))
    ):
        raise InvitationError(INVITATION_PENDING)
    invitation_id = await connection.scalar(
        insert(invitation)
        .values(
            email=email,
            issued_by=issued_by,
            created_at=now,
            expires_at=now + INVITATION_LIFETIME,
        )
        .returning(invitation.c.id)
    )
    assert invitation_id is not None
    return invitation_id


async def listing(connection: AsyncConnection, now: datetime) -> Sequence[Invitation]:
    """Every Invitation, the latest first."""
    rows = await connection.execute(
        select(
            invitation,
            user_account.c.id.label("issuer_number"),
            user_account.c.display_name.label("issuer_name"),
        )
        .select_from(
            invitation.outerjoin(user_account, user_account.c.id == invitation.c.issued_by)
        )
        .order_by(invitation.c.created_at.desc(), invitation.c.id.desc())
    )
    return [
        Invitation(
            id=row.id,
            email=row.email,
            status=_status(row, now),
            issuer=Issuer(row.issuer_number, row.issuer_name)
            if row.issuer_number is not None
            else None,
            created_at=row.created_at,
            expires_at=row.expires_at,
            used_at=row.used_at,
            revoked_at=row.revoked_at,
        )
        for row in rows
    ]


async def revoke(
    connection: AsyncConnection, invitation_id: int, revoked_by: int, now: datetime
) -> None:
    """Revoke a pending Invitation; any Moderator may, not only its issuer."""
    row = (
        await connection.execute(
            select(invitation).where(invitation.c.id == invitation_id).with_for_update()
        )
    ).one_or_none()
    if row is None:
        raise InvitationError(INVITATION_NOT_FOUND)
    if _status(row, now) is not Status.PENDING:
        raise InvitationError(INVITATION_NOT_PENDING)
    await connection.execute(
        update(invitation)
        .where(invitation.c.id == invitation_id)
        .values(revoked_at=now, revoked_by=revoked_by)
    )


async def admits(connection: AsyncConnection, email: str, now: datetime) -> bool:
    """Whether the address has a pending Invitation."""
    return bool(
        await connection.scalar(
            select(exists().where(invitation.c.email == email, _is_pending(now)))
        )
    )


async def redeem(connection: AsyncConnection, email: str, user_id: int, now: datetime) -> None:
    """Mark the address's pending Invitation used by the User just created."""
    await connection.execute(
        update(invitation)
        .where(invitation.c.email == email, _is_pending(now))
        .values(used_at=now, used_by=user_id)
    )
