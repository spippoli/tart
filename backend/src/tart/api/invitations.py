"""`/api/moderation/invitations`: issue, list, and revoke Invitations (Contribution and
moderation spec, Invitations). Moderators only, and only under `registration = invite`.

An Invitation's email address is visible to Moderators, who entered it. The invitation
email belongs to the Notifications spec; until it exists nothing is sent, and the
Moderator copies the link to the sign-in page, where the invited person registers.
"""

from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncEngine

from tart.api.auth import (
    Clock,
    Error,
    current_user,
    get_clock,
    get_configuration,
    get_engine,
)
from tart.auth import invitations
from tart.auth.invitations import REGISTRATION_NOT_INVITE, Invitation, InvitationError
from tart.auth.sessions import SessionUser
from tart.auth.users import normalise_email
from tart.config import Configuration

router = APIRouter(prefix="/api/moderation/invitations")

SIGN_IN_REQUIRED = "sign_in_required"
MODERATOR_ONLY = "moderator_only"
EMAIL_INVALID = "email_invalid"

_ERRORS: dict[int | str, dict] = {
    401: {"model": Error},
    403: {"model": Error},
    409: {"model": Error},
}


async def moderator(
    user: Annotated[SessionUser | None, Depends(current_user)],
    configuration: Annotated[Configuration, Depends(get_configuration)],
) -> SessionUser | JSONResponse:
    """The signed-in Moderator, or the refusal: 401 anonymous, 403 without the role, 409
    when the Instance does not use Invitations."""
    if user is None:
        return JSONResponse({"code": SIGN_IN_REQUIRED}, status_code=401)
    if not user.moderator:
        return JSONResponse({"code": MODERATOR_ONLY}, status_code=403)
    if configuration.instance.settings.community.registration != "invite":
        return JSONResponse({"code": REGISTRATION_NOT_INVITE}, status_code=409)
    return user


Moderator = Annotated[SessionUser | JSONResponse, Depends(moderator)]


class IssuerOut(BaseModel):
    number: int
    display_name: str


class InvitationOut(BaseModel):
    id: int
    email: str
    status: Literal["pending", "used", "expired", "revoked"]
    issuer: IssuerOut | None
    """Null when the Operator issued it from the CLI."""
    created_at: datetime
    expires_at: datetime
    used_at: datetime | None
    revoked_at: datetime | None


def _out(invitation: Invitation) -> InvitationOut:
    issuer = invitation.issuer
    return InvitationOut(
        id=invitation.id,
        email=invitation.email,
        status=invitation.status.value,  # type: ignore[arg-type]
        issuer=IssuerOut(number=issuer.number, display_name=issuer.display_name)
        if issuer
        else None,
        created_at=invitation.created_at,
        expires_at=invitation.expires_at,
        used_at=invitation.used_at,
        revoked_at=invitation.revoked_at,
    )


class InvitationList(BaseModel):
    items: list[InvitationOut]


@router.get("", responses=_ERRORS)
async def list_invitations(
    user: Moderator,
    engine: Annotated[AsyncEngine, Depends(get_engine)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> InvitationList:
    """Every Invitation with its status, the latest first."""
    if isinstance(user, JSONResponse):
        return user  # type: ignore[return-value]
    async with engine.begin() as connection:
        found = await invitations.listing(connection, clock())
    return InvitationList(items=[_out(each) for each in found])


class IssueBody(BaseModel):
    email: str


@router.post("", status_code=201, responses={**_ERRORS, 400: {"model": Error}})
async def issue_invitation(
    body: IssueBody,
    user: Moderator,
    engine: Annotated[AsyncEngine, Depends(get_engine)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> InvitationOut:
    """Invite an email address. It is single-use, valid for 14 days, and redeemed by
    registering at that address; no email is sent yet (the link is the sign-in page)."""
    if isinstance(user, JSONResponse):
        return user  # type: ignore[return-value]
    email = normalise_email(body.email)
    if email is None:
        return JSONResponse({"code": EMAIL_INVALID}, status_code=400)  # type: ignore[return-value]
    now = clock()
    try:
        async with engine.begin() as connection:
            invitation_id = await invitations.issue(connection, email, user.id, now)
            created = next(
                each
                for each in await invitations.listing(connection, now)
                if each.id == invitation_id
            )
    except InvitationError as error:
        return JSONResponse({"code": error.code}, status_code=409)  # type: ignore[return-value]
    return _out(created)


@router.post(
    "/{invitation_id}/revoke",
    status_code=204,
    responses={**_ERRORS, 404: {"model": Error}},
)
async def revoke_invitation(
    invitation_id: int,
    user: Moderator,
    engine: Annotated[AsyncEngine, Depends(get_engine)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> None:
    """Revoke a pending Invitation; any Moderator may."""
    if isinstance(user, JSONResponse):
        return user  # type: ignore[return-value]
    try:
        async with engine.begin() as connection:
            await invitations.revoke(connection, invitation_id, user.id, clock())
    except InvitationError as error:
        status = 404 if error.code == invitations.INVITATION_NOT_FOUND else 409
        return JSONResponse({"code": error.code}, status_code=status)  # type: ignore[return-value]
