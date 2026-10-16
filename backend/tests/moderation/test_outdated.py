"""Outdated and the rebase of an edit, without a database (ADR 0007, ADR 0018;
contribution and moderation spec, Lifecycle). Every record is fictional."""

from datetime import UTC, datetime

import pytest

from tart.archive import (
    AddItem,
    Attribution,
    Certainty,
    ChangeItem,
    Kind,
    RemoveItem,
    SetField,
)
from tart.moderation import (
    Actor,
    Content,
    ModerationError,
    Reason,
    RecordChange,
    Status,
    Submission,
    TargetState,
    check_content,
    merge_outdated_reasons,
    outdated_reasons,
    rebase,
    rebase_working_copy,
    resolve_conflict,
)
from tart.moderation.outdated import changes_of

NOW = datetime(2026, 9, 1, 10, 0, tzinfo=UTC)
BASE = 5
TARGET = 7


def edit(*, target_id: int = TARGET, base: int = BASE) -> Submission:
    return Submission(1, 2, Kind.ARTWORK, target_id, (base,), Status.SUBMITTED, NOW)


def state(revision: int = 9, **values: object) -> TargetState:
    return TargetState(TARGET, revision, **values)  # type: ignore[arg-type]


def field_changed(name: str, revision: int = 8, now: object = "theirs") -> RecordChange:
    return RecordChange(revision, ("field", name), now)  # type: ignore[arg-type]


# Acceptance criterion 6.
def test_an_edit_is_not_outdated_when_nothing_it_touches_changed_since_its_base() -> None:
    content = Content((SetField(TARGET, "title", "Mine"),))

    assert outdated_reasons(edit(), content, state(), [field_changed("description")]) == ()
    assert outdated_reasons(edit(), content, state(), []) == ()


# Acceptance criterion 6.
def test_an_edit_is_outdated_when_an_operation_touches_a_field_or_item_changed_since() -> None:
    attribution = Attribution(30, Certainty.PROBABLE)
    item_changed = RecordChange(8, ("item", "attributions", 30), {"artist": 30})
    cases = [
        (SetField(TARGET, "title", "Mine"), field_changed("title")),
        (AddItem(TARGET, "attributions", attribution), item_changed),
        (ChangeItem(TARGET, "attributions", attribution), item_changed),
        (RemoveItem(TARGET, "attributions", 30), item_changed),
    ]

    for operation, change in cases:
        reasons = outdated_reasons(edit(), Content((operation,)), state(), [change])
        assert reasons == (Reason.OVERLAP,)


def test_revisions_are_read_as_the_fields_and_items_they_change() -> None:
    entries = [
        {"op": "set", "field": "title", "old": None, "new": "Theirs"},
        {"op": "add", "collection": "history_events", "item": _event_json(40)},
        {
            "op": "remove",
            "collection": "attributions",
            "item": {"artist": 30, "certainty": "probable"},
        },
        {"op": "change", "collection": "series", "old": 3, "new": 4},
    ]

    assert changes_of(Kind.ARTWORK, 8, entries) == [  # type: ignore[arg-type]
        RecordChange(8, ("field", "title"), "Theirs"),
        RecordChange(8, ("item", "history_events", 40), _event_json(40)),
        RecordChange(8, ("item", "attributions", 30), None),
        RecordChange(8, ("item", "series", 4), 4),
    ]


def _event_json(event_id: int) -> dict[str, object]:
    return {
        "id": event_id,
        "type": "damaged",
        "observed_date": {"precision": "unknown", "qualifier": None, "first": None, "second": None},
        "condition": None,
        "note": None,
        "citations": [],
        "covering": None,
    }


# Acceptance criterion 7.
def test_an_edit_of_a_merged_or_withdrawn_target_is_outdated() -> None:
    content = Content((SetField(TARGET, "title", "Mine"),))

    assert outdated_reasons(edit(), content, state(withdrawn=True), []) == (
        Reason.TARGET_WITHDRAWN,
    )
    assert outdated_reasons(edit(), content, state(merged_into=12), []) == (Reason.TARGET_MERGED,)


# Acceptance criterion 7.
def test_a_merge_is_outdated_when_either_base_revision_moves_on_or_a_record_is_not_public() -> None:
    x, y = TargetState(7, 5), TargetState(8, 6)

    assert merge_outdated_reasons((5, 6), (x, y)) == ()
    assert merge_outdated_reasons((5, 6), (TargetState(7, 9), y)) == (Reason.BASE_MOVED,)
    assert merge_outdated_reasons((5, 6), (x, TargetState(8, 9))) == (Reason.BASE_MOVED,)
    assert merge_outdated_reasons((5, 6), (TargetState(7, 5, withdrawn=True), y)) == (
        Reason.NOT_PUBLIC,
    )
    assert merge_outdated_reasons((5, 6), (x, TargetState(8, 6, merged_into=3))) == (
        Reason.NOT_PUBLIC,
    )
    assert merge_outdated_reasons((5, 6), (x, TargetState(8, 6, open_notice=True))) == (
        Reason.OPEN_NOTICE,
    )


def test_a_create_is_never_outdated() -> None:
    create = Submission(1, 2, Kind.ARTWORK, None, (), Status.SUBMITTED, NOW)

    assert outdated_reasons(create, Content(()), state(withdrawn=True), []) == ()


# Acceptance criterion 54.
def test_a_rebase_moves_the_base_keeps_what_does_not_overlap_and_flags_the_rest() -> None:
    mine = Content(
        (
            SetField(TARGET, "title", "Mine"),
            SetField(TARGET, "description", "Also mine"),
            AddItem(TARGET, "series", 12),
        )
    )

    rebased = rebase(edit(), mine, state(9), [field_changed("title", 8, "Theirs")])

    assert rebased.base_revision == 9
    assert rebased.content.operations == mine.operations[1:]
    (conflict,) = rebased.content.conflicts
    assert conflict.operation == mine.operations[0]
    assert (conflict.now, conflict.revision_id) == ("Theirs", 8)


# Acceptance criterion 54.
def test_it_cannot_be_submitted_until_every_conflict_is_kept_or_dropped() -> None:
    mine = Content((SetField(TARGET, "title", "Mine"), SetField(TARGET, "description", "Mine too")))
    rebased = rebase(edit(base=9), mine, state(9), [field_changed("title", 8)]).content

    with pytest.raises(ModerationError) as raised:
        check_content(edit(base=9), rebased)
    assert raised.value.code == "moderation.unresolved_conflicts"

    kept = resolve_conflict(rebased, 0, keep=True)
    dropped = resolve_conflict(rebased, 0, keep=False)
    check_content(edit(base=9), kept)
    check_content(edit(base=9), dropped)
    assert SetField(TARGET, "title", "Mine") in kept.operations
    assert SetField(TARGET, "title", "Mine") not in dropped.operations


def test_a_kept_operation_is_adapted_to_the_state_it_now_applies_to() -> None:
    attribution = Attribution(30, Certainty.PROBABLE)
    slot = ("item", "attributions", 30)
    added = rebase(
        edit(),
        Content((AddItem(TARGET, "attributions", attribution),)),
        state(),
        [RecordChange(8, slot, {"artist": 30})],
    ).content
    changed = rebase(
        edit(),
        Content((ChangeItem(TARGET, "attributions", attribution),)),
        state(),
        [RecordChange(8, slot, None)],
    ).content
    removed = rebase(
        edit(),
        Content((RemoveItem(TARGET, "attributions", 30),)),
        state(),
        [RecordChange(8, slot, None)],
    ).content

    assert resolve_conflict(added, 0, keep=True).operations == (
        ChangeItem(TARGET, "attributions", attribution),
    )
    assert resolve_conflict(changed, 0, keep=True).operations == (
        AddItem(TARGET, "attributions", attribution),
    )
    assert resolve_conflict(removed, 0, keep=True).operations == ()
    with pytest.raises(ModerationError):
        resolve_conflict(added, 3, keep=True)


# Acceptance criterion 54.
def test_a_withdrawn_target_cannot_be_rebased() -> None:
    with pytest.raises(ModerationError) as raised:
        rebase(edit(), Content((SetField(TARGET, "title", "Mine"),)), state(withdrawn=True), [])

    assert raised.value.code == "moderation.cannot_rebase"


# Acceptance criterion 54.
def test_a_merged_target_is_rebased_onto_the_surviving_record() -> None:
    mine = Content((SetField(TARGET, "title", "Mine"),))
    survivor = TargetState(12, 10)

    rebased = rebase(edit(), mine, survivor, [])

    assert (rebased.target_id, rebased.base_revision) == (12, 10)
    assert rebased.content.operations == (SetField(12, "title", "Mine"),)


def test_opening_the_editor_stores_the_rebase_as_the_submitters_working_copy() -> None:
    submitted = edit()

    moved = rebase_working_copy(
        submitted, Actor.user(2), NOW, target_id=12, base_revision=10, content={"operations": []}
    )

    assert (moved.target_id, moved.base_revisions) == (12, (10,))
    assert moved.working_copy == {"operations": []}
    assert moved.rounds == submitted.rounds  # the round Moderators see is unchanged
    with pytest.raises(ModerationError):
        rebase_working_copy(
            submitted, Actor.user(3), NOW, target_id=12, base_revision=10, content=None
        )
