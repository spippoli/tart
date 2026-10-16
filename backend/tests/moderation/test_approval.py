"""Validation, approval, Outdated, and rebase over PostgreSQL + PostGIS (contribution and
moderation spec, Lifecycle, Submission form, and Acceptance criteria). Every record and User
is fictional."""

from dataclasses import replace
from datetime import date, timedelta

import pytest
from archive_fixtures import RULES as ARCHIVE_RULES
from archive_fixtures import artwork, image, location
from moderation_fixtures import (
    ARTWORK,
    IMAGE,
    LOCATION,
    NOW,
    RULES,
    new_artwork_operations,
    new_artwork_snapshot,
    refusal,
    run,
    snapshot,
    submitted,
    user,
    write,
)
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncConnection

from tart.archive import (
    AddItem,
    Artist,
    ArtistKind,
    Attribution,
    Certainty,
    Condition,
    Create,
    HistoryEventType,
    Kind,
    Medium,
    New,
    Precision,
    Qualifier,
    RightsBasis,
    SetField,
    UncertainDate,
    evidence_level,
)
from tart.archive_persistence import PostgresArchiveStore
from tart.archive_persistence import tables as t
from tart.moderation import Reason, Status, Verdict
from tart.moderation_persistence import archive_access, service, store

LATER = NOW + timedelta(days=2)


async def artwork_with_people(connection: AsyncConnection) -> tuple[int, int, int, int]:
    """A stored Artwork, and a submitter, a Moderator, and a second Moderator."""
    _, artwork_id, _ = await write(
        connection,
        Create(LOCATION, location()),
        Create(ARTWORK, artwork(LOCATION)),
        Create(IMAGE, image(ARTWORK)),
    )
    submitter = await user(connection, "ada")
    moderator = await user(connection, "gus", moderator=True)
    other = await user(connection, "ivo", moderator=True)
    return artwork_id, submitter, moderator, other


async def revision_of(connection: AsyncConnection, record_id: int) -> int:
    state = await archive_access.target_state(connection, record_id)
    assert state is not None and state.revision_id is not None
    return state.revision_id


async def edit(
    connection: AsyncConnection, submitter: int, artwork_id: int, *changes: tuple[str, str]
) -> int:
    """A `submitted` edit of the Artwork's fields, written against its current Revision."""
    operations = [SetField(artwork_id, name, value) for name, value in changes]
    return await submitted(
        connection,
        submitter,
        snapshot(*operations),
        target_id=artwork_id,
        base_revisions=(await revision_of(connection, artwork_id),),
    )


async def approve(connection: AsyncConnection, submission_id: int, moderator: int):  # type: ignore[no-untyped-def]
    return await service.approve(
        connection, submission_id, moderator, 1, RULES, ARCHIVE_RULES, LATER
    )


# Acceptance criterion 6.
def test_an_edit_behind_the_current_revision_is_approved_when_nothing_overlaps(
    migrated_database: str,
) -> None:
    async def work(connection: AsyncConnection) -> None:
        artwork_id, submitter, moderator, _ = await artwork_with_people(connection)
        titled = await edit(connection, submitter, artwork_id, ("title", "A fictional cat"))
        described = await edit(connection, submitter, artwork_id, ("description", "On a shutter."))

        await approve(connection, titled, moderator)
        assert await service.outdated(connection, described) == ()
        await approve(connection, described, moderator)

        stored = await PostgresArchiveStore(connection).get(artwork_id)
        assert (stored.title, stored.description) == ("A fictional cat", "On a shutter.")  # type: ignore[union-attr]
        revisions = await connection.scalar(
            select(func.count()).select_from(t.revision).where(t.revision.c.record_id == artwork_id)
        )
        assert revisions == 3  # the first write, then one per approved Submission

    run(migrated_database, work)


# Acceptance criterion 6.
def test_an_edit_that_overlaps_a_change_since_its_base_is_outdated_and_cannot_be_approved(
    migrated_database: str,
) -> None:
    async def setup(connection: AsyncConnection) -> tuple[int, int, int, int]:
        artwork_id, submitter, moderator, _ = await artwork_with_people(connection)
        first = await edit(connection, submitter, artwork_id, ("title", "A fictional cat"))
        second = await edit(connection, submitter, artwork_id, ("title", "A fictional dog"))
        await approve(connection, first, moderator)
        return artwork_id, second, moderator, submitter

    artwork_id, second, moderator, _ = run(migrated_database, setup)

    async def reasons(connection: AsyncConnection) -> tuple[Reason, ...]:
        return await service.outdated(connection, second)

    assert run(migrated_database, reasons) == (Reason.OVERLAP,)

    async def approving(connection: AsyncConnection) -> object:
        return await approve(connection, second, moderator)

    assert refusal(migrated_database, approving) == "moderation.outdated"

    async def unchanged(connection: AsyncConnection) -> None:
        stored = await PostgresArchiveStore(connection).get(artwork_id)
        assert stored.title == "A fictional cat"  # type: ignore[union-attr]
        loaded = await store.load(connection, second)
        assert loaded is not None and loaded.status is Status.SUBMITTED

    run(migrated_database, unchanged)


# Acceptance criterion 7.
def test_an_edit_of_a_withdrawn_or_merged_target_is_outdated_and_cannot_be_approved(
    migrated_database: str,
) -> None:
    # The Rights and legal actions spec owns Withdrawal and Merge; here their effect on the
    # record row is enough: `withdrawn_at` and `merged_into` are what Outdated reads.
    async def withdraw(connection: AsyncConnection) -> tuple[int, int, int]:
        artwork_id, submitter, moderator, _ = await artwork_with_people(connection)
        first = await edit(connection, submitter, artwork_id, ("title", "A fictional cat"))
        second = await edit(connection, submitter, artwork_id, ("title", "A fictional dog"))
        other = (
            await write(
                connection, Create(LOCATION, location()), Create(ARTWORK, artwork(LOCATION))
            )
        )[1]
        await connection.execute(
            update(t.record).where(t.record.c.id == artwork_id).values(withdrawn_at=NOW)
        )
        assert await service.outdated(connection, first) == (Reason.TARGET_WITHDRAWN,)
        await connection.execute(
            update(t.record)
            .where(t.record.c.id == artwork_id)
            .values(withdrawn_at=None, merged_into=other)
        )
        assert await service.outdated(connection, second) == (Reason.TARGET_MERGED,)
        return first, second, moderator

    first, second, moderator = run(migrated_database, withdraw)

    for submission_id in (first, second):

        async def approving(
            connection: AsyncConnection, submission_id: int = submission_id
        ) -> object:
            return await approve(connection, submission_id, moderator)

        assert refusal(migrated_database, approving) == "moderation.outdated"


# Acceptance criterion 8.
def test_approving_a_new_artwork_writes_one_revision_per_record_with_its_provenance(
    migrated_database: str,
) -> None:
    async def work(connection: AsyncConnection) -> None:
        submitter = await user(connection, "ada")
        moderator = await user(connection, "gus", moderator=True)
        submission_id = await submitted(connection, submitter)
        await service.submit(  # a revision: the first-submitted date is the first round's
            connection,
            submission_id,
            submitter,
            new_artwork_snapshot(),
            NOW + timedelta(hours=5),
            ARCHIVE_RULES,
        )

        approval = await service.approve(
            connection, submission_id, moderator, 2, RULES, ARCHIVE_RULES, LATER
        )

        assert approval.submission.status is Status.APPROVED
        assert len(approval.revisions) == 3  # the Location, the Artwork, the Documentation item
        rows = (await connection.execute(select(t.revision).order_by(t.revision.c.id))).all()
        assert [row.record_id for row in rows] == [r.record_id for r in approval.revisions]
        for row in rows:
            assert (row.submission_id, row.submitter_id, row.moderator_id) == (
                submission_id,
                submitter,
                moderator,
            )
            assert (row.submitted_at, row.approved_at) == (NOW, LATER)
        public = await store.load(connection, submission_id)
        assert public is not None and public.status is Status.APPROVED

    run(migrated_database, work)


# Acceptance criterion 8.
def test_a_failure_while_writing_leaves_no_revision_no_record_and_a_submitted_submission(
    migrated_database: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def work(connection: AsyncConnection) -> None:
        submitter = await user(connection, "ada")
        moderator = await user(connection, "gus", moderator=True)
        submission_id = await submitted(connection, submitter)

        calls = 0
        add_revision = PostgresArchiveStore.add_revision

        async def failing(self: PostgresArchiveStore, *args: object) -> object:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError("the database went away")
            return await add_revision(self, *args)  # type: ignore[arg-type]

        monkeypatch.setattr(PostgresArchiveStore, "add_revision", failing)
        with pytest.raises(RuntimeError):
            await service.approve(
                connection, submission_id, moderator, 1, RULES, ARCHIVE_RULES, LATER
            )

        # The caller carries on and commits: nothing of the write is left in its transaction.
        for table in (t.record, t.revision, t.artwork, t.location):
            assert await connection.scalar(select(func.count()).select_from(table)) == 0
        loaded = await store.load(connection, submission_id)
        assert loaded is not None and loaded.status is Status.SUBMITTED
        assert len(loaded.log) == 1

    run(migrated_database, work)


def test_approval_is_the_only_way_to_approve(migrated_database: str) -> None:
    async def work(connection: AsyncConnection) -> object:
        submitter = await user(connection, "ada")
        moderator = await user(connection, "gus", moderator=True)
        submission_id = await submitted(connection, submitter)
        return await service.decide(
            connection, submission_id, moderator, Verdict.APPROVE, 1, RULES, LATER
        )

    assert refusal(migrated_database, work) == "moderation.approval_writes_archive"


# Acceptance criterion 15.
def test_approving_a_new_artwork_records_its_initial_condition_as_a_history_event(
    migrated_database: str,
) -> None:
    older = UncertainDate(Precision.YEAR, Qualifier.EXACT, date(2019, 1, 1))
    newer = UncertainDate(Precision.MONTH, Qualifier.EXACT, date(2024, 3, 1))
    second = New("second-image")

    async def work(connection: AsyncConnection) -> None:
        submitter = await user(connection, "ada")
        moderator = await user(connection, "gus", moderator=True)
        operations = (
            Create(LOCATION, location()),
            Create(ARTWORK, artwork(LOCATION, history_events=())),
            Create(IMAGE, image(ARTWORK, observed_date=newer)),
            Create(second, image(ARTWORK, observed_date=older)),
        )
        content = snapshot(*operations, condition=Condition.MISSING)
        submission_id = await submitted(connection, submitter, content)

        approval = await service.approve(
            connection, submission_id, moderator, 1, RULES, ARCHIVE_RULES, LATER
        )

        _, artwork_id, newer_image, _ = [r.record_id for r in approval.revisions]
        stored = await PostgresArchiveStore(connection).get(artwork_id)
        (recorded,) = stored.history_events  # type: ignore[union-attr]
        assert recorded.type is HistoryEventType.CONDITION_RECORDED
        assert recorded.condition is Condition.MISSING
        assert recorded.observed_date == newer
        assert recorded.citations == (newer_image,)

    run(migrated_database, work)


# Acceptance criteria 5 and 14.
def test_validation_refuses_a_second_record_and_an_incomplete_new_artwork(
    migrated_database: str,
) -> None:
    async def setup(connection: AsyncConnection) -> tuple[int, int, int]:
        artwork_id, submitter, _, _ = await artwork_with_people(connection)
        other = (
            await write(
                connection, Create(LOCATION, location()), Create(ARTWORK, artwork(LOCATION))
            )
        )[1]
        draft = await store.create_draft(
            connection,
            submitter,
            Kind.ARTWORK,
            NOW,
            target_id=artwork_id,
            base_revisions=(await revision_of(connection, artwork_id),),
        )
        create = await store.create_draft(connection, submitter, Kind.ARTWORK, NOW)
        return other, draft.id, create.id

    other, edit_draft, create_draft = run(migrated_database, setup)

    def codes(submission_id: int, content: object) -> str:
        async def work(connection: AsyncConnection) -> object:
            return await service.validate(connection, submission_id, content, ARCHIVE_RULES, NOW)  # type: ignore[arg-type]

        return refusal(migrated_database, work)

    two_records = snapshot(SetField(other, "title", "Theirs"))
    assert codes(edit_draft, two_records) == "moderation.second_record_edited"
    # No id names a record that exists only in a pending Submission: a reference to one,
    # by an id nothing was written under or by the key of a record another Submission
    # creates, resolves to nothing.
    unknown_id = snapshot(*new_artwork_operations(series=(999_999,)), condition=Condition.INTACT)
    assert codes(create_draft, unknown_id) == "changeset.invalid_reference"
    elsewhere = snapshot(
        *new_artwork_operations(
            attributions=(Attribution(New("created-elsewhere"), Certainty.PROBABLE),)
        ),
        condition=Condition.INTACT,
    )
    assert codes(create_draft, elsewhere) == "changeset.unknown_new_record"
    # Acceptance criterion 14.
    operations = new_artwork_operations()
    assert codes(create_draft, snapshot(*operations)) == "moderation.initial_condition_required"
    no_document = snapshot(*operations[:2], condition=Condition.INTACT)
    assert codes(create_draft, no_document) == "moderation.documentation_required"


# Acceptance criterion 14.
def test_a_single_link_is_enough_documentation_for_a_new_artwork(migrated_database: str) -> None:
    link = image(
        ARTWORK,
        medium=Medium.LINK,
        url="https://example.org/fictional-photo",
        file=None,
        licence=None,
        creator_credit=None,
        rights_basis=None,
        alt_text=None,
    )

    async def work(connection: AsyncConnection) -> None:
        submitter = await user(connection, "ada")
        operations = (*new_artwork_operations()[:2], Create(IMAGE, link))
        content = snapshot(*operations, condition=Condition.UNKNOWN)

        submission_id = await submitted(connection, submitter, content)

        loaded = await store.load(connection, submission_id)
        assert loaded is not None and loaded.status is Status.SUBMITTED

    run(migrated_database, work)


# Acceptance criterion 16.
def test_a_confirmed_attribution_without_a_citation_fails_validation(
    migrated_database: str,
) -> None:
    async def setup(connection: AsyncConnection) -> tuple[int, int, int]:
        artist_id = (
            await write(
                connection, Create(New("artist"), Artist("Nebbia Finta", ArtistKind.INDIVIDUAL))
            )
        )[0]
        artwork_id, submitter, _, _ = await artwork_with_people(connection)
        draft = await store.create_draft(
            connection,
            submitter,
            Kind.ARTWORK,
            NOW,
            target_id=artwork_id,
            base_revisions=(await revision_of(connection, artwork_id),),
        )
        return artist_id, artwork_id, draft.id

    artist_id, artwork_id, draft_id = run(migrated_database, setup)
    confirmed = Attribution(artist_id, Certainty.CONFIRMED)
    content = snapshot(AddItem(artwork_id, "attributions", confirmed))

    async def work(connection: AsyncConnection) -> object:
        return await service.validate(connection, draft_id, content, ARCHIVE_RULES, NOW)

    assert refusal(migrated_database, work) == "attribution.confirmed_requires_citation"
    # The readout of a Claim that cites nothing.
    assert evidence_level(confirmed.citations, public=[1, 2, 3]).value == "reported"


# Acceptance criterion 17.
@pytest.mark.parametrize(
    ("values", "code"),
    [
        ({"observed_date": None}, "documentation_item.observed_date_required"),
        ({"rights_basis": None}, "documentation_item.rights_basis_required"),
        ({"creator_credit": None}, "documentation_item.creator_credit_required"),
        ({"licence": None}, "documentation_item.licence_required"),
        ({"licence": "All-rights-reserved"}, "documentation_item.licence_not_allowed"),
        (
            {"rights_basis": RightsBasis.THIRD_PARTY},
            "documentation_item.origin_url_required",
        ),
    ],
)
def test_an_uploaded_file_without_its_rights_data_fails_validation(
    migrated_database: str, values: dict[str, object], code: str
) -> None:
    async def setup(connection: AsyncConnection) -> int:
        submitter = await user(connection, "ada")
        return (await store.create_draft(connection, submitter, Kind.ARTWORK, NOW)).id

    draft_id = run(migrated_database, setup)
    operations = (*new_artwork_operations()[:2], Create(IMAGE, replace(image(ARTWORK), **values)))
    content = snapshot(*operations, condition=Condition.INTACT)

    async def work(connection: AsyncConnection) -> object:
        return await service.validate(connection, draft_id, content, ARCHIVE_RULES, NOW)

    assert refusal(migrated_database, work) == code


# Acceptance criterion 54.
def test_opening_the_editor_on_an_outdated_edit_rebases_it(migrated_database: str) -> None:
    async def setup(connection: AsyncConnection) -> tuple[int, int, int, int, int]:
        artwork_id, submitter, moderator, _ = await artwork_with_people(connection)
        mine = await edit(
            connection,
            submitter,
            artwork_id,
            ("title", "A fictional dog"),
            ("description", "Mine."),
        )
        theirs = await edit(connection, submitter, artwork_id, ("title", "A fictional cat"))
        await approve(connection, theirs, moderator)
        return artwork_id, mine, submitter, moderator, await revision_of(connection, artwork_id)

    artwork_id, mine, submitter, moderator, current = run(migrated_database, setup)

    async def open_editor(connection: AsyncConnection) -> None:
        assert await service.outdated(connection, mine) == (Reason.OVERLAP,)
        rebased = await service.rebase(connection, mine, submitter, LATER)

        assert rebased.base_revisions == (current,)
        assert (
            rebased.rounds[-1].snapshot == (await store.load(connection, mine)).rounds[-1].snapshot
        )  # type: ignore[union-attr]
        content = rebased.working_copy
        assert [op["field"] for op in content["operations"]] == ["description"]  # type: ignore[index, union-attr]
        (conflict,) = content["conflicts"]  # type: ignore[index, misc]
        assert conflict["now"] == "A fictional cat"
        assert conflict["operation"]["value"] == "A fictional dog"

    run(migrated_database, open_editor)

    async def submit_with_conflict(connection: AsyncConnection) -> object:
        loaded = await store.load(connection, mine)
        assert loaded is not None
        return await service.submit(
            connection, mine, submitter, loaded.working_copy, LATER, ARCHIVE_RULES
        )

    assert refusal(migrated_database, submit_with_conflict) == "moderation.unresolved_conflicts"

    async def keep_and_submit(connection: AsyncConnection) -> None:
        from tart.moderation import decode_content, encode_content, resolve_conflict

        loaded = await store.load(connection, mine)
        assert loaded is not None
        content = decode_content(loaded.working_copy, Kind.ARTWORK)
        resolved = encode_content(resolve_conflict(content, 0, keep=True))
        revised = await service.submit(connection, mine, submitter, resolved, LATER, ARCHIVE_RULES)
        assert revised.status is Status.SUBMITTED and len(revised.rounds) == 2
        assert await service.outdated(connection, mine) == ()
        await service.approve(connection, mine, moderator, 2, RULES, ARCHIVE_RULES, LATER)
        stored = await PostgresArchiveStore(connection).get(artwork_id)
        assert (stored.title, stored.description) == ("A fictional dog", "Mine.")  # type: ignore[union-attr]

    run(migrated_database, keep_and_submit)


# Acceptance criterion 54.
def test_a_submission_whose_target_is_withdrawn_cannot_be_rebased(migrated_database: str) -> None:
    async def setup(connection: AsyncConnection) -> tuple[int, int]:
        artwork_id, submitter, _, _ = await artwork_with_people(connection)
        mine = await edit(connection, submitter, artwork_id, ("title", "A fictional dog"))
        await connection.execute(
            update(t.record).where(t.record.c.id == artwork_id).values(withdrawn_at=NOW)
        )
        return mine, submitter

    mine, submitter = run(migrated_database, setup)

    async def work(connection: AsyncConnection) -> object:
        return await service.rebase(connection, mine, submitter, LATER)

    assert refusal(migrated_database, work) == "moderation.cannot_rebase"


# Acceptance criterion 54.
def test_a_submission_whose_target_was_merged_is_rebased_onto_the_surviving_record(
    migrated_database: str,
) -> None:
    async def work(connection: AsyncConnection) -> None:
        artwork_id, submitter, _, _ = await artwork_with_people(connection)
        mine = await edit(connection, submitter, artwork_id, ("title", "A fictional dog"))
        survivor = (
            await write(
                connection, Create(LOCATION, location()), Create(ARTWORK, artwork(LOCATION))
            )
        )[1]
        await connection.execute(
            update(t.record).where(t.record.c.id == artwork_id).values(merged_into=survivor)
        )
        assert await service.outdated(connection, mine) == (Reason.TARGET_MERGED,)

        rebased = await service.rebase(connection, mine, submitter, LATER)

        assert rebased.target_id == survivor
        assert rebased.base_revisions == (await revision_of(connection, survivor),)
        assert await service.outdated(connection, mine) == ()  # asked of the new target

    run(migrated_database, work)


# Acceptance criterion 1.
def test_no_api_route_changes_an_archive_record() -> None:
    import re
    from pathlib import Path

    from tart.api.app import create_app

    unsafe = {"POST", "PUT", "PATCH", "DELETE"}
    changing = [
        route.path  # type: ignore[attr-defined]
        for route in create_app().routes
        if unsafe & set(getattr(route, "methods", ())) and route.path.startswith("/api/archive")  # type: ignore[attr-defined]
    ]
    api = Path(__file__).parents[2] / "src" / "tart" / "api"
    writers = [
        path.name
        for path in api.glob("*.py")
        if re.search(r"apply_changeset|write_changeset|\.save\(|add_revision", path.read_text())
    ]

    assert changing == []
    assert writers == []


def test_the_archive_is_written_only_by_approval_and_development_tools() -> None:
    import re
    from pathlib import Path

    src = Path(__file__).parents[2] / "src" / "tart"
    callers = {
        str(path.relative_to(src))
        for path in src.rglob("*.py")
        if re.search(r"\bapply_changeset\(|\bwrite_changeset\(", path.read_text())
        and path.name != "write.py"
    }

    assert callers == {
        "archive_persistence/__init__.py",  # the helper tests and development use
        "fictional.py",  # the fictional dataset, development and tests only
        "moderation_persistence/archive_access.py",  # a dry run, always rolled back
        "moderation_persistence/service.py",  # approval
    }
