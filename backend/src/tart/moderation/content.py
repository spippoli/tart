"""What a round snapshot and the working copy hold, as typed values (ADR 0007).

    content = decode_content(round_.snapshot, submission.target_kind)

The JSON form is `{"operations": [...], "initial_condition": "intact", "conflicts": [...]}`;
the operations are the archive's changeset (`tart.archive.changeset_codec`). The initial
Condition is asked of a new Artwork only. A conflict is an operation of a rebased edit that
overlaps a change made since its Base revision and waits for the Submitter to keep or drop it.
"""

from dataclasses import dataclass, replace

from tart.archive.changeset import AddItem, ChangeItem, Changeset, Operation, RemoveItem
from tart.archive.changeset_codec import decode_changeset, encode_changeset
from tart.archive.codec import Json
from tart.archive.errors import ArchiveRuleViolation
from tart.archive.records import Condition, Kind
from tart.moderation.errors import ModerationError


@dataclass(frozen=True)
class Conflict:
    """An operation that overlaps a field or item changed since the Base revision."""

    operation: Operation
    now: Json
    """The current value of the field or item, `None` when the item was removed."""
    revision_id: int
    """The Revision that made the change."""


@dataclass(frozen=True)
class Content:
    operations: Changeset
    initial_condition: Condition | None = None
    conflicts: tuple[Conflict, ...] = ()


def decode_content(snapshot: Json, target_kind: Kind) -> Content:
    """The content of a snapshot; a snapshot that is not content is refused."""
    try:
        if not isinstance(snapshot, dict):
            raise TypeError("an object was expected")
        condition = snapshot.get("initial_condition")
        conflicts = []
        for raw in snapshot.get("conflicts") or []:
            (operation,) = decode_changeset([raw["operation"]], target_kind)  # type: ignore[index]
            conflicts.append(Conflict(operation, raw["now"], int(raw["revision"])))  # type: ignore[index, arg-type]
        return Content(
            decode_changeset(snapshot.get("operations"), target_kind),
            Condition(condition) if condition is not None else None,  # type: ignore[arg-type]
            tuple(conflicts),
        )
    except ArchiveRuleViolation as violation:
        if violation.code.startswith("geometry."):
            raise  # a geometry the editor can word: self-intersecting, too few vertices, ...
        raise ModerationError("moderation.malformed_content") from None
    except KeyError, TypeError, ValueError:
        raise ModerationError("moderation.malformed_content") from None


def encode_content(content: Content) -> Json:
    return {
        "operations": encode_changeset(content.operations),
        "initial_condition": content.initial_condition.value if content.initial_condition else None,
        "conflicts": [
            {
                "operation": encode_changeset((conflict.operation,))[0],  # type: ignore[index]
                "now": conflict.now,
                "revision": conflict.revision_id,
            }
            for conflict in content.conflicts
        ],
    }


MAX_UPLOADED_ITEMS = 20
"""At most this many uploaded Documentation items in one Submission; links are not counted."""


def uploaded_files(snapshot: Json) -> list[str]:
    """The files of the Documentation items a snapshot creates, in order.

    Read from the JSON as it is, so that an incomplete draft can be scanned too; anything
    that is not a Documentation item with a file is skipped.
    """
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("operations"), list):
        return []
    files: list[str] = []
    for operation in snapshot["operations"]:  # type: ignore[union-attr]
        if not isinstance(operation, dict) or operation.get("op") != "create":
            continue
        record = operation.get("record")
        if (
            operation.get("kind") == "documentation_item"
            and isinstance(record, dict)
            and isinstance(record.get("file"), str)
        ):
            files.append(record["file"])
    return files


def check_file_count(snapshot: Json) -> None:
    if len(uploaded_files(snapshot)) > MAX_UPLOADED_ITEMS:
        raise ModerationError("moderation.too_many_files")


def resolve_conflict(content: Content, index: int, *, keep: bool) -> Content:
    """Keep or drop one conflict; nothing is resolved silently.

    A kept operation applies over the current state, so it is adapted to it: adding an
    item that now exists changes it, changing an item that was removed adds it back,
    and removing an item that is already gone has nothing left to do.
    """
    try:
        conflict = content.conflicts[index]
    except IndexError:
        raise ModerationError("moderation.unknown_conflict") from None
    remaining = (*content.conflicts[:index], *content.conflicts[index + 1 :])
    if not keep:
        return replace(content, conflicts=remaining)
    operation = conflict.operation
    match operation:
        case AddItem() if conflict.now is not None:
            kept: tuple[Operation, ...] = (
                ChangeItem(operation.target, operation.collection, operation.item),
            )
        case ChangeItem() if conflict.now is None:
            kept = (AddItem(operation.target, operation.collection, operation.item),)
        case RemoveItem() if conflict.now is None:
            kept = ()
        case _:
            kept = (operation,)
    return replace(content, operations=(*content.operations, *kept), conflicts=remaining)
