"""Uploads from quarantine to stored objects: the processing job, the sweep, and who may
see a file (Foundations spec, 3. Storage and media pipeline).
"""

import asyncio
import uuid
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import Text, cast, exists, insert, select, update
from sqlalchemy import delete as delete_rows
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from tart.archive_persistence.tables import documentation_item
from tart.media import (
    Rendition,
    original_key,
    quarantine_key,
    rendition_key,
)
from tart.media.processing import Processed, process
from tart.media.tables import PROCESSING, READY, REJECTED, upload
from tart.moderation_persistence.tables import submission_upload
from tart.storage import Area, ObjectExistsError, ObjectNotFoundError, Storage

ABANDONED_AFTER = timedelta(hours=24)
"""An upload never attached is deleted this long after it was uploaded; its EXIF
suggestions go at the same age either way."""


@dataclass(frozen=True)
class Upload:
    id: uuid.UUID
    user_id: int
    status: str
    error: str | None
    format: str | None
    renditions: dict[str, list[int]] | None
    suggestions: dict[str, object] | None
    deleted_at: datetime | None = None
    """When its files were deleted with a rejected or retracted Submission's media."""


async def create(connection: AsyncConnection, user_id: int, now: datetime) -> uuid.UUID:
    upload_id = uuid.uuid4()
    await connection.execute(
        insert(upload).values(id=upload_id, user_id=user_id, status=PROCESSING, created_at=now)
    )
    return upload_id


async def received(connection: AsyncConnection, upload_id: uuid.UUID, size: int) -> None:
    await connection.execute(update(upload).where(upload.c.id == upload_id).values(size=size))


async def discard(connection: AsyncConnection, upload_id: uuid.UUID) -> None:
    """Forget an upload refused while it was being received; nothing of it was stored."""
    await connection.execute(delete_rows(upload).where(upload.c.id == upload_id))


async def read(connection: AsyncConnection, upload_id: uuid.UUID) -> Upload | None:
    row = (await connection.execute(select(upload).where(upload.c.id == upload_id))).first()
    if row is None:
        return None
    return Upload(
        id=row.id,
        user_id=row.user_id,
        status=row.status,
        error=row.error,
        format=row.format,
        renditions=row.renditions,
        suggestions=row.suggestions,
        deleted_at=row.deleted_at,
    )


def _in_record():
    """Uploads that an archive record holds."""
    return exists().where(documentation_item.c.file == cast(upload.c.id, Text))


def _attached():
    """Uploads that an archive record holds, or that a Submission's content names (the
    draft's and the rounds'): the sweep leaves both alone."""
    return _in_record() | exists().where(submission_upload.c.upload_id == upload.c.id)


async def is_public(connection: AsyncConnection, upload_id: uuid.UUID) -> bool:
    """Whether the upload is the file of an approved Documentation item.

    Archive records hold only approved data; a withdrawn item stops being public once
    Withdrawals exist (Rights and legal actions spec).
    """
    query = select(_in_record()).where(upload.c.id == upload_id)
    return bool((await connection.execute(query)).scalar())


async def process_upload(
    engine: AsyncEngine, storage: Storage, upload_id: uuid.UUID, cap: int, now: datetime
) -> None:
    """The worker job's work: process the quarantined file, store what it gives, and
    delete the quarantined object. A refused file is deleted at once, and only its error
    code stays."""
    try:
        async with storage.get(Area.QUARANTINE, quarantine_key(str(upload_id))) as stream:
            data = b"".join([chunk async for chunk in stream])
    except ObjectNotFoundError:
        return  # swept, or processed already
    result = await asyncio.to_thread(process, data, cap)
    if isinstance(result, Processed):
        await _store(storage, str(upload_id), result)
        values = {
            "status": READY,
            "format": result.format.value,
            "renditions": {r.value: [w, h] for r, (_, w, h) in result.renditions.items()},
            "suggestions": {
                "observed_date": result.suggestions.observed_date,
                "point": list(result.suggestions.point) if result.suggestions.point else None,
            },
        }
    else:
        values = {"status": REJECTED, "error": result.code}
    async with engine.begin() as connection:
        await connection.execute(
            update(upload)
            .where(upload.c.id == upload_id, upload.c.status == PROCESSING)
            .values(processed_at=now, **values)
        )
    await storage.delete(Area.QUARANTINE, quarantine_key(str(upload_id)))


async def _store(storage: Storage, upload_id: str, result: Processed) -> None:
    objects = [(original_key(upload_id), result.original)] + [
        (rendition_key(upload_id, rendition), data)
        for rendition, (data, _, _) in result.renditions.items()
    ]
    for key, data in objects:
        # An object stored by an earlier run of this job holds the same bytes.
        with suppress(ObjectExistsError):
            await storage.put(Area.PERMANENT, key, _chunks(data))


async def _chunks(data: bytes):
    yield data


async def sweep(engine: AsyncEngine, storage: Storage, now: datetime) -> None:
    """Delete the uploads never attached, 24 hours after upload, with their objects; and
    drop every upload's EXIF suggestions at the same age."""
    cutoff = now - ABANDONED_AFTER
    async with engine.begin() as connection:
        abandoned = (
            await connection.scalars(
                select(upload.c.id).where(upload.c.created_at <= cutoff, ~_attached())
            )
        ).all()
    for upload_id in abandoned:
        await delete_objects(storage, str(upload_id))
        async with engine.begin() as connection:
            await connection.execute(delete_rows(upload).where(upload.c.id == upload_id))
    async with engine.begin() as connection:
        await connection.execute(
            update(upload)
            .where(upload.c.created_at <= cutoff, upload.c.suggestions.is_not(None))
            .values(suggestions=None)
        )


async def delete_objects(storage: Storage, upload_id: str) -> None:
    await storage.delete(Area.QUARANTINE, quarantine_key(upload_id))
    await storage.delete(Area.PERMANENT, original_key(upload_id))
    for rendition in Rendition:
        await storage.delete(Area.PERMANENT, rendition_key(upload_id, rendition))
