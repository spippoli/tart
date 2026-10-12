"""History events through the archive write operation over PostgreSQL + PostGIS
(archive-records spec, Physical history and Attribution). Every record here is fictional.
"""

from collections.abc import Iterable
from dataclasses import replace

import pytest
from archive_fixtures import PROVENANCE, Archive, artwork, event, image, location

from tart.archive import (
    AddItem,
    ApprovedEvent,
    ArchiveRuleViolation,
    Artist,
    ArtistKind,
    Artwork,
    Attribution,
    Certainty,
    ChangeItem,
    Condition,
    ConditionGroup,
    Create,
    HistoryEvent,
    HistoryEventType,
    New,
    RemoveItem,
    SetField,
    Source,
    UncertainDate,
    derive_condition,
)
from tart.archive_persistence import PostgresArchiveStore

T = HistoryEventType
LOCATION, ARTWORK, IMAGE = New("location"), New("artwork"), New("image")


@pytest.fixture
def archive(migrated_database: str) -> Archive:
    return Archive(migrated_database)


def _rejected(archive: Archive, *changeset: object) -> str:
    with pytest.raises(ArchiveRuleViolation) as raised:
        archive.write(*changeset)  # type: ignore[arg-type]
    return raised.value.code


def _new_artwork(archive: Archive, **values: object) -> tuple[int, int, int]:
    """A new Artwork on a new Location, with an image; returns the three ids."""
    revisions = archive.write(
        Create(LOCATION, location()),
        Create(ARTWORK, artwork(LOCATION, **values)),
        Create(IMAGE, image(ARTWORK)),
    )
    location_id, artwork_id, image_id = archive.ids(revisions)
    return artwork_id, location_id, image_id


def _stored(archive: Archive, artwork_id: int) -> Artwork:
    record = archive.get(artwork_id)
    assert isinstance(record, Artwork)
    return record


def _approved(events: Iterable[HistoryEvent]) -> list[ApprovedEvent]:
    return [ApprovedEvent(stored, PROVENANCE.approved_at) for stored in events]


def test_history_events_are_stored_with_their_ids_citations_and_links(archive: Archive) -> None:
    covering_id, location_id, image_id = _new_artwork(archive, title="Fictional newer piece")
    source_id = archive.ids(archive.write(Create(New("source"), Source("A fictional zine"))))[0]

    revisions = archive.write(
        Create(
            ARTWORK,
            artwork(
                location_id,
                history_events=(
                    event(T.CREATED, citations=(source_id,)),
                    event(T.COVERED, covering=covering_id, note="Fictional: painted over."),
                    event(condition=Condition.MISSING, citations=(image_id, source_id)),
                ),
            ),
        )
    )

    artwork_id = archive.ids(revisions)[0]
    events = _stored(archive, artwork_id).history_events
    assert [(stored.type, stored.condition) for stored in events] == [
        (T.CREATED, None),
        (T.COVERED, None),
        (T.CONDITION_RECORDED, Condition.MISSING),
    ]
    assert [stored.citations for stored in events] == [(source_id,), (), (image_id, source_id)]
    assert (events[1].covering, events[1].note) == (covering_id, "Fictional: painted over.")
    ids = [stored.id for stored in events]
    assert all(isinstance(event_id, int) for event_id in ids)
    assert len(set(ids)) == 3
    # The Revision names each new event by the id it was given.
    added = [change["item"]["id"] for change in revisions[0].changes if change["op"] == "add"]
    assert added == ids


def test_an_event_is_edited_and_removed_by_its_id(archive: Archive) -> None:
    artwork_id, _, image_id = _new_artwork(archive)
    archive.write(AddItem(artwork_id, "history_events", event(T.DAMAGED)))
    recorded, damaged = _stored(archive, artwork_id).history_events

    archive.write(ChangeItem(artwork_id, "history_events", replace(damaged, citations=(image_id,))))
    revisions = archive.write(RemoveItem(artwork_id, "history_events", recorded.id))

    assert _stored(archive, artwork_id).history_events == (replace(damaged, citations=(image_id,)),)
    assert [change["op"] for change in revisions[0].changes] == ["remove"]


def test_a_new_event_is_named_by_new_never_by_an_id(archive: Archive) -> None:
    artwork_id, _, _ = _new_artwork(archive)
    taken = _stored(archive, artwork_id).history_events[0]

    assert _rejected(
        archive,
        AddItem(artwork_id, "history_events", replace(taken, type=T.DAMAGED, condition=None)),
    ) == ("changeset.history_event_not_new")


def test_an_event_key_never_names_a_record(archive: Archive) -> None:
    _, location_id, _ = _new_artwork(archive)
    named_like_the_source = event(T.DAMAGED, id=New("source"), citations=(New("source"),))

    revisions = archive.write(
        Create(New("source"), Source("A fictional zine")),
        Create(ARTWORK, artwork(location_id, history_events=(event(), named_like_the_source))),
    )

    source_id, artwork_id = archive.ids(revisions)
    assert _stored(archive, artwork_id).history_events[1].citations == (source_id,)
    assert _rejected(
        archive, ChangeItem(artwork_id, "history_events", event(T.DAMAGED, id=New("source")))
    ) == ("changeset.unknown_item")


def test_a_covered_event_links_only_another_artwork(archive: Archive) -> None:
    artwork_id, location_id, _ = _new_artwork(archive)

    assert _rejected(
        archive, AddItem(artwork_id, "history_events", event(T.COVERED, covering=artwork_id))
    ) == ("history_event.covering_itself")
    assert _rejected(
        archive, AddItem(artwork_id, "history_events", event(T.COVERED, covering=location_id))
    ) == ("changeset.invalid_reference")


def test_an_event_cites_only_sources_and_documentation_items(archive: Archive) -> None:
    artwork_id, location_id, _ = _new_artwork(archive)

    assert _rejected(
        archive, AddItem(artwork_id, "history_events", event(T.DAMAGED, citations=(location_id,)))
    ) == ("changeset.invalid_reference")


# Criterion 2: no Condition value is accepted as input.


def test_criterion_2_the_write_operation_accepts_no_condition_for_an_artwork(
    archive: Archive,
) -> None:
    artwork_id, _, _ = _new_artwork(archive)

    assert _rejected(archive, SetField(artwork_id, "condition", "destroyed")) == (
        "changeset.unknown_field"
    )


# Criterion 3.


def test_criterion_3_a_destroyed_event_makes_the_artwork_disappeared_and_hides_nothing(
    archive: Archive,
) -> None:
    artwork_id, location_id, image_id = _new_artwork(archive)
    archive.write(AddItem(artwork_id, "history_events", event(T.DAMAGED)))
    before = _stored(archive, artwork_id)
    assert derive_condition(_approved(before.history_events)).group is ConditionGroup.PRESENT

    archive.write(AddItem(artwork_id, "history_events", event(T.DESTROYED, citations=(image_id,))))

    after = _stored(archive, artwork_id)
    reading = derive_condition(_approved(after.history_events))
    assert (reading.condition, reading.group) == (Condition.DESTROYED, ConditionGroup.DISAPPEARED)
    # The Artwork, its Documentation item, its Location, and every earlier event remain.
    assert after.history_events[:2] == before.history_events
    assert archive.get(image_id) == image(artwork_id)
    assert archive.get(location_id) == location()
    public = archive.read(lambda store: store.public_records([artwork_id, location_id, image_id]))
    assert public == {artwork_id, location_id, image_id}


# Criterion 41: the last condition-changing event cannot be removed.


def test_criterion_41_a_new_artwork_without_a_condition_changing_event_is_rejected(
    archive: Archive,
) -> None:
    assert _rejected(
        archive,
        Create(LOCATION, location()),
        Create(ARTWORK, artwork(LOCATION, history_events=(event(T.CREATED),))),
        Create(IMAGE, image(ARTWORK)),
    ) == ("artwork.condition_changing_event_required")


def test_criterion_41_removing_the_last_condition_changing_event_is_rejected(
    archive: Archive,
) -> None:
    artwork_id, _, _ = _new_artwork(archive)
    archive.write(AddItem(artwork_id, "history_events", event(T.CREATED)))
    recorded = _stored(archive, artwork_id).history_events[0]

    assert _rejected(archive, RemoveItem(artwork_id, "history_events", recorded.id)) == (
        "artwork.condition_changing_event_required"
    )
    assert _rejected(
        archive,
        ChangeItem(
            artwork_id,
            "history_events",
            replace(recorded, type=T.ATTRIBUTION_CHANGED, condition=None),
        ),
    ) == ("artwork.condition_changing_event_required")


def test_criterion_41_the_last_event_can_be_replaced_by_an_unknown_condition_record(
    archive: Archive,
) -> None:
    artwork_id, _, _ = _new_artwork(archive)
    recorded = _stored(archive, artwork_id).history_events[0]
    unknown = event(condition=Condition.UNKNOWN, observed_date=UncertainDate.unknown())

    archive.write(
        RemoveItem(artwork_id, "history_events", recorded.id),
        AddItem(artwork_id, "history_events", unknown),
    )

    (replacement,) = _stored(archive, artwork_id).history_events
    assert (replacement.condition, replacement.observed_date) == (
        Condition.UNKNOWN,
        UncertainDate.unknown(),
    )


# Criterion 53, the writing side.


def test_criterion_53_an_edit_keeping_confirmed_without_a_public_citation_is_refused(
    archive: Archive, monkeypatch: pytest.MonkeyPatch
) -> None:
    artwork_id, _, _ = _new_artwork(archive)
    artist_id, source_id = archive.ids(
        archive.write(
            Create(New("artist"), Artist("Nebbia Finta (fictional)", ArtistKind.INDIVIDUAL)),
            Create(New("source"), Source("A fictional interview")),
        )
    )
    confirmed = Attribution(artist_id, Certainty.CONFIRMED, citations=(source_id,))
    archive.write(AddItem(artwork_id, "attributions", confirmed))

    # The Source is withdrawn (Rights and legal actions): no longer public.
    public_records = PostgresArchiveStore.public_records

    async def without_source(store: PostgresArchiveStore, ids: Iterable[int]) -> frozenset[int]:
        return await public_records(store, ids) - {source_id}

    monkeypatch.setattr(PostgresArchiveStore, "public_records", without_source)

    # An edit that leaves the Attribution alone goes through.
    archive.write(SetField(artwork_id, "title", "Fictional title"))
    edited = replace(confirmed, note="Fictional: signed lower left.")
    assert _rejected(archive, ChangeItem(artwork_id, "attributions", edited)) == (
        "attribution.confirmed_requires_citation"
    )
    archive.write(
        ChangeItem(artwork_id, "attributions", replace(edited, certainty=Certainty.PROBABLE))
    )

    stored = _stored(archive, artwork_id).attributions
    assert stored == (replace(edited, certainty=Certainty.PROBABLE),)
