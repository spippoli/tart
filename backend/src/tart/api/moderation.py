"""`/api/moderation`: the queue (Contribution and moderation spec, Queue). Moderators only.

    GET /api/moderation/queue    the Submissions awaiting a decision, with flags

The orders are the only three of the spec (oldest first by first-submitted date, newest first,
recently resubmitted); the filters are the derived label, the target kind, the Submitter by
User number, the Area, and Outdated. A Submitter appears by display name and User number,
never by email address. The decisions and the Moderation notes are on the Submission
(`/api/contributions/{id}/decision`, `/notes`).
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncEngine

from tart import moderation
from tart.api.auth import SIGN_IN_REQUIRED, Error, current_user, get_engine
from tart.api.contributions import Intent, Person, intent_of, people_of
from tart.archive.records import Kind
from tart.auth.sessions import SessionUser
from tart.moderation import Label
from tart.moderation_persistence import queue
from tart.moderation_persistence.queue import Filters, Sort

router = APIRouter(prefix="/api/moderation")

MODERATOR_ONLY = "moderator_only"


class QueueItem(BaseModel):
    id: int
    target_kind: Kind
    intent: Intent
    target_id: int | None
    labels: list[str]
    """Derived from the changeset, never entered."""
    submitter: Person
    own: bool
    """Whether the caller is the Submitter: under `self_approval = false` they cannot decide."""
    first_submitted_at: datetime
    latest_round_at: datetime
    rounds: int
    outdated: list[str]
    """Why it is Outdated; empty when it is not."""
    overlapping: list[int]
    """Other open Submissions on the same record."""
    nearby_creates: list[int]
    """Other pending creates within 25 m of this one's new Location."""


class QueueOut(BaseModel):
    sort: Sort
    items: list[QueueItem]


@router.get(
    "/queue",
    response_model=QueueOut,
    responses={401: {"model": Error}, 403: {"model": Error}},
)
async def read_queue(
    user: Annotated[SessionUser | None, Depends(current_user)],
    engine: Annotated[AsyncEngine, Depends(get_engine)],
    sort: Sort = Sort.OLDEST,
    label: Label | None = None,
    target_kind: Kind | None = None,
    submitter: int | None = None,
    area: int | None = None,
    outdated: bool | None = None,
) -> QueueOut | JSONResponse:
    """The Submissions awaiting a decision, oldest first unless told otherwise."""
    if user is None:
        return JSONResponse({"code": SIGN_IN_REQUIRED}, status_code=401)
    if not user.moderator:
        return JSONResponse({"code": MODERATOR_ONLY}, status_code=403)
    filters = Filters(label.value if label else None, target_kind, submitter, area, outdated)
    async with engine.connect() as connection:
        entries = await queue.queue(connection, sort, filters)
        people = await people_of(connection, {entry.submission.submitter_id for entry in entries})
    return QueueOut(
        sort=sort,
        items=[
            QueueItem(
                id=entry.submission.id,
                target_kind=entry.submission.target_kind,
                intent=intent_of(entry.submission),
                target_id=entry.submission.target_id,
                labels=list(moderation.labels_of(entry.submission)),
                submitter=people.get(
                    entry.submission.submitter_id,
                    Person(number=entry.submission.submitter_id, display_name=""),
                ),
                own=entry.submission.submitter_id == user.id,
                first_submitted_at=entry.submission.rounds[0].submitted_at,
                latest_round_at=entry.latest_round_at,
                rounds=len(entry.submission.rounds),
                outdated=[reason.value for reason in entry.outdated],
                overlapping=list(entry.overlapping),
                nearby_creates=list(entry.nearby_creates),
            )
            for entry in entries
        ],
    )
