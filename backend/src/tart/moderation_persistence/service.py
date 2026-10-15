"""The moderation use cases over the PostgreSQL adapter.

Each one loads the Submission with its row locked, applies the domain rule, and stores
the result in the caller's transaction. A Moderator's role is read from the database on
every call, so revoking it takes effect on the next request.

    submission = await decide(connection, 7, user_id, Verdict.REJECT, version, rules, now, ...)
"""

from datetime import datetime

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncConnection

from tart import moderation
from tart.archive.codec import Json
from tart.auth.tables import MODERATOR, user_role
from tart.moderation import (
    Actor,
    Decision,
    DecisionRules,
    ModerationError,
    Status,
    Submission,
    Verdict,
)
from tart.moderation_persistence import store


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


async def submit(
    connection: AsyncConnection,
    submission_id: int,
    user_id: int,
    snapshot: Json,
    now: datetime,
    *,
    note: str | None = None,
) -> Submission:
    submission = await _locked(connection, submission_id)
    actor = await actor_for(connection, user_id)
    updated = moderation.submit(submission, actor, now, snapshot, note=note)
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
