"""The worker's retention of contributions (contribution spec, Lifecycle).

    await sweep(engine, storage, now, draft_expiry_days)

Run by the hourly sweep. It deletes the drafts the clocks have run out for, with their media;
retracts the `changes requested` Submissions left unanswered; deletes the media of rejected
and retracted Submissions 30 days after their final transition, leaving the uploads' rows as
placeholders that keep their metadata; and reduces them to a stub after twelve months. These
are ordinary retention, not erasures: none is recorded in the Erasure log.
"""

import logging
from datetime import datetime, timedelta

from sqlalchemy import and_, exists, or_, select
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from tart import moderation
from tart.media.tables import upload
from tart.moderation import ModerationError, Status
from tart.moderation.lifecycle import MEDIA_RETENTION, NEVER_EDITED_AFTER, STUB_AFTER
from tart.moderation.model import FINAL_EVENTS
from tart.moderation_persistence import contribution, files, service, store
from tart.moderation_persistence import tables as t
from tart.storage import Storage

logger = logging.getLogger(__name__)

_CLOSED = (Status.REJECTED.value, Status.RETRACTED.value)


async def _drafts_due(connection: AsyncConnection, now: datetime, expiry_days: int) -> list[int]:
    """Drafts never edited 24 hours after creation, and drafts abandoned `expiry_days` after
    their last autosave."""
    return list(
        await connection.scalars(
            select(t.submission.c.id).where(
                t.submission.c.status == Status.DRAFT.value,
                or_(
                    and_(
                        t.submission.c.last_autosave_at.is_(None),
                        t.submission.c.created_at <= now - NEVER_EDITED_AFTER,
                    ),
                    t.submission.c.last_autosave_at <= now - timedelta(days=expiry_days),
                ),
            )
        )
    )


def _final_before(cutoff: datetime):
    """The rejected or retracted Submissions whose final transition is at or before `cutoff`."""
    final = (
        select(t.submission_log.c.at)
        .where(
            t.submission_log.c.submission_id == t.submission.c.id,
            t.submission_log.c.event.in_([event.value for event in FINAL_EVENTS]),
        )
        .scalar_subquery()
    )
    return and_(t.submission.c.status.in_(_CLOSED), final <= cutoff)


async def _delete_drafts(
    engine: AsyncEngine, storage: Storage, now: datetime, expiry_days: int
) -> list[int]:
    async with engine.connect() as connection:
        due = await _drafts_due(connection, now, expiry_days)
    deleted = []
    for submission_id in due:
        async with engine.connect() as connection:
            uploads = await files.linked(connection, submission_id)
        await contribution.discard_draft(engine, storage, submission_id, uploads)
        deleted.append(submission_id)
    return deleted


async def _expire_unanswered(engine: AsyncEngine, now: datetime, expiry_days: int) -> list[int]:
    async with engine.begin() as connection:
        return await service.expire_unanswered(connection, now, expiry_days)


async def _delete_media(engine: AsyncEngine, storage: Storage, now: datetime) -> list[int]:
    held = exists().where(
        t.submission_upload.c.submission_id == t.submission.c.id,
        t.submission_upload.c.upload_id == upload.c.id,
        upload.c.deleted_at.is_(None),
    )
    async with engine.connect() as connection:
        candidates = list(
            await connection.scalars(
                select(t.submission.c.id).where(_final_before(now - MEDIA_RETENTION), held)
            )
        )
    done = []
    for submission_id in candidates:
        async with engine.connect() as connection:
            submission = await store.load(connection, submission_id)
            assert submission is not None
            if not moderation.media_deletion_due(submission, now):
                continue
            ids = [
                each
                for each in await files.linked(connection, submission_id)
                if await connection.scalar(
                    select(upload.c.deleted_at.is_(None)).where(upload.c.id == each)
                )
            ]
        await files.mark_deleted(engine, storage, ids, now)
        done.append(submission_id)
    return done


async def _labels(connection: AsyncConnection, submission_id: int) -> list[str]:
    submission = await store.load(connection, submission_id)
    assert submission is not None
    if not submission.rounds or submission.rounds[-1].snapshot is None:
        return []
    try:
        content = moderation.decode_content(submission.rounds[-1].snapshot, submission.target_kind)
        return [label.value for label in moderation.derive_labels(content)]
    except ModerationError:
        return []


async def _reduce_to_stubs(engine: AsyncEngine, now: datetime) -> list[int]:
    async with engine.connect() as connection:
        candidates = list(
            await connection.scalars(
                select(t.submission.c.id).where(
                    _final_before(now - STUB_AFTER), t.submission.c.reduced_at.is_(None)
                )
            )
        )
    reduced = []
    for submission_id in candidates:
        async with engine.begin() as connection:
            submission = await store.load(connection, submission_id, lock=True)
            assert submission is not None
            if not moderation.stub_due(submission, now):
                continue
            labels = await _labels(connection, submission_id)
            await store.save(connection, moderation.reduce_to_stub(submission, now, labels))
        reduced.append(submission_id)
    return reduced


async def sweep(engine: AsyncEngine, storage: Storage, now: datetime, expiry_days: int) -> None:
    drafts = await _delete_drafts(engine, storage, now, expiry_days)
    expired = await _expire_unanswered(engine, now, expiry_days)
    media = await _delete_media(engine, storage, now)
    stubs = await _reduce_to_stubs(engine, now)
    logger.info(
        "contribution retention: %d drafts deleted, %d Submissions expired, "
        "%d with media deleted, %d reduced to stubs",
        len(drafts),
        len(expired),
        len(media),
        len(stubs),
    )
