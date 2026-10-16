"""The contributor's use cases: start a draft, autosave, submit, delete, start again, and
convert into documentation (contribution spec, Lifecycle, Rate limits, Terms of use).

They add what the API needs around `service`: the terms, the per-User limits, and the
uploads a Submission holds. Each works in the caller's transaction; a refusal raises, so
the caller's rollback leaves the draft and its autosaved content as they were.
"""

import uuid
from dataclasses import replace
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from tart import moderation, rate_limits
from tart.archive.changeset import AddItem, Create
from tart.archive.codec import Json
from tart.archive.records import Artwork, DocumentationItem, Kind, New
from tart.archive.rules import InstanceRules
from tart.archive_persistence import tables as archive_tables
from tart.moderation import (
    Actor,
    Content,
    Event,
    ModerationError,
    Status,
    Submission,
)
from tart.moderation.validation import CREATABLE
from tart.moderation_persistence import archive_access, files, limits, service, store, terms
from tart.storage import Storage


async def _lock_user(connection: AsyncConnection, user_id: int) -> None:
    await connection.execute(
        select(func.pg_advisory_xact_lock(func.hashtextextended(f"drafts:{user_id}", 0)))
    )


async def _check_draft_limit(
    connection: AsyncConnection, actor: Actor, now: datetime, expiry_days: int
) -> None:
    """At most 20 open drafts at once; Moderators are exempt.

    Nothing frees a place at a fixed time, so the wait is the time until the system next
    deletes one of the User's drafts: its earliest deadline.
    """
    if actor.moderator:
        return
    assert actor.user_id is not None
    await _lock_user(connection, actor.user_id)
    drafts = await store.drafts_of(connection, actor.user_id)
    if len(drafts) >= limits.OPEN_DRAFTS:
        earliest = min(moderation.draft_deadline(draft, expiry_days) for draft in drafts)
        raise limits.LimitReached(limits.DRAFTS_LIMITED, max(earliest - now, timedelta(0)))


async def _kind_of(connection: AsyncConnection, record_id: int) -> Kind | None:
    kind = await connection.scalar(
        select(archive_tables.record.c.kind).where(archive_tables.record.c.id == record_id)
    )
    return Kind(kind) if kind is not None else None


async def _editable_target(
    connection: AsyncConnection, kind: Kind | None, target_id: int
) -> tuple[Kind, int]:
    """The kind and latest Revision of a record an edit may start from."""
    state = await archive_access.target_state(connection, target_id)
    actual = await _kind_of(connection, target_id)
    if state is None or actual is None or (kind is not None and kind is not actual):
        raise ModerationError("moderation.unknown_target")
    if state.withdrawn:
        raise ModerationError("moderation.target_withdrawn")
    if state.merged_into is not None:
        raise ModerationError("moderation.target_merged")
    assert state.revision_id is not None
    return actual, state.revision_id


async def start(
    connection: AsyncConnection,
    user_id: int,
    kind: Kind | None,
    target_id: int | None,
    now: datetime,
    *,
    expiry_days: int,
) -> Submission:
    """Start a contribution as a draft: a new record of a creatable kind, or an edit of a
    record, which stores the record's current Revision as its Base revision."""
    actor = await service.actor_for(connection, user_id)
    base_revisions: tuple[int, ...] = ()
    if target_id is None:
        if kind not in CREATABLE:
            raise ModerationError("moderation.target_not_creatable")
    else:
        kind, revision = await _editable_target(connection, kind, target_id)
        base_revisions = (revision,)
    assert kind is not None
    await _check_draft_limit(connection, actor, now, expiry_days)
    return await store.create_draft(
        connection, user_id, kind, now, target_id=target_id, base_revisions=base_revisions
    )


async def autosave(
    connection: AsyncConnection, submission_id: int, user_id: int, content: Json, now: datetime
) -> Submission:
    """Store the Submitter's working copy. Nothing is validated except what protects the
    store: an object, at most 20 uploaded Documentation items, and files that are the
    Submitter's own."""
    if not isinstance(content, dict):
        raise ModerationError("moderation.malformed_content")
    moderation.check_file_count(content)
    updated = await service.autosave(connection, submission_id, user_id, content, now)
    await files.sync_links(connection, updated)
    return updated


async def submit(
    connection: AsyncConnection,
    submission_id: int,
    user_id: int,
    content: Json,
    now: datetime,
    archive_rules: InstanceRules,
    *,
    terms_version: int,
    accept_terms: bool,
    key: bytes,
    note: str | None = None,
) -> Submission:
    """Submit a draft, revise a `submitted` Submission, or resubmit after changes were
    requested.

    The User must have accepted the current terms: the request carries the acceptance when
    the Review step asked for it. A submission or resubmission counts against the User's 20
    per 24 hours (a revision does not, and Moderators are never limited); a refusal rolls
    the submission back. Submitting a conversion retracts the original.
    """
    if content is None:
        existing = await store.load(connection, submission_id)
        if existing is None:
            raise ModerationError("moderation.unknown_submission")
        content = existing.working_copy
        if content is None:
            raise ModerationError("moderation.malformed_content")
    moderation.check_file_count(content)
    actor = await service.actor_for(connection, user_id)
    accepted = await terms.accepted_version(connection, user_id)
    if terms.acceptance_needed(accepted, terms_version):
        if not accept_terms:
            raise ModerationError("moderation.terms_not_accepted")
        await terms.accept(connection, user_id, terms_version, now)
    updated = await service.submit(
        connection, submission_id, user_id, content, now, archive_rules, note=note
    )
    await files.sync_links(connection, updated)
    event = updated.log[-1].event
    if event in {Event.SUBMITTED, Event.RESUBMITTED} and not actor.moderator:
        wait = await rate_limits.hit(connection, [(limits.SUBMISSIONS, str(user_id))], now, key)
        if wait is not None:
            raise limits.LimitReached(limits.SUBMISSIONS_LIMITED, wait)
    if event is Event.SUBMITTED and updated.converts is not None:
        original = await store.load(connection, updated.converts, lock=True)
        if original is not None and original.status is Status.CHANGES_REQUESTED:
            await store.save(connection, moderation.convert(original, now, updated.id))
    return updated


async def delete_draft(
    engine: AsyncEngine, storage: Storage, submission_id: int, user_id: int
) -> None:
    """Delete a draft with its media; only its Submitter may."""
    async with engine.begin() as connection:
        submission = await store.load(connection, submission_id, lock=True)
        if submission is None:
            raise ModerationError("moderation.unknown_submission")
        actor = await service.actor_for(connection, user_id)
        if actor.user_id != submission.submitter_id:
            raise ModerationError("moderation.not_submitter")
        if submission.status is not Status.DRAFT:
            raise ModerationError("moderation.invalid_transition")
        uploads = await files.linked(connection, submission_id)
    await discard_draft(engine, storage, submission_id, uploads)


async def discard_draft(
    engine: AsyncEngine, storage: Storage, submission_id: int, uploads: list[uuid.UUID]
) -> None:
    """Delete the draft's files, then the draft and its upload rows."""
    if uploads:
        await files.delete_uploads(engine, storage, uploads)
    async with engine.begin() as connection:
        await store.delete_draft(connection, submission_id)


async def start_again(
    connection: AsyncConnection,
    storage: Storage,
    submission_id: int,
    user_id: int,
    now: datetime,
    *,
    expiry_days: int,
) -> Submission:
    """ "Start again from this": a new draft pre-filled from the last round of a rejected or
    retracted Submission, with its files copied and both Submissions linked.

    An edit is rebased onto the target's current Revision (a withdrawn target cannot be).
    """
    original = await store.load(connection, submission_id, lock=True)
    if original is None:
        raise ModerationError("moderation.unknown_submission")
    actor = await service.actor_for(connection, user_id)
    moderation.check_can_start_again(original, actor)
    snapshot = original.rounds[-1].snapshot if original.rounds else None
    if snapshot is None:
        raise ModerationError("moderation.cannot_start_again")
    await _check_draft_limit(connection, actor, now, expiry_days)
    content, _ = await files.copy_files(connection, storage, snapshot, user_id, now)
    draft = await store.create_draft(
        connection,
        user_id,
        original.target_kind,
        now,
        target_id=original.target_id,
        base_revisions=original.base_revisions,
        retry_of=original.id,
        working_copy=content,
    )
    draft = moderation.link(draft, Event.RETRY_OF, actor, now, original.id)
    await store.save(connection, draft)
    await store.save(connection, moderation.link(original, Event.RETRIED_IN, actor, now, draft.id))
    await files.sync_links(connection, draft)
    if original.target_id is not None:
        # The rebase is not the Submitter's own entry: the draft stays never edited.
        rebased = await service.rebase(connection, draft.id, user_id, now)
        draft = replace(rebased, last_autosave_at=None)
        await store.save(connection, draft)
    return draft


def _documentation_content(content: Content, target_id: int) -> Content:
    """What a conversion keeps of a new Artwork's content: its Documentation items, now
    about the existing Artwork, and its History events; its fields, Attributions, and
    Location are dropped."""
    artworks = {
        operation.ref
        for operation in content.operations
        if isinstance(operation, Create) and isinstance(operation.record, Artwork)
    }
    kept = []
    for operation in content.operations:
        if isinstance(operation, Create) and isinstance(operation.record, DocumentationItem):
            record = operation.record
            about = tuple(target_id if ref in artworks else ref for ref in record.artworks)
            about = tuple(ref for ref in about if not isinstance(ref, New))
            kept.append(
                Create(operation.ref, replace(record, artworks=about, location=None))  # type: ignore[arg-type]
            )
        elif isinstance(operation, Create) and isinstance(operation.record, Artwork):
            kept += [
                AddItem(target_id, "history_events", event)
                for event in operation.record.history_events
            ]
    return Content(tuple(kept))


async def convert(
    connection: AsyncConnection,
    storage: Storage,
    submission_id: int,
    user_id: int,
    target_id: int,
    now: datetime,
    *,
    expiry_days: int,
) -> Submission:
    """Convert a `changes requested` new Artwork, a duplicate of an existing one, into a
    draft Submission that adds its documentation to that Artwork.

    The original stays as it is while the draft is open; submitting the draft retracts it.
    """
    original = await store.load(connection, submission_id, lock=True)
    if original is None:
        raise ModerationError("moderation.unknown_submission")
    actor = await service.actor_for(connection, user_id)
    moderation.check_can_convert(original, actor)
    if original.target_id is not None or original.target_kind is not Kind.ARTWORK:
        raise ModerationError("moderation.cannot_convert")
    snapshot = original.rounds[-1].snapshot if original.rounds else None
    if snapshot is None:
        raise ModerationError("moderation.cannot_convert")
    kind, revision = await _editable_target(connection, Kind.ARTWORK, target_id)
    await _check_draft_limit(connection, actor, now, expiry_days)
    carried = moderation.encode_content(
        _documentation_content(moderation.decode_content(snapshot, original.target_kind), target_id)
    )
    content, _ = await files.copy_files(connection, storage, carried, user_id, now)
    draft = await store.create_draft(
        connection,
        user_id,
        kind,
        now,
        target_id=target_id,
        base_revisions=(revision,),
        converts=original.id,
        working_copy=content,
    )
    draft = moderation.link(draft, Event.CONVERSION_OF, actor, now, original.id)
    await store.save(connection, draft)
    await files.sync_links(connection, draft)
    return draft
