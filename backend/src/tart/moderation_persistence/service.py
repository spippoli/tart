"""The moderation use cases over the PostgreSQL adapter.

Each one loads the Submission with its row locked, applies the domain rule, and stores
the result in the caller's transaction. A Moderator's role is read from the database on
every call, so revoking it takes effect on the next request.

    submission = await decide(connection, 7, user_id, Verdict.REJECT, version, rules, now, ...)
    approval = await approve(connection, 7, user_id, version, rules, archive_rules, now)

Approval is the only use case that changes an Archive record: it records the decision and
calls the archive's write operation in one transaction (ADR 0002).
"""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncConnection

from tart import moderation
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
    state = await archive_access.target_state(connection, submission.target_id)
    if state is None:
        raise ModerationError("moderation.unknown_target")
    changes = await archive_access.changes_since(
        connection, submission.target_id, submission.target_kind, submission.base_revisions[0]
    )
    return moderation.outdated_reasons(submission, content, state, changes)


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
