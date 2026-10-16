"""The PostgreSQL adapter of the Submission aggregate.

It works on one `AsyncConnection` inside a transaction its caller owns. The aggregate
only grows (rounds, log entries, and notes are appended), so `save` stores what the
database does not have yet.
"""

from datetime import datetime

from sqlalchemy import Table, delete, func, insert, null, select, update
from sqlalchemy.ext.asyncio import AsyncConnection

from tart.archive.codec import Json
from tart.archive.records import Kind
from tart.moderation.model import (
    Actor,
    ActorKind,
    Event,
    LogEntry,
    ModerationNote,
    Round,
    Status,
    Submission,
)
from tart.moderation_persistence import tables as t


async def create_draft(
    connection: AsyncConnection,
    submitter_id: int,
    target_kind: Kind,
    now: datetime,
    *,
    target_id: int | None = None,
    base_revisions: tuple[int, ...] = (),
    retry_of: int | None = None,
    converts: int | None = None,
    working_copy: Json = None,
) -> Submission:
    """A contribution starts as a draft, as soon as it is started. A retry or a conversion
    starts with the content it is pre-filled with, which is not the Submitter's own entry:
    the draft still counts as never edited."""
    submission_id = await connection.scalar(
        insert(t.submission)
        .values(
            submitter_id=submitter_id,
            target_kind=target_kind.value,
            target_id=target_id,
            base_revisions=list(base_revisions),
            status=Status.DRAFT.value,
            created_at=now,
            retry_of=retry_of,
            converts=converts,
            working_copy=working_copy,
        )
        .returning(t.submission.c.id)
    )
    return Submission(
        submission_id,
        submitter_id,
        target_kind,
        target_id,
        base_revisions,
        Status.DRAFT,
        now,
        working_copy=working_copy,
        retry_of=retry_of,
        converts=converts,
    )


async def load(
    connection: AsyncConnection, submission_id: int, *, lock: bool = False
) -> Submission | None:
    """The Submission with its rounds, log, and notes; `lock` holds its row until the
    caller's transaction ends, so that the first of two concurrent decisions wins."""
    query = select(t.submission).where(t.submission.c.id == submission_id)
    row = (await connection.execute(query.with_for_update() if lock else query)).one_or_none()
    if row is None:
        return None
    rounds = (
        await connection.execute(
            select(t.submission_round)
            .where(t.submission_round.c.submission_id == submission_id)
            .order_by(t.submission_round.c.number)
        )
    ).all()
    log = (
        await connection.execute(
            select(t.submission_log)
            .where(t.submission_log.c.submission_id == submission_id)
            .order_by(t.submission_log.c.position)
        )
    ).all()
    notes = (
        await connection.execute(
            select(t.moderation_note)
            .where(t.moderation_note.c.submission_id == submission_id)
            .order_by(t.moderation_note.c.id)
        )
    ).all()
    return Submission(
        id=row.id,
        submitter_id=row.submitter_id,
        target_kind=Kind(row.target_kind),
        target_id=row.target_id,
        base_revisions=tuple(row.base_revisions),
        status=Status(row.status),
        created_at=row.created_at,
        rounds=tuple(Round(r.number, r.snapshot, r.submitted_at) for r in rounds),
        log=tuple(
            LogEntry(
                Event(e.event),
                Actor(ActorKind(e.actor_kind), e.actor_id),
                e.at,
                e.round,
                e.message,
                e.reason,
                e.related_submission_id,
            )
            for e in log
        ),
        notes=tuple(ModerationNote(n.author_id, n.at, n.text) for n in notes),
        working_copy=row.working_copy,
        last_autosave_at=row.last_autosave_at,
        working_copy_discarded=row.working_copy_discarded,
        retry_of=row.retry_of,
        converts=row.converts,
        reduced_at=row.reduced_at,
        stub=row.stub,
    )


async def _count(connection: AsyncConnection, table: Table, submission_id: int) -> int:  # type: ignore[name-defined]
    return await connection.scalar(
        select(func.count()).select_from(table).where(table.c.submission_id == submission_id)
    )


async def save(connection: AsyncConnection, submission: Submission) -> None:
    """Store the Submission's state and whatever was appended to it since it was loaded."""
    await connection.execute(
        update(t.submission)
        .where(t.submission.c.id == submission.id)
        .values(
            status=submission.status.value,
            target_id=submission.target_id,
            base_revisions=list(submission.base_revisions),
            working_copy=submission.working_copy,
            last_autosave_at=submission.last_autosave_at,
            working_copy_discarded=submission.working_copy_discarded,
            reduced_at=submission.reduced_at,
            stub=submission.stub,
        )
    )
    stored_rounds = await _count(connection, t.submission_round, submission.id)
    if submission.reduced_at is not None:
        # The stub keeps the rounds' number and date, never their changesets.
        await connection.execute(
            update(t.submission_round)
            .where(t.submission_round.c.submission_id == submission.id)
            .values(snapshot=null())
        )
    for round_ in submission.rounds[stored_rounds:]:
        await connection.execute(
            insert(t.submission_round).values(
                submission_id=submission.id,
                number=round_.number,
                snapshot=round_.snapshot,
                submitted_at=round_.submitted_at,
            )
        )
    stored_log = await _count(connection, t.submission_log, submission.id)
    for position, entry in enumerate(submission.log[stored_log:], start=stored_log):
        await connection.execute(
            insert(t.submission_log).values(
                submission_id=submission.id,
                position=position,
                event=entry.event.value,
                actor_kind=entry.actor.kind.value,
                actor_id=entry.actor.user_id,
                at=entry.at,
                round=entry.round,
                message=entry.message,
                reason=entry.reason,
                related_submission_id=entry.related,
            )
        )
    stored_notes = await _count(connection, t.moderation_note, submission.id)
    for note in submission.notes[stored_notes:]:
        await connection.execute(
            insert(t.moderation_note).values(
                submission_id=submission.id, author_id=note.author_id, at=note.at, text=note.text
            )
        )


async def delete_draft(connection: AsyncConnection, submission_id: int) -> None:
    """A deleted draft leaves nothing behind (its media are deleted by the media pipeline)."""
    await connection.execute(
        delete(t.submission).where(
            t.submission.c.id == submission_id, t.submission.c.status == Status.DRAFT.value
        )
    )


async def changes_requested(connection: AsyncConnection) -> list[int]:
    """The ids of the Submissions waiting for their Submitter."""
    return list(
        await connection.scalars(
            select(t.submission.c.id).where(t.submission.c.status == Status.CHANGES_REQUESTED.value)
        )
    )


async def of_submitter(
    connection: AsyncConnection, submitter_id: int, status: Status | None = None
) -> list[int]:
    """The ids of a User's Submissions, drafts included, the latest first."""
    query = select(t.submission.c.id).where(t.submission.c.submitter_id == submitter_id)
    if status is not None:
        query = query.where(t.submission.c.status == status.value)
    return list(await connection.scalars(query.order_by(t.submission.c.id.desc())))


async def drafts_of(connection: AsyncConnection, submitter_id: int) -> list[Submission]:
    """The User's open drafts, oldest first (without their rounds, log, or notes)."""
    rows = await connection.execute(
        select(t.submission)
        .where(
            t.submission.c.submitter_id == submitter_id,
            t.submission.c.status == Status.DRAFT.value,
        )
        .order_by(t.submission.c.id)
    )
    return [
        Submission(
            id=row.id,
            submitter_id=row.submitter_id,
            target_kind=Kind(row.target_kind),
            target_id=row.target_id,
            base_revisions=tuple(row.base_revisions),
            status=Status.DRAFT,
            created_at=row.created_at,
            last_autosave_at=row.last_autosave_at,
        )
        for row in rows
    ]
