"""Outdated, and the rebase of an Outdated edit (ADR 0007, ADR 0018; contribution-and-moderation
spec, Lifecycle).

Outdated is computed, never a status. An edit is Outdated when one of its operations touches
a field or item changed since its Base revision, or when its target was merged or withdrawn:

    reasons = outdated_reasons(submission, content, state, changes)

Otherwise approval applies its operations to the current Revision, and the result holds both
changes. A rebase moves the Base revision to the current Revision, keeps the operations that
overlap nothing, and turns each one that does into a conflict for the Submitter to keep or drop.
"""

from collections.abc import Sequence
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Any

from tart.archive.changeset import (
    AddItem,
    ChangeItem,
    Changeset,
    Create,
    Merge,
    Operation,
    RemoveItem,
    Unmerge,
)
from tart.archive.changeset_codec import decode_item
from tart.archive.codec import Json
from tart.archive.records import RECORD_TYPES, Kind, RecordId, item_key
from tart.moderation.content import Conflict, Content
from tart.moderation.errors import ModerationError
from tart.moderation.model import Submission

type Slot = tuple[str, str] | tuple[str, str, Any]
"""What an operation touches: `("field", name)` or `("item", collection, key)`."""


class Reason(StrEnum):
    TARGET_WITHDRAWN = "target_withdrawn"
    TARGET_MERGED = "target_merged"
    OVERLAP = "overlap"
    """An operation touches a field or item changed since the Base revision."""
    BASE_MOVED = "base_moved"
    """A Merge's record has a Revision newer than its Base revision."""
    NOT_PUBLIC = "not_public"
    OPEN_NOTICE = "open_notice"
    NOT_MERGED = "not_merged"
    """An Unmerge's record is no longer merged into the survivor."""


@dataclass(frozen=True)
class TargetState:
    """What the archive says about a target record now."""

    record_id: RecordId
    revision_id: int | None
    """Its latest Revision."""
    withdrawn: bool = False
    merged_into: RecordId | None = None
    open_notice: bool = False


@dataclass(frozen=True)
class RecordChange:
    """One field or item changed by a Revision."""

    revision_id: int
    slot: Slot
    now: Json
    """The value after the change; `None` for an item the Revision removed."""


def slot_of(operation: Operation) -> Slot | None:
    match operation:
        case Create() | Merge() | Unmerge():
            return None
        case AddItem() | ChangeItem():
            return ("item", operation.collection, item_key(operation.item))
        case RemoveItem():
            return ("item", operation.collection, operation.key)
    return ("field", operation.field)


def changes_of(
    kind: Kind, revision_id: int, entries: Sequence[dict[str, Json]]
) -> list[RecordChange]:
    """The fields and items a Revision's change list touches, in its order."""
    record_type = RECORD_TYPES[kind]
    changes: list[RecordChange] = []
    for entry in entries:
        match entry["op"]:
            case "set":
                changes.append(
                    RecordChange(revision_id, ("field", str(entry["field"])), entry["new"])
                )
            case "add" | "change" | "remove" as op:
                collection = str(entry["collection"])
                item = entry["new"] if op == "change" else entry["item"]
                key = item_key(decode_item(record_type, collection, item))
                now = None if op == "remove" else item
                changes.append(RecordChange(revision_id, ("item", collection, key), now))
    return changes


def overlaps(
    operations: Changeset, changes: Sequence[RecordChange]
) -> list[tuple[int, RecordChange]]:
    """Each operation that touches something changed, with the latest change to it."""
    latest = {change.slot: change for change in changes}
    found = []
    for index, operation in enumerate(operations):
        slot = slot_of(operation)
        if slot is not None and slot in latest:
            found.append((index, latest[slot]))
    return found


def outdated_reasons(
    submission: Submission, content: Content, state: TargetState, changes: Sequence[RecordChange]
) -> tuple[Reason, ...]:
    """Why an edit is Outdated; empty when it is not, and always for a create.

    `changes` are those of the target's Revisions after the Base revision.
    """
    if submission.target_id is None:
        return ()
    if state.withdrawn:
        return (Reason.TARGET_WITHDRAWN,)
    if state.merged_into is not None:
        return (Reason.TARGET_MERGED,)
    if overlaps(content.operations, changes):
        return (Reason.OVERLAP,)
    return ()


def merge_outdated_reasons(
    base_revisions: Sequence[int], states: Sequence[TargetState]
) -> tuple[Reason, ...]:
    """Why a Merge, Duplicate retirement, or Unmerge is Outdated (ADR 0018): either
    record has a Revision newer than its Base revision, is not public, or has an open Notice."""
    reasons: list[Reason] = []
    if any(state.revision_id != base for base, state in zip(base_revisions, states, strict=True)):
        reasons.append(Reason.BASE_MOVED)
    if any(state.withdrawn or state.merged_into is not None for state in states):
        reasons.append(Reason.NOT_PUBLIC)
    if any(state.open_notice for state in states):
        reasons.append(Reason.OPEN_NOTICE)
    return tuple(reasons)


@dataclass(frozen=True)
class Rebase:
    target_id: RecordId
    base_revision: int
    content: Content


def _retarget(operation: Operation, old: RecordId, new: RecordId) -> Operation:
    if isinstance(operation, Create | Merge | Unmerge) or operation.target != old:
        return operation
    return replace(operation, target=new)


def rebase(
    submission: Submission, content: Content, state: TargetState, changes: Sequence[RecordChange]
) -> Rebase:
    """Move an edit onto the target's current Revision.

    `state` is the current state of the record the edit now applies to: the target, or the
    record it was merged into, and `changes` are the Revisions of that record after the old
    Base revision. A withdrawn target cannot be rebased; the Submission stays Outdated until
    a Reinstatement. Nothing is resolved silently: an overlapping operation becomes a conflict.
    """
    if submission.target_id is None:
        raise ModerationError("moderation.cannot_rebase")
    if state.withdrawn or state.revision_id is None:
        raise ModerationError("moderation.cannot_rebase")
    operations = tuple(
        _retarget(op, submission.target_id, state.record_id) for op in content.operations
    )
    conflicts = tuple(
        replace(
            conflict, operation=_retarget(conflict.operation, submission.target_id, state.record_id)
        )
        for conflict in content.conflicts
    )
    clashing = dict(overlaps(operations, changes))
    kept = tuple(op for index, op in enumerate(operations) if index not in clashing)
    raised = tuple(
        Conflict(operations[index], change.now, change.revision_id)
        for index, change in clashing.items()
    )
    rebased = replace(content, operations=kept, conflicts=(*conflicts, *raised))
    return Rebase(state.record_id, state.revision_id, rebased)


@dataclass(frozen=True)
class MergeRebase:
    base_revisions: tuple[int, int]
    content: Content


def rebase_merge(
    content: Content,
    into_id: RecordId,
    states: tuple[TargetState, TargetState],
    into_changes: Sequence[RecordChange],
) -> MergeRebase:
    """Move a Merge, Duplicate retirement, or Unmerge onto the current Revisions of both
    records. While either record is not public or has an open Notice no rebase is possible,
    as for a withdrawn target. The operations on the survivor that overlap what changed
    since the Base revision become conflicts; the references to rewrite are recomputed
    whenever they are listed."""
    if any(state.withdrawn or state.open_notice or state.revision_id is None for state in states):
        raise ModerationError("moderation.cannot_rebase")
    mine = [
        index
        for index, op in enumerate(content.operations)
        if not isinstance(op, Create | Merge | Unmerge) and op.target == into_id
    ]
    clashing = {
        mine[found]: change
        for found, change in overlaps(tuple(content.operations[i] for i in mine), into_changes)
    }
    kept = tuple(op for index, op in enumerate(content.operations) if index not in clashing)
    raised = tuple(
        Conflict(content.operations[index], change.now, change.revision_id)
        for index, change in clashing.items()
    )
    rebased = replace(content, operations=kept, conflicts=(*content.conflicts, *raised))
    assert states[0].revision_id is not None and states[1].revision_id is not None
    return MergeRebase((states[0].revision_id, states[1].revision_id), rebased)
