"""The moderation queue: the Submissions awaiting a decision, in one of three orders, with
filters and the flags that tell a Moderator what to look at (contribution-and-moderation
spec, Queue).

    entries = await queue(connection, Sort.OLDEST, Filters(target_kind=Kind.ARTWORK))

Nothing here ranks by popularity: the orders are the date of the first submission (so a
resubmission or a revision keeps its place), its reverse, and the date of the latest round.
There is no claiming or assignment; the first decision wins (`moderation.already_decided`).
"""

import json
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncConnection

from tart import moderation
from tart.archive.changeset import Create, SetField
from tart.archive.geometry import Geometry
from tart.archive.records import Artwork, Kind, Location
from tart.archive_persistence import PostgresArchiveStore
from tart.archive_persistence import tables as t
from tart.moderation import Reason, Status, Submission
from tart.moderation_persistence import service, store
from tart.moderation_persistence import tables as s
from tart.moderation_persistence.duplicates import nearby_pending_creates

OPEN = (Status.SUBMITTED.value, Status.CHANGES_REQUESTED.value)
"""The Submissions a decision can still reach: two on one record overlap."""


class Sort(StrEnum):
    """The only orders of the queue."""

    OLDEST = "oldest"
    """By first-submitted date, oldest first: the default."""
    NEWEST = "newest"
    RESUBMITTED = "resubmitted"
    """By the date of the latest round, newest first."""


@dataclass(frozen=True)
class Filters:
    label: str | None = None
    target_kind: Kind | None = None
    submitter: int | None = None
    """A User number."""
    area: int | None = None
    """Submissions about a place inside this Area."""
    outdated: bool | None = None


@dataclass(frozen=True)
class Entry:
    submission: Submission
    latest_round_at: datetime
    outdated: tuple[Reason, ...]
    overlapping: tuple[int, ...]
    """Other open Submissions on the same record (ADR 0007)."""
    nearby_creates: tuple[int, ...]
    """Other pending creates within the proximity rule of this one's new Location."""


async def _place(connection: AsyncConnection, submission: Submission) -> Geometry | None:
    """Where the Submission is about: the Location it creates or moves, the Location of the
    Artwork it creates or edits, else none."""
    if not submission.rounds:
        return None
    content = moderation.decode_content(submission.rounds[-1].snapshot, submission.target_kind)
    archive = PostgresArchiveStore(connection)
    location_ref: object = None
    for operation in content.operations:
        match operation:
            case Create(record=Location() as place):
                return place.geometry
            case SetField(field="geometry", value=Geometry() as moved) if (
                submission.target_kind is Kind.LOCATION
            ):
                return moved
            case Create(record=Artwork(location=int() as existing)):
                location_ref = existing
    target = await archive.get(submission.target_id) if submission.target_id is not None else None
    if isinstance(target, Location):
        return target.geometry
    if isinstance(target, Artwork):
        location_ref = target.location
    if isinstance(location_ref, int):
        place = await archive.get(location_ref)
        if isinstance(place, Location):
            return place.geometry
    return None


async def _in_area(connection: AsyncConnection, area_id: int, place: Geometry) -> bool:
    found = await connection.scalar(
        select(
            func.ST_Intersects(
                t.area.c.geometry,
                func.ST_SetSRID(func.ST_GeomFromGeoJSON(json.dumps(place.to_geojson())), 4326),
            )
        ).where(t.area.c.id == area_id)
    )
    return bool(found)


def _order(sort: Sort, first, latest):  # type: ignore[no-untyped-def]
    match sort:
        case Sort.OLDEST:
            return (first.asc(), s.submission.c.id.asc())
        case Sort.NEWEST:
            return (first.desc(), s.submission.c.id.desc())
        case Sort.RESUBMITTED:
            return (latest.desc(), s.submission.c.id.desc())


async def queue(
    connection: AsyncConnection, sort: Sort = Sort.OLDEST, filters: Filters | None = None
) -> list[Entry]:
    """The Submissions in `submitted`, in the order asked for, narrowed by the filters.

    A Submission in `changes requested` waits for its Submitter, not for a decision, so it
    is not queued; a Moderator can still reach it by its page and reject it.
    """
    filters = filters or Filters()
    rounds = (
        select(
            s.submission_round.c.submission_id,
            func.min(s.submission_round.c.submitted_at).label("first"),
            func.max(s.submission_round.c.submitted_at).label("latest"),
        )
        .group_by(s.submission_round.c.submission_id)
        .subquery()
    )
    query = (
        select(s.submission.c.id, rounds.c.latest)
        .join(rounds, rounds.c.submission_id == s.submission.c.id)
        .where(s.submission.c.status == Status.SUBMITTED.value)
        .order_by(*_order(sort, rounds.c.first, rounds.c.latest))
    )
    if filters.target_kind is not None:
        query = query.where(s.submission.c.target_kind == filters.target_kind.value)
    if filters.submitter is not None:
        query = query.where(s.submission.c.submitter_id == filters.submitter)
    rows = (await connection.execute(query)).all()

    overlaps: dict[int, list[int]] = {}
    for row in await connection.execute(
        select(s.submission.c.id, s.submission.c.target_id).where(
            s.submission.c.status.in_(OPEN), s.submission.c.target_id.is_not(None)
        )
    ):
        overlaps.setdefault(row.target_id, []).append(row.id)
    nearby = await nearby_pending_creates(connection)

    entries: list[Entry] = []
    for row in rows:
        submission = await store.load(connection, row.id)
        assert submission is not None
        if filters.label is not None and filters.label not in moderation.labels_of(submission):
            continue
        reasons = await service.outdated_now(connection, submission)
        if filters.outdated is not None and bool(reasons) is not filters.outdated:
            continue
        if filters.area is not None:
            place = await _place(connection, submission)
            if place is None or not await _in_area(connection, filters.area, place):
                continue
        sharing = overlaps.get(submission.target_id or 0, [])
        entries.append(
            Entry(
                submission,
                row.latest,
                reasons,
                tuple(sorted(each for each in sharing if each != submission.id)),
                nearby.get(submission.id, ()),
            )
        )
    return entries
