"""The moderation use cases over the PostgreSQL adapter.

Each one loads the Submission with its row locked, applies the domain rule, and stores
the result in the caller's transaction. A Moderator's role is read from the database on
every call, so revoking it takes effect on the next request.

    submission = await decide(connection, 7, user_id, Verdict.REJECT, version, rules, now, ...)
    approval = await approve(connection, 7, user_id, version, rules, archive_rules, now)

Approval is the only use case that changes an Archive record: it records the decision and
calls the archive's write operation in one transaction (ADR 0002).
"""

from dataclasses import dataclass, replace
from datetime import datetime

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncConnection

from tart import moderation
from tart.archive.changeset import Merge, Unmerge
from tart.archive.codec import Json
from tart.archive.revisions import Provenance, Revision
from tart.archive.rules import InstanceRules
from tart.archive.write import apply_changeset
from tart.archive_persistence import PostgresArchiveStore
from tart.auth.tables import MODERATOR, user_role
from tart.moderation import (
    Actor,
    Content,
    Decision,
    DecisionRules,
    ModerationError,
    Reason,
    Status,
    Submission,
    Verdict,
)
from tart.moderation_persistence import archive_access, store


async def actor_for(connection: AsyncConnection, user_id: int) -> Actor:
    held = await connection.scalar(
        select(exists().where(user_role.c.user_id == user_id, user_role.c.role == MODERATOR))
    )
    return Actor.user(user_id, moderator=bool(held))


async def _locked(connection: AsyncConnection, submission_id: int) -> Submission:
    submission = await store.load(connection, submission_id, lock=True)
    if submission is None:
        raise ModerationError("moderation.unknown_submission")
    return submission


async def autosave(
    connection: AsyncConnection, submission_id: int, user_id: int, content: Json, now: datetime
) -> Submission:
    submission = await _locked(connection, submission_id)
    actor = await actor_for(connection, user_id)
    updated = moderation.save_working_copy(submission, actor, now, content)
    await store.save(connection, updated)
    return updated


async def _outdated_reasons(
    connection: AsyncConnection, submission: Submission, content: Content
) -> tuple[Reason, ...]:
    """Why the content, written against the Submission's Base revision, is Outdated now."""
    if submission.target_id is None:
        return ()
    if (merging := moderation.merge_of(content)) is not None:
        return await _merge_outdated(connection, submission, merging)
    state = await archive_access.target_state(connection, submission.target_id)
    if state is None:
        raise ModerationError("moderation.unknown_target")
    changes = await archive_access.changes_since(
        connection, submission.target_id, submission.target_kind, submission.base_revisions[0]
    )
    return moderation.outdated_reasons(submission, content, state, changes)


async def _merge_states(
    connection: AsyncConnection, merging: Merge | Unmerge
) -> tuple[moderation.TargetState, moderation.TargetState]:
    """The state of the folded record and of the survivor. An Unmerge expects the folded one
    to be merged into the survivor, so that is not what makes it not public."""
    source = await archive_access.target_state(connection, merging.source)
    into = await archive_access.target_state(connection, merging.into)
    if source is None or into is None:
        raise ModerationError("moderation.unknown_target")
    if isinstance(merging, Unmerge) and source.merged_into == merging.into:
        source = replace(source, merged_into=None)
    return source, into


async def _merge_outdated(
    connection: AsyncConnection, submission: Submission, merging: Merge | Unmerge
) -> tuple[Reason, ...]:
    """Outdated for a Merge, Duplicate retirement, or Unmerge (ADR 0018): either record has
    a Revision newer than its Base revision, is not public, or has an open Notice."""
    states = await _merge_states(connection, merging)
    reasons = list(moderation.merge_outdated_reasons(submission.base_revisions, states))
    if isinstance(merging, Unmerge):
        merged_into = (await archive_access.target_state(connection, merging.source)).merged_into  # type: ignore[union-attr]
        if merged_into != merging.into:
            reasons.append(Reason.NOT_MERGED)
    return tuple(reasons)


async def _validate(
    connection: AsyncConnection,
    submission: Submission,
    snapshot: Json,
    archive_rules: InstanceRules,
    now: datetime,
) -> Content:
    """The content of the snapshot, if it is a valid Submission against the current archive.

    Raises a `ModerationError` for the rules of the model and an `ArchiveRuleViolation`
    for the archive's own, found by applying the changeset and rolling it back.
    """
    content = moderation.decode_content(snapshot, submission.target_kind)
    moderation.check_content(submission, content)
    if await _outdated_reasons(connection, submission, content):
        raise ModerationError("moderation.outdated")
    provenance = Provenance(
        submission.id, submission.submitter_id, submission.submitter_id, now, now
    )
    await archive_access.dry_run(
        connection, moderation.materialize(content), provenance, archive_rules
    )
    return content


async def validate(
    connection: AsyncConnection,
    submission_id: int,
    snapshot: Json,
    archive_rules: InstanceRules,
    now: datetime,
) -> Content:
    """Validate a snapshot of the Submission without submitting it."""
    submission = await store.load(connection, submission_id)
    if submission is None:
        raise ModerationError("moderation.unknown_submission")
    return await _validate(connection, submission, snapshot, archive_rules, now)


async def submit(
    connection: AsyncConnection,
    submission_id: int,
    user_id: int,
    snapshot: Json,
    now: datetime,
    archive_rules: InstanceRules,
    *,
    note: str | None = None,
) -> Submission:
    """Submit, revise, or resubmit; the snapshot must validate against the current archive."""
    submission = await _locked(connection, submission_id)
    actor = await actor_for(connection, user_id)
    updated = moderation.submit(submission, actor, now, snapshot, note=note)
    await _validate(connection, submission, snapshot, archive_rules, now)
    await store.save(connection, updated)
    return updated


async def outdated(connection: AsyncConnection, submission_id: int) -> tuple[Reason, ...]:
    """Why the last submitted round is Outdated; empty when it is not."""
    submission = await _locked(connection, submission_id)
    if not submission.rounds:
        return ()
    content = moderation.decode_content(submission.rounds[-1].snapshot, submission.target_kind)
    return await _outdated_reasons(connection, submission, content)


async def rebase(
    connection: AsyncConnection, submission_id: int, user_id: int, now: datetime
) -> Submission:
    """Open the editor on an edit: move its Base revision to the current Revision.

    The working copy becomes the Submitter's copy (or the last round) over the current
    Revision, with each overlapping operation as a conflict to keep or drop. A merged
    target moves the edit to the surviving record; a withdrawn one cannot be rebased.
    """
    submission = await _locked(connection, submission_id)
    actor = await actor_for(connection, user_id)
    raw = submission.working_copy
    if raw is None and submission.rounds:
        raw = submission.rounds[-1].snapshot
    if submission.target_id is None or raw is None:
        raise ModerationError("moderation.cannot_rebase")
    content = moderation.decode_content(raw, submission.target_kind)
    if (merging := moderation.merge_of(content)) is not None:
        return await _rebase_merge(connection, submission, actor, now, content, merging)
    state = await archive_access.target_state(connection, submission.target_id)
    if state is not None and state.merged_into is not None:
        state = await archive_access.target_state(connection, state.merged_into)
    if state is None:
        raise ModerationError("moderation.unknown_target")
    changes = await archive_access.changes_since(
        connection, state.record_id, submission.target_kind, submission.base_revisions[0]
    )
    rebased = moderation.rebase(submission, content, state, changes)
    updated = moderation.rebase_working_copy(
        submission,
        actor,
        now,
        target_id=rebased.target_id,
        base_revision=rebased.base_revision,
        content=moderation.encode_content(rebased.content),
    )
    await store.save(connection, updated)
    return updated


async def _rebase_merge(
    connection: AsyncConnection,
    submission: Submission,
    actor: Actor,
    now: datetime,
    content: Content,
    merging: Merge | Unmerge,
) -> Submission:
    """Rebase a Merge, Duplicate retirement, or Unmerge onto the current Revisions of both
    records; the references to rewrite are recomputed whenever they are listed."""
    states = await _merge_states(connection, merging)
    changes = await archive_access.changes_since(
        connection, merging.into, submission.target_kind, submission.base_revisions[1]
    )
    rebased = moderation.rebase_merge(content, merging.into, states, changes)
    updated = moderation.rebase_working_copy(
        submission,
        actor,
        now,
        target_id=merging.source,
        base_revisions=rebased.base_revisions,
        content=moderation.encode_content(rebased.content),
    )
    await store.save(connection, updated)
    return updated


async def retract(
    connection: AsyncConnection, submission_id: int, user_id: int, now: datetime
) -> Submission:
    submission = await _locked(connection, submission_id)
    actor = await actor_for(connection, user_id)
    updated = moderation.retract(submission, actor, now)
    await store.save(connection, updated)
    return updated


async def decide(
    connection: AsyncConnection,
    submission_id: int,
    user_id: int,
    verdict: Verdict,
    expected_version: int,
    rules: DecisionRules,
    now: datetime,
    *,
    decision: Decision | None = None,
) -> Submission:
    """Reject or request changes. Approving writes the archive, so it goes through `approve`."""
    if verdict is Verdict.APPROVE:
        raise ModerationError("moderation.approval_writes_archive")
    submission = await _locked(connection, submission_id)
    actor = await actor_for(connection, user_id)
    updated = moderation.decide(
        submission,
        actor,
        verdict,
        now,
        expected_version=expected_version,
        rules=rules,
        decision=decision,
    )
    await store.save(connection, updated)
    return updated


@dataclass(frozen=True)
class Approval:
    submission: Submission
    revisions: tuple[Revision, ...]
    """One per record the Submission created or changed."""


async def approve(
    connection: AsyncConnection,
    submission_id: int,
    user_id: int,
    expected_version: int,
    rules: DecisionRules,
    archive_rules: InstanceRules,
    now: datetime,
) -> Approval:
    """Approve the last submitted round: the decision and the archive write, atomically.

    An Outdated Submission is refused. The changeset is applied to the current Revisions,
    so an edit whose Base revision is behind keeps the changes approved since. Everything
    is stored in a savepoint of the caller's transaction, so a failure leaves neither a
    Revision, a record, nor a changed Submission, even if the caller commits afterwards.
    """
    submission = await _locked(connection, submission_id)
    actor = await actor_for(connection, user_id)
    updated = moderation.decide(
        submission,
        actor,
        Verdict.APPROVE,
        now,
        expected_version=expected_version,
        rules=rules,
    )
    content = moderation.decode_content(submission.rounds[-1].snapshot, submission.target_kind)
    moderation.check_content(submission, content)
    if await _outdated_reasons(connection, submission, content):
        raise ModerationError("moderation.outdated")
    assert submission.first_submitted_at is not None
    provenance = Provenance(
        submission.id, submission.submitter_id, user_id, submission.first_submitted_at, now
    )
    async with connection.begin_nested():
        revisions = await apply_changeset(
            PostgresArchiveStore(connection),
            moderation.materialize(content),
            provenance,
            archive_rules,
        )
        await store.save(connection, updated)
    return Approval(updated, revisions)


async def add_note(
    connection: AsyncConnection, submission_id: int, user_id: int, text: str, now: datetime
) -> Submission:
    submission = await _locked(connection, submission_id)
    actor = await actor_for(connection, user_id)
    updated = moderation.add_note(submission, actor, now, text)
    await store.save(connection, updated)
    return updated


async def expire_unanswered(
    connection: AsyncConnection, now: datetime, expiry_days: int
) -> list[int]:
    """Retract the `changes requested` Submissions left without a response; their ids."""
    expired: list[int] = []
    for submission_id in await store.changes_requested(connection):
        submission = await _locked(connection, submission_id)
        deadline = moderation.expiry_deadline(submission, expiry_days)
        if submission.status is Status.CHANGES_REQUESTED and deadline and now >= deadline:
            await store.save(connection, moderation.expire(submission, now, expiry_days))
            expired.append(submission_id)
    return expired
