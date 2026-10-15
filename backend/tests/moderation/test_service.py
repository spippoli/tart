"""The moderation use cases over PostgreSQL: roles read on every call, the first of two
concurrent decisions wins, and the aggregate survives a round trip. Every User is fictional."""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncConnection

from tart.archive import Kind
from tart.auth import operator
from tart.db import create_engine
from tart.moderation import (
    Decision,
    DecisionRules,
    Event,
    ModerationError,
    Status,
    Verdict,
)
from tart.moderation_persistence import service, store

NOW = datetime(2026, 9, 1, 10, 0, tzinfo=UTC)
RULES = DecisionRules(self_approval=False, reasons=frozenset({"incomplete", "duplicate"}))
REASON = Decision("incomplete", "The second photo does not show the stencil.")


def run[T](database: str, work: Callable[[AsyncConnection], Awaitable[T]]) -> T:
    """`work` in a transaction of its own, committed when it returns."""

    async def go() -> T:
        engine = create_engine(database)
        try:
            async with engine.begin() as connection:
                return await work(connection)
        finally:
            await engine.dispose()

    return asyncio.run(go())


async def user(connection: AsyncConnection, name: str, *, moderator: bool = False) -> int:
    created = await operator.create(connection, f"{name}@example.org", name.title(), "it", NOW)
    if moderator:
        await operator.grant_moderator(connection, created)
    return created.id


async def submitted(connection: AsyncConnection, submitter: int) -> int:
    draft = await store.create_draft(connection, submitter, Kind.ARTWORK, NOW)
    await service.submit(connection, draft.id, submitter, {"title": "First"}, NOW, note="Hello")
    return draft.id


def refusal(database: str, work: Callable[[AsyncConnection], Awaitable[object]]) -> str:
    with pytest.raises(ModerationError) as error:
        run(database, work)
    return error.value.code


def test_the_aggregate_survives_a_round_trip(migrated_database: str) -> None:
    async def work(connection: AsyncConnection) -> None:
        submitter = await user(connection, "ada")
        moderator = await user(connection, "gus", moderator=True)
        submission_id = await submitted(connection, submitter)
        await service.add_note(connection, submission_id, moderator, "Check the plate", NOW)
        await service.decide(
            connection,
            submission_id,
            moderator,
            Verdict.REQUEST_CHANGES,
            1,
            RULES,
            NOW + timedelta(hours=1),
            decision=REASON,
        )
        await service.autosave(
            connection, submission_id, submitter, {"title": "Second"}, NOW + timedelta(hours=2)
        )

        loaded = await store.load(connection, submission_id)

        assert loaded is not None
        assert loaded.status is Status.CHANGES_REQUESTED
        assert [(r.number, r.snapshot) for r in loaded.rounds] == [(1, {"title": "First"})]
        assert [(e.event, e.actor.user_id, e.message, e.reason) for e in loaded.log] == [
            (Event.SUBMITTED, submitter, "Hello", None),
            (Event.CHANGES_REQUESTED, moderator, REASON.text, "incomplete"),
        ]
        assert [n.text for n in loaded.notes] == ["Check the plate"]
        assert loaded.working_copy == {"title": "Second"}
        assert loaded.version == 2

    run(migrated_database, work)


# Acceptance criterion 30.
def test_a_user_without_the_role_cannot_decide_and_revocation_applies_on_the_next_call(
    migrated_database: str,
) -> None:
    async def setup(connection: AsyncConnection) -> tuple[int, int, int]:
        submitter = await user(connection, "ada")
        moderator = await user(connection, "gus", moderator=True)
        return submitter, moderator, await submitted(connection, submitter)

    submitter, moderator, submission_id = run(migrated_database, setup)

    async def as_submitter(connection: AsyncConnection) -> object:
        return await service.decide(
            connection, submission_id, submitter, Verdict.APPROVE, 1, RULES, NOW
        )

    assert refusal(migrated_database, as_submitter) == "moderation.forbidden"

    async def as_moderator(connection: AsyncConnection) -> object:
        return await service.decide(
            connection, submission_id, moderator, Verdict.APPROVE, 1, RULES, NOW
        )

    async def revoke(connection: AsyncConnection) -> None:
        await operator.revoke_moderator(connection, "gus@example.org")

    run(migrated_database, revoke)
    assert refusal(migrated_database, as_moderator) == "moderation.forbidden"


# Acceptance criterion 32.
def test_of_two_concurrent_decisions_only_the_first_is_applied(migrated_database: str) -> None:
    async def setup(connection: AsyncConnection) -> tuple[int, int, int]:
        submitter = await user(connection, "ada")
        first = await user(connection, "gus", moderator=True)
        second = await user(connection, "ivo", moderator=True)
        submission_id = await submitted(connection, submitter)
        return first, second, submission_id

    first, second, submission_id = run(migrated_database, setup)

    async def decide_as(moderator: int, verdict: Verdict) -> str:
        engine = create_engine(migrated_database)
        try:
            async with engine.begin() as connection:
                await service.decide(
                    connection,
                    submission_id,
                    moderator,
                    verdict,
                    1,
                    RULES,
                    NOW,
                    decision=None if verdict is Verdict.APPROVE else REASON,
                )
            return "applied"
        except ModerationError as error:
            return error.code
        finally:
            await engine.dispose()

    async def both() -> list[str]:
        return await asyncio.gather(
            decide_as(first, Verdict.APPROVE), decide_as(second, Verdict.REJECT)
        )

    outcomes = asyncio.run(both())

    assert sorted(outcomes) == ["applied", "moderation.already_decided"]

    async def log(connection: AsyncConnection) -> list[Event]:
        loaded = await store.load(connection, submission_id)
        assert loaded is not None
        return [entry.event for entry in loaded.log]

    events = run(migrated_database, log)
    assert len(events) == 2  # submitted, then exactly one decision


def test_unanswered_changes_requested_are_retracted_by_the_system(migrated_database: str) -> None:
    async def work(connection: AsyncConnection) -> None:
        submitter = await user(connection, "ada")
        moderator = await user(connection, "gus", moderator=True)
        waiting = await submitted(connection, submitter)
        answered = await submitted(connection, submitter)
        for submission_id in (waiting, answered):
            await service.decide(
                connection,
                submission_id,
                moderator,
                Verdict.REQUEST_CHANGES,
                1,
                RULES,
                NOW,
                decision=REASON,
            )
        await service.autosave(
            connection, answered, submitter, {"title": "Working"}, NOW + timedelta(days=60)
        )

        expired = await service.expire_unanswered(connection, NOW + timedelta(days=91), 90)

        assert expired == [waiting]
        loaded = await store.load(connection, waiting)
        assert loaded is not None
        assert loaded.status is Status.RETRACTED
        assert loaded.log[-1].event is Event.EXPIRED
        assert loaded.log[-1].actor.user_id is None
        still = await store.load(connection, answered)
        assert still is not None and still.status is Status.CHANGES_REQUESTED

    run(migrated_database, work)


def test_deleting_a_draft_leaves_nothing_and_leaves_a_submitted_submission(
    migrated_database: str,
) -> None:
    async def work(connection: AsyncConnection) -> None:
        submitter = await user(connection, "ada")
        draft = await store.create_draft(connection, submitter, Kind.ARTWORK, NOW)
        kept = await submitted(connection, submitter)

        await store.delete_draft(connection, draft.id)
        await store.delete_draft(connection, kept)

        assert await store.load(connection, draft.id) is None
        assert await store.load(connection, kept) is not None

    run(migrated_database, work)
