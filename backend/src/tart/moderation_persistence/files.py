"""The uploads a Submission's content holds: which ones it holds, copies for a retry or a
conversion, and the deletion of the files of drafts and of rejected or retracted Submissions.

The content of a Submission names an upload by the `file` of its Documentation items. A
draft's files are private to the Submitter and the Moderators (the media API serves a
rendition publicly only for an approved Documentation item).
"""

import copy
import uuid
from datetime import datetime
from functools import partial

from sqlalchemy import delete, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from tart.archive.codec import Json
from tart.media import Rendition, original_key, rendition_key
from tart.media.tables import READY, upload
from tart.media.uploads import delete_objects
from tart.moderation import ModerationError, Submission, uploaded_files
from tart.moderation_persistence.tables import submission_upload
from tart.storage import Area, ObjectNotFoundError, Storage


def _upload_id(file: str) -> uuid.UUID:
    try:
        return uuid.UUID(file)
    except ValueError:
        raise ModerationError("moderation.file_not_found") from None


def held_files(submission: Submission) -> set[str]:
    """The uploads of the working copy and of every round."""
    snapshots = [submission.working_copy, *(round_.snapshot for round_ in submission.rounds)]
    return {file for snapshot in snapshots for file in uploaded_files(snapshot)}


async def sync_links(connection: AsyncConnection, submission: Submission) -> None:
    """Make the Submission hold exactly the uploads its content names.

    Every file must be an upload of the Submitter that was not deleted: no one attaches,
    and so no one deletes or exposes, another User's file.
    """
    wanted = {_upload_id(file) for file in held_files(submission)}
    if wanted:
        found = set(
            await connection.scalars(
                select(upload.c.id).where(
                    upload.c.id.in_(wanted),
                    upload.c.user_id == submission.submitter_id,
                    upload.c.deleted_at.is_(None),
                )
            )
        )
        if found != wanted:
            raise ModerationError("moderation.file_not_found")
    await connection.execute(
        delete(submission_upload).where(
            submission_upload.c.submission_id == submission.id,
            submission_upload.c.upload_id.not_in(wanted),
        )
    )
    if wanted:
        await connection.execute(
            pg_insert(submission_upload)
            .values([{"submission_id": submission.id, "upload_id": each} for each in wanted])
            .on_conflict_do_nothing()
        )


async def linked(connection: AsyncConnection, submission_id: int) -> list[uuid.UUID]:
    return list(
        await connection.scalars(
            select(submission_upload.c.upload_id).where(
                submission_upload.c.submission_id == submission_id
            )
        )
    )


async def _copy_upload(
    connection: AsyncConnection, storage: Storage, source: uuid.UUID, user_id: int, now: datetime
) -> uuid.UUID | None:
    """A new upload of the same bytes, or `None` when the source is gone or not ready."""
    row = (
        await connection.execute(
            select(upload).where(
                upload.c.id == source,
                upload.c.user_id == user_id,
                upload.c.status == READY,
                upload.c.deleted_at.is_(None),
            )
        )
    ).first()
    if row is None:
        return None
    new_id = uuid.uuid4()
    try:
        for key_of in (original_key, *(partial(rendition_key, rendition=r) for r in Rendition)):
            try:
                async with storage.get(Area.PERMANENT, key_of(str(source))) as stream:
                    await storage.put(Area.PERMANENT, key_of(str(new_id)), stream)
            except ObjectNotFoundError:
                if key_of is original_key:
                    raise
    except ObjectNotFoundError:
        await delete_objects(storage, str(new_id))
        return None
    await connection.execute(
        insert(upload).values(
            id=new_id,
            user_id=user_id,
            status=READY,
            format=row.format,
            size=row.size,
            renditions=row.renditions,
            created_at=now,
            processed_at=now,
        )
    )
    return new_id


async def copy_files(
    connection: AsyncConnection, storage: Storage, snapshot: Json, user_id: int, now: datetime
) -> tuple[Json, list[uuid.UUID]]:
    """The snapshot with each file copied to a new upload of the User, for a retry or a
    conversion, which must keep their files after the original's media are deleted. A file
    that is gone is left out of its item: the Submitter uploads it again.

    Returns the new snapshot and the new uploads.
    """
    new = copy.deepcopy(snapshot)
    created: list[uuid.UUID] = []
    if not isinstance(new, dict) or not isinstance(new.get("operations"), list):
        return new, created
    try:
        for operation in new["operations"]:  # type: ignore[union-attr]
            record = operation.get("record") if isinstance(operation, dict) else None
            if not (
                isinstance(record, dict)
                and operation.get("op") == "create"
                and operation.get("kind") == "documentation_item"
                and isinstance(record.get("file"), str)
            ):
                continue
            try:
                source = uuid.UUID(record["file"])
            except ValueError:
                record["file"] = None
                continue
            copied = await _copy_upload(connection, storage, source, user_id, now)
            if copied is not None:
                created.append(copied)
            record["file"] = str(copied) if copied is not None else None
    except BaseException:
        for each in created:
            await delete_objects(storage, str(each))
        raise
    return new, created


async def delete_uploads(
    engine: AsyncEngine, storage: Storage, upload_ids: list[uuid.UUID]
) -> None:
    """Delete the uploads of a deleted draft: their objects, then their rows."""
    for each in upload_ids:
        await delete_objects(storage, str(each))
    async with engine.begin() as connection:
        await connection.execute(delete(upload).where(upload.c.id.in_(upload_ids)))


async def mark_deleted(
    engine: AsyncEngine, storage: Storage, upload_ids: list[uuid.UUID], now: datetime
) -> None:
    """Delete the files of a rejected or retracted Submission; each upload row stays as the
    placeholder that keeps its metadata."""
    for each in upload_ids:
        await delete_objects(storage, str(each))
    async with engine.begin() as connection:
        await connection.execute(
            update(upload).where(upload.c.id.in_(upload_ids)).values(deleted_at=now)
        )
