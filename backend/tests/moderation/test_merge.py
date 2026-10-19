"""Merge, Duplicate retirement, and Unmerge over PostgreSQL + PostGIS (contribution and
moderation spec, Merge, Duplicate retirement, Unmerge; acceptance criteria 26 to 29 and 51).
Every record and User is fictional."""

from collections.abc import Callable
from dataclasses import replace
from datetime import timedelta

import pytest
from archive_fixtures import RULES as ARCHIVE_RULES
from archive_fixtures import artwork, event, image, location, point
from moderation_fixtures import NOW, RULES, refusal, run, user
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncConnection

from tart import moderation
from tart.archive import (
    AddItem,
    Artist,
    ArtistKind,
    Attribution,
    Certainty,
    Create,
    CrewMembership,
    HistoryEventType,
    Kind,
    Medium,
    Merge,
    New,
    Operation,
    Provenance,
    RemoveItem,
    SetField,
    Source,
    Unmerge,
    apply_changeset,
)
from tart.archive_persistence import PostgresArchiveStore
from tart.archive_persistence import tables as t
from tart.archive_read import RecordMergedError
from tart.archive_read.reader import Reader, Viewer
from tart.moderation import Reason, merge_of
from tart.moderation.merge import Contradiction, Origin, plan_merge
from tart.moderation_persistence import archive_access, contribution, merging, service, store

LATER = NOW + timedelta(days=2)
X, Y = New("x"), New("y")


async def write(connection: AsyncConnection, *changeset: Operation) -> list[int]:
    """Records straight through the write operation, attributed to no Submission (id 0)."""
    revisions = await apply_changeset(
        PostgresArchiveStore(connection),
        changeset,
        Provenance(0, 1, 1, NOW, NOW),
        ARCHIVE_RULES,
    )
    return [revision.record_id for revision in revisions]


async def people(connection: AsyncConnection) -> tuple[int, int]:
    return await user(connection, "ada"), await user(connection, "gus", moderator=True)


async def propose(
    connection: AsyncConnection,
    submitter: int,
    source: int,
    into: int,
    edit: Callable[[moderation.Content], moderation.Content] = lambda content: content,
    *,
    submit: bool = True,
) -> int:
    """A Merge (or Duplicate retirement) draft pre-filled by the plan, edited, and submitted."""
    draft = await contribution.start_merge(
        connection, submitter, source, into, NOW, ARCHIVE_RULES, expiry_days=90
    )
    assert draft.working_copy is not None
    content = edit(moderation.decode_content(draft.working_copy, draft.target_kind))
    snapshot = moderation.encode_content(content)
    if submit:
        await service.submit(connection, draft.id, submitter, snapshot, NOW, ARCHIVE_RULES)
    else:
        await service.autosave(connection, draft.id, submitter, snapshot, NOW)
    return draft.id


async def approve(connection: AsyncConnection, submission_id: int, moderator: int) -> None:
    await service.approve(connection, submission_id, moderator, 1, RULES, ARCHIVE_RULES, LATER)


async def two_locations(connection: AsyncConnection) -> tuple[int, int, int, int]:
    """Two Locations on the same surface, each with an Artwork: (x, y, artwork of x, of y)."""
    lx, ax, _ = await write(
        connection,
        Create(New("l"), location()),
        Create(New("a"), artwork(New("l"))),
        Create(New("i"), image(New("a"))),
    )
    ly, ay, _ = await write(
        connection,
        Create(New("l"), location(geometry=point(12.4824, 41.8956))),
        Create(New("a"), artwork(New("l"), title="Fictional second cat")),
        Create(New("i"), image(New("a"))),
    )
    return lx, ly, ax, ay


# Acceptance criterion 26.
def test_approving_a_merge_rewrites_every_record_that_referenced_x_and_redirects_x_to_y(
    migrated_database: str,
) -> None:
    async def work(connection: AsyncConnection) -> None:
        submitter, moderator = await people(connection)
        lx, ly, ax, _ = await two_locations(connection)
        archive = PostgresArchiveStore(connection)

        references = await merging.references_of(connection, lx)
        assert [(each.id, each.kind) for each in references] == [(ax, Kind.ARTWORK)]

        merge_id = await propose(connection, submitter, lx, ly)
        await approve(connection, merge_id, moderator)

        moved = await archive.get(ax)
        assert moved is not None and moved.location == ly  # type: ignore[union-attr]
        latest = (await archive.revisions_of(ax))[-1]
        assert latest.provenance.submission_id == merge_id
        survivor = (await archive.revisions_of(ly))[-1]
        assert survivor.provenance.submission_id == merge_id
        assert {"op": "merge", "record": lx} in survivor.changes
        assert await archive.redirect_of(lx) == ly
        with pytest.raises(RecordMergedError) as redirect:
            await Reader(connection, Viewer()).resolve(Kind.LOCATION, lx)
        assert redirect.value.target == ly

    run(migrated_database, work)


# Acceptance criterion 26.
def test_redirects_are_flattened_so_that_no_id_redirects_through_a_chain(
    migrated_database: str,
) -> None:
    async def work(connection: AsyncConnection) -> None:
        submitter, moderator = await people(connection)
        lx, ly, _, _ = await two_locations(connection)
        (lz,) = await write(connection, Create(New("l"), location(geometry=point(12.45, 41.9))))
        archive = PostgresArchiveStore(connection)

        await approve(connection, await propose(connection, submitter, lx, ly), moderator)
        await approve(connection, await propose(connection, submitter, ly, lz), moderator)

        assert await archive.redirect_of(lx) == lz
        assert await archive.redirect_of(ly) == lz
        view = await Reader(connection, Viewer()).revisions(Kind.LOCATION, lx)
        assert view.merged_into is not None and view.merged_into.id == lz

    run(migrated_database, work)


def test_the_merge_revision_of_the_survivor_names_the_folded_record(migrated_database: str) -> None:
    async def work(connection: AsyncConnection) -> None:
        submitter, moderator = await people(connection)
        lx, ly, _, _ = await two_locations(connection)
        await approve(connection, await propose(connection, submitter, lx, ly), moderator)

        view = await Reader(connection, Viewer()).revisions(Kind.LOCATION, ly)

        change = view.revisions[0].changes[0]
        assert (change.op, change.record.id if change.record else None) == ("merge", lx)

    run(migrated_database, work)


async def artists(connection: AsyncConnection) -> tuple[int, int, int]:
    """Two Artists and an Artwork signed by the first with its Alias: (x, y, artwork)."""
    (source,) = await write(connection, Create(New("s"), Source(title="A fictional zine")))
    x, y = await write(
        connection,
        Create(
            New("x"), Artist(name="Fictional Hand", kind=ArtistKind.INDIVIDUAL, aliases=("FH",))
        ),
        Create(New("y"), Artist(name="Fictional Brush", kind=ArtistKind.INDIVIDUAL)),
    )
    _, signed, _ = await write(
        connection,
        Create(New("l"), location()),
        Create(
            New("a"),
            artwork(
                New("l"),
                attributions=(
                    Attribution(x, Certainty.CONFIRMED, alias="FH", citations=(source,)),
                ),
            ),
        ),
        Create(New("i"), image(New("a"))),
    )
    return x, y, signed


# Acceptance criterion 27.
def test_an_artist_merge_adds_the_name_and_aliases_of_x_to_y_as_aliases(
    migrated_database: str,
) -> None:
    async def work(connection: AsyncConnection) -> None:
        submitter, moderator = await people(connection)
        x, y, signed = await artists(connection)
        archive = PostgresArchiveStore(connection)

        await approve(connection, await propose(connection, submitter, x, y), moderator)

        survivor = await archive.get(y)
        assert survivor.aliases == ("Fictional Hand", "FH")  # type: ignore[union-attr]
        attribution = (await archive.get(signed)).attributions[0]  # type: ignore[union-attr]
        assert (attribution.artist, attribution.alias) == (y, "FH")  # the same Alias, on Y

    run(migrated_database, work)


# Acceptance criterion 27.
def test_an_artist_merge_whose_changeset_removes_the_alias_an_attribution_names_fails(
    migrated_database: str,
) -> None:
    async def work(connection: AsyncConnection) -> None:
        submitter, _ = await people(connection)
        x, y, _ = await artists(connection)

        def drop_alias(content: moderation.Content) -> moderation.Content:
            kept = tuple(
                op for op in content.operations if not (isinstance(op, AddItem) and op.item == "FH")
            )
            return replace(content, operations=kept)

        await propose(connection, submitter, x, y, drop_alias)

    assert refusal(migrated_database, work) == "attribution.alias_not_of_artist"


# Acceptance criterion 27.
def test_a_merge_that_leaves_an_artist_a_member_of_itself_fails_validation(
    migrated_database: str,
) -> None:
    async def work(connection: AsyncConnection) -> None:
        submitter, _ = await people(connection)
        x, y = await write(
            connection,
            Create(X, Artist(name="Fictional Crew", kind=ArtistKind.COLLECTIVE)),
            Create(
                Y,
                Artist(
                    name="Fictional Crew Two",
                    kind=ArtistKind.COLLECTIVE,
                    crew_memberships=(CrewMembership(X),),
                ),
            ),
        )
        await propose(connection, submitter, x, y)

    assert refusal(migrated_database, work) == "crew_membership.cycle"


# Acceptance criterion 27.
def test_a_merge_that_leaves_an_artist_two_identical_memberships_fails_validation(
    migrated_database: str,
) -> None:
    async def work(connection: AsyncConnection) -> None:
        submitter, _ = await people(connection)
        x, y, _ = await write(
            connection,
            Create(X, Artist(name="Fictional Crew", kind=ArtistKind.COLLECTIVE)),
            Create(Y, Artist(name="Fictional Crew Two", kind=ArtistKind.COLLECTIVE)),
            Create(
                New("m"),
                Artist(
                    name="Fictional Member",
                    kind=ArtistKind.INDIVIDUAL,
                    crew_memberships=(CrewMembership(X), CrewMembership(Y)),
                ),
            ),
        )
        await propose(connection, submitter, x, y)

    assert refusal(migrated_database, work) == "crew_membership.duplicate"


async def documentation(connection: AsyncConnection) -> tuple[int, int, int]:
    """An Artwork with two photographs of it, one cited by its Attribution:
    (artwork, kept item, duplicate item)."""
    (artist,) = await write(
        connection, Create(New("p"), Artist(name="Fictional Hand", kind=ArtistKind.INDIVIDUAL))
    )
    _, work_id, kept, duplicate = await write(
        connection,
        Create(New("l"), location()),
        Create(
            New("a"),
            artwork(
                New("l"),
                attributions=(Attribution(artist, Certainty.CONFIRMED, citations=(New("d"),)),),
            ),
        ),
        Create(New("k"), image(New("a"))),
        Create(New("d"), image(New("a"), file="originals/duplicate.jpg")),
    )
    return work_id, kept, duplicate


# Acceptance criterion 28.
def test_an_accepted_retirement_moves_links_and_citations_so_no_evidence_is_lost(
    migrated_database: str,
) -> None:
    async def work(connection: AsyncConnection) -> None:
        submitter, moderator = await people(connection)
        work_id, kept, duplicate = await documentation(connection)
        archive = PostgresArchiveStore(connection)

        retirement = await propose(connection, submitter, duplicate, kept)
        submission = await store.load(connection, retirement)
        assert submission is not None
        assert (
            moderation.derive_kind(
                submission,
                moderation.decode_content(submission.rounds[-1].snapshot, Kind.DOCUMENTATION_ITEM),
            ).intent.value
            == "retirement"
        )
        await approve(connection, retirement, moderator)

        artwork_record = await archive.get(work_id)
        assert artwork_record.attributions[0].citations == (kept,)  # type: ignore[union-attr]
        assert await archive.public_records([kept]) == {kept}
        assert await archive.redirect_of(duplicate) == kept
        view = await Reader(connection, Viewer()).view(Kind.ARTWORK, work_id)
        assert [item.id for item in view.gallery] == [kept]  # type: ignore[union-attr]

    run(migrated_database, work)


# Acceptance criterion 28.
def test_a_retirement_between_items_on_different_locations_is_rejected(
    migrated_database: str,
) -> None:
    async def work(connection: AsyncConnection) -> None:
        submitter, _ = await people(connection)
        _, _, ax, ay = await two_locations(connection)
        kept, duplicate = [
            next(iter(await PostgresArchiveStore(connection).documentation_items_of([each])))
            for each in (ax, ay)
        ]
        await propose(connection, submitter, duplicate, kept)

    assert refusal(migrated_database, work) == "duplicate_retirement.different_locations"


# Acceptance criterion 29.
def test_an_unmerge_restores_x_under_its_own_id_and_points_its_records_back(
    migrated_database: str,
) -> None:
    async def work(connection: AsyncConnection) -> None:
        submitter, moderator = await people(connection)
        x, y, signed = await artists(connection)
        archive = PostgresArchiveStore(connection)
        before = await archive.get(x)
        await approve(connection, await propose(connection, submitter, x, y), moderator)
        # An Alias added to Y after the Merge, which the Unmerge must not remove by default.
        await write(connection, AddItem(y, "aliases", "Later"))

        draft = await contribution.start_unmerge(connection, submitter, x, NOW, expiry_days=90)
        assert draft.working_copy is not None
        content = moderation.decode_content(draft.working_copy, Kind.ARTIST)
        removed = {
            op.key for op in content.operations if isinstance(op, RemoveItem) and op.target == y
        }
        assert removed == {"Fictional Hand", "FH"}
        await service.submit(
            connection, draft.id, submitter, draft.working_copy, NOW, ARCHIVE_RULES
        )
        await approve(connection, draft.id, moderator)

        assert await archive.redirect_of(x) is None
        assert await archive.get(x) == before
        assert (await archive.get(y)).aliases == ("Later",)  # type: ignore[union-attr]
        attribution = (await archive.get(signed)).attributions[0]  # type: ignore[union-attr]
        assert (attribution.artist, attribution.alias) == (x, "FH")
        assert next(iter((await archive.revisions_of(y))[-1].changes)) == {
            "op": "unmerge",
            "record": x,
        }

    run(migrated_database, work)


# Acceptance criterion 51.
def test_an_unmerge_preselects_only_the_items_that_came_from_x(migrated_database: str) -> None:
    async def work(connection: AsyncConnection) -> None:
        submitter, moderator = await people(connection)
        x, y, _ = await artists(connection)
        await approve(connection, await propose(connection, submitter, x, y), moderator)
        await write(connection, AddItem(y, "aliases", "Later"))

        into, plan = await merging.unmerge_plan(connection, x)

        assert into == y
        assert [(e.collection, e.item) for e in plan.from_source] == [
            ("aliases", "Fictional Hand"),
            ("aliases", "FH"),
        ]
        assert [(e.collection, e.item) for e in plan.added_since] == [("aliases", "Later")]
        removals = [op.key for op in plan.operations if isinstance(op, RemoveItem)]
        assert "Later" not in removals

    run(migrated_database, work)


async def two_artworks_with_creation_events(connection: AsyncConnection) -> tuple[int, int]:
    created = lambda: event(HistoryEventType.CREATED)  # noqa: E731
    _, ax = await write(
        connection,
        Create(New("l"), location()),
        Create(New("a"), artwork(New("l"), history_events=(created(), event()))),
    )
    _, ay = await write(
        connection,
        Create(New("l"), location(geometry=point(12.4824, 41.8956))),
        Create(New("a"), artwork(New("l"), history_events=(created(), event()))),
    )
    return ax, ay


# Acceptance criterion 51.
def test_a_merge_with_two_creation_events_fails_at_submit_not_before(
    migrated_database: str,
) -> None:
    async def work(connection: AsyncConnection) -> None:
        submitter, _ = await people(connection)
        ax, ay = await two_artworks_with_creation_events(connection)
        plan = await merging.merge_plan(connection, ax, ay)
        assert [found.kind for found in plan.contradictions] == [Contradiction.TWO_CREATION_EVENTS]

        # Flagged at once, and the draft still saves: the form never blocks.
        draft_id = await propose(connection, submitter, ax, ay, submit=False)
        assert (await store.load(connection, draft_id)) is not None
        await propose(connection, submitter, ax, ay)

    assert refusal(migrated_database, work) == "artwork.creation_event_duplicated"


def test_dropping_the_creation_event_of_x_resolves_the_contradiction(
    migrated_database: str,
) -> None:
    async def work(connection: AsyncConnection) -> None:
        submitter, moderator = await people(connection)
        ax, ay = await two_artworks_with_creation_events(connection)

        def drop_created(content: moderation.Content) -> moderation.Content:
            kept = tuple(
                op
                for op in content.operations
                if not (
                    isinstance(op, AddItem)
                    and getattr(op.item, "type", None) is HistoryEventType.CREATED
                )
            )
            return replace(content, operations=kept)

        merge_id = await propose(connection, submitter, ax, ay, drop_created)
        await approve(connection, merge_id, moderator)

        merged = await PostgresArchiveStore(connection).get(ay)
        created = [e for e in merged.history_events if e.type is HistoryEventType.CREATED]  # type: ignore[union-attr]
        assert len(created) == 1

    run(migrated_database, work)


def test_a_merge_is_outdated_when_either_base_revision_moves_on_and_rebases(
    migrated_database: str,
) -> None:
    async def work(connection: AsyncConnection) -> None:
        submitter, moderator = await people(connection)
        lx, ly, _, _ = await two_locations(connection)
        merge_id = await propose(connection, submitter, lx, ly)
        assert await service.outdated(connection, merge_id) == ()

        await write(connection, SetField(ly, "place_description", "Behind the fictional bakery"))

        assert await service.outdated(connection, merge_id) == (Reason.BASE_MOVED,)
        with pytest.raises(ValueError) as refused:
            await approve(connection, merge_id, moderator)
        assert refused.value.code == "moderation.outdated"  # type: ignore[attr-defined]

        rebased = await service.rebase(connection, merge_id, submitter, LATER)

        current = [
            (await archive_access.target_state(connection, each)).revision_id  # type: ignore[union-attr]
            for each in (lx, ly)
        ]
        assert list(rebased.base_revisions) == current

    run(migrated_database, work)


def test_a_merge_is_outdated_when_either_record_is_not_public(migrated_database: str) -> None:
    async def work(connection: AsyncConnection) -> None:
        submitter, _ = await people(connection)
        lx, ly, _, _ = await two_locations(connection)
        merge_id = await propose(connection, submitter, lx, ly)

        await connection.execute(
            update(t.record).where(t.record.c.id == ly).values(withdrawn_at=NOW)
        )

        assert await service.outdated(connection, merge_id) == (Reason.NOT_PUBLIC,)
        with pytest.raises(ValueError) as refused:
            await service.rebase(connection, merge_id, submitter, LATER)
        assert refused.value.code == "moderation.cannot_rebase"  # type: ignore[attr-defined]

    run(migrated_database, work)


def test_merging_records_of_different_kinds_or_already_merged_ones_is_refused(
    migrated_database: str,
) -> None:
    async def work(connection: AsyncConnection) -> None:
        submitter, moderator = await people(connection)
        lx, ly, ax, _ = await two_locations(connection)
        await approve(connection, await propose(connection, submitter, lx, ly), moderator)
        with pytest.raises(ValueError) as merged:
            await contribution.start_merge(
                connection, submitter, lx, ly, NOW, ARCHIVE_RULES, expiry_days=90
            )
        assert merged.value.code == "moderation.target_merged"  # type: ignore[attr-defined]
        with pytest.raises(ValueError) as kinds:
            await contribution.start_merge(
                connection, submitter, ly, ax, NOW, ARCHIVE_RULES, expiry_days=90
            )
        assert kinds.value.code == "moderation.merge_kind_mismatch"  # type: ignore[attr-defined]

    run(migrated_database, work)


def test_the_operations_of_a_merge_round_trip_through_json_with_their_kinds() -> None:
    operations = (
        AddItem(7, "attributions", Attribution(9, Certainty.PROBABLE), Kind.ARTWORK),
        RemoveItem(8, "aliases", "FH"),
        Merge(5, 6),
        Unmerge(5, 6),
    )
    content = moderation.Content(operations)

    decoded = moderation.decode_content(moderation.encode_content(content), Kind.ARTIST)

    assert decoded == content
    assert merge_of(decoded) == Merge(5, 6)


def test_the_plan_adds_what_the_survivor_lacks_and_leaves_its_fields() -> None:
    plan = plan_merge
    source = Artist(name="Fictional Hand", kind=ArtistKind.INDIVIDUAL, aliases=("FH",))
    into = Artist(name="Fictional Brush", kind=ArtistKind.INDIVIDUAL, aliases=("FB",))

    result = plan(1, source, 2, into)

    assert [op for op in result.operations if isinstance(op, AddItem)] == [
        AddItem(2, "aliases", "Fictional Hand"),
        AddItem(2, "aliases", "FH"),
    ]
    assert result.operations[-1] == Merge(1, 2)
    assert [(e.item, e.origin) for e in result.items if e.collection == "aliases"] == [
        ("Fictional Hand", Origin.SOURCE),
        ("FH", Origin.SOURCE),
        ("FB", Origin.INTO),
    ]
    assert [(d.name, d.source, d.into) for d in result.fields] == [
        ("name", "Fictional Hand", "Fictional Brush")
    ]


def test_a_documentation_retirement_plan_never_reconciles_the_file_or_its_rights() -> None:
    plan = plan_merge
    source = image(1, file="originals/a.jpg", creator_credit="Fictional A")
    into = image(1, file="originals/b.jpg", creator_credit="Fictional B", medium=Medium.IMAGE)

    result = plan(10, source, 11, into)

    assert result.fields == ()
    assert result.operations == (Merge(10, 11),)
