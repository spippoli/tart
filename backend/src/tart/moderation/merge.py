"""Planning a Merge, a Duplicate retirement, and an Unmerge (ADR 0018; contribution-and-moderation
spec, Merge, Duplicate retirement, Unmerge).

    plan = plan_merge(source_id, source, into_id, into)
    plan = plan_unmerge(source_id, into_id, into, revisions_of_into, referrers)

A plan is the changeset an editor starts from, with what the proposer decides: it is pre-filled
and editable, and the Submission stores only the operations. A Merge folds the items of the
source that the surviving record lacks into it; field values stay the survivor's unless the
changeset sets them. An Unmerge reverses what the Merge wrote: it removes the items it added
to the survivor, and points the records that referenced the source back to it.

Pure: records and Revisions are read by the caller.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields, replace
from enum import StrEnum
from typing import Any, get_type_hints

from tart.archive.changeset import (
    AddItem,
    ChangeItem,
    Changeset,
    Merge,
    Operation,
    RemoveItem,
    SetField,
    Unmerge,
)
from tart.archive.changeset_codec import decode_item, decode_value, encode_value
from tart.archive.codec import Json
from tart.archive.records import (
    RECORD_TYPES,
    Artist,
    DocumentationItem,
    HistoryEvent,
    HistoryEventType,
    New,
    Record,
    RecordId,
    item_key,
)
from tart.archive.revisions import Revision
from tart.moderation.content import Content
from tart.moderation.errors import ModerationError


class Contradiction(StrEnum):
    """What the merged result would say twice. The proposer resolves it; it blocks the
    Submission only when it is submitted."""

    TWO_CREATION_EVENTS = "two_creation_events"
    COMPETING_ATTRIBUTIONS = "competing_attributions"
    """Both Artworks attribute themselves to the same Artist."""
    DIFFERENT_DISAPPEARANCE_LOCATIONS = "different_disappearance_locations"
    """Both Documentation items document the disappearance of different Locations."""


@dataclass(frozen=True)
class Found:
    kind: Contradiction
    key: Json = None
    """The Artist of competing Attributions."""
    item: Json = None
    """The folded record's Attribution, which the proposer may choose over the survivor's."""


class Origin(StrEnum):
    SOURCE = "source"
    """An item of the folded record that the survivor lacks: added by default."""
    INTO = "into"
    """An item of the survivor: kept by default, and droppable."""


@dataclass(frozen=True)
class ItemEntry:
    collection: str
    key: Json
    """What the operation that adds or removes the item names it by."""
    item: Json
    origin: Origin


@dataclass(frozen=True)
class FieldDifference:
    name: str
    source: Json
    into: Json


@dataclass(frozen=True)
class Plan:
    operations: Changeset
    items: tuple[ItemEntry, ...]
    fields: tuple[FieldDifference, ...]
    contradictions: tuple[Found, ...]


def _folded(item: Any) -> Any:
    """The item as the survivor receives it: a History event gets an id of its own."""
    if isinstance(item, HistoryEvent):
        return replace(item, id=New(f"merged-event-{item.id}"))
    return item


def _lacking(
    source_id: RecordId, into_id: RecordId, source: Record, into: Record, collection: str
) -> list[Any]:
    """The items of the source that the survivor lacks, in order."""
    kept = {item_key(item) for item in getattr(into, collection)}
    if isinstance(source, Artist) and collection == "aliases":
        # The folded Artist's name and Aliases become Aliases of the survivor (ADR 0018).
        names = dict.fromkeys([source.name, *source.aliases])
        return [name for name in names if name not in kept and name != into.name]
    found = []
    for item in getattr(source, collection):
        if collection == "crew_memberships" and item.collective in (source_id, into_id):
            continue  # a membership of the folded Artist in the survivor has no meaning
        if collection == "history_events" or item_key(item) not in kept:
            found.append(item)
    return found


def _differences(source: Record, into: Record, *, retirement: bool) -> list[FieldDifference]:
    found = []
    for field in fields(source):  # type: ignore[arg-type]
        name = field.name
        if name in source.COLLECTIONS:
            continue
        if retirement and name != "location":
            continue  # file, licence, credits, and fields are never reconciled
        mine, theirs = getattr(source, name), getattr(into, name)
        if mine is not None and mine != theirs:
            found.append(FieldDifference(name, encode_value(mine), encode_value(theirs)))
    return found


def _contradictions(
    source: Record, into: Record, folded: Mapping[str, Sequence[Any]]
) -> list[Found]:
    found: list[Found] = []
    events = [*getattr(into, "history_events", ()), *folded.get("history_events", ())]
    if sum(event.type is HistoryEventType.CREATED for event in events) > 1:
        found.append(Found(Contradiction.TWO_CREATION_EVENTS))
    if hasattr(source, "attributions"):
        mine = {attribution.artist: attribution for attribution in source.attributions}
        found += [
            Found(
                Contradiction.COMPETING_ATTRIBUTIONS,
                attribution.artist,
                encode_value(mine[attribution.artist]),
            )
            for attribution in into.attributions  # type: ignore[attr-defined]
            if attribution.artist in mine
        ]
    if (
        isinstance(source, DocumentationItem)
        and isinstance(into, DocumentationItem)
        and source.location is not None
        and into.location is not None
        and source.location != into.location
    ):
        found.append(Found(Contradiction.DIFFERENT_DISAPPEARANCE_LOCATIONS))
    return found


def plan_merge(source_id: RecordId, source: Record, into_id: RecordId, into: Record) -> Plan:
    """The default Merge of `source` into `into`: the items the survivor lacks are added to it,
    and the Merge itself. For a Documentation item (a Duplicate retirement) that is its
    Artwork links and, when the survivor has none, its disappearance Location."""
    if source.KIND is not into.KIND:
        raise ModerationError("moderation.merge_kind_mismatch")
    retirement = isinstance(source, DocumentationItem)
    operations: list[Operation] = []
    items: list[ItemEntry] = []
    folded: dict[str, list[Any]] = {}
    for collection in source.COLLECTIONS:
        folded[collection] = _lacking(source_id, into_id, source, into, collection)
        for item in folded[collection]:
            added = _folded(item)
            operations.append(AddItem(into_id, collection, added))
            items.append(
                ItemEntry(
                    collection, encode_value(item_key(added)), encode_value(added), Origin.SOURCE
                )
            )
        items += [
            ItemEntry(collection, encode_value(item_key(item)), encode_value(item), Origin.INTO)
            for item in getattr(into, collection)
        ]
    differences = _differences(source, into, retirement=retirement)
    if (
        isinstance(source, DocumentationItem)
        and isinstance(into, DocumentationItem)
        and source.location is not None
        and into.location is None
    ):
        operations.append(SetField(into_id, "location", source.location))
        differences = [d for d in differences if d.name != "location"]
    return Plan(
        (*operations, Merge(source_id, into_id)),
        tuple(items),
        tuple(differences),
        tuple(_contradictions(source, into, folded)),
    )


# Unmerge.


@dataclass(frozen=True)
class Referrer:
    """A record that the Merge rewrote, with its Revisions written by that Merge's Submission
    and the record as it is now."""

    record_id: RecordId
    record: Record
    revisions: Sequence[Revision]


@dataclass(frozen=True)
class Restore:
    """A record's change by the Merge, as the operation that points it back."""

    record_id: RecordId
    operation: Operation


@dataclass(frozen=True)
class UnmergePlan:
    operations: Changeset
    """The default Unmerge: the survivor's items from the folded record removed, the
    referencing records pointed back to it, and the Unmerge itself."""
    from_source: tuple[ItemEntry, ...]
    """The survivor's items that the Merge added: preselected for removal."""
    added_since: tuple[ItemEntry, ...]
    """The items added to the survivor after the Merge: the proposer decides."""
    restored: tuple[Restore, ...]
    """The records pointed back to the folded one: preselected, and editable."""
    skipped: tuple[RecordId, ...]
    """Referencing records that changed since the Merge in the same place: pointed back by
    hand if at all."""


def merge_submission(revisions_of_into: Sequence[Revision], source_id: RecordId) -> int | None:
    """The Submission whose approval last merged the source into this record."""
    for revision in reversed(revisions_of_into):
        if {"op": "merge", "record": source_id} in revision.changes:
            return revision.provenance.submission_id
    return None


def _collection_changes(
    kind_record: Record, revisions: Sequence[Revision]
) -> list[tuple[int, str, Any]]:
    """The items the Revisions added: (Revision id, collection, item)."""
    added = []
    record_type = type(kind_record)
    for revision in revisions:
        for change in revision.changes:
            if change["op"] == "add":
                collection = str(change["collection"])
                added.append(
                    (revision.id, collection, decode_item(record_type, collection, change["item"]))
                )
    return added


def _present(record: Record, collection: str, key: Any) -> bool:
    return any(item_key(item) == key for item in getattr(record, collection))


def plan_unmerge(
    source_id: RecordId,
    into_id: RecordId,
    into: Record,
    revisions_of_into: Sequence[Revision],
    referrers: Sequence[Referrer],
) -> UnmergePlan:
    """The default Unmerge of a record, from the Revisions the Merge wrote."""
    submission = merge_submission(revisions_of_into, source_id)
    if submission is None:
        raise ModerationError("moderation.not_merged")
    merging = [r for r in revisions_of_into if r.provenance.submission_id == submission]
    last_merge = max(revision.id for revision in merging)
    from_source, added_since = [], []
    operations: list[Operation] = []
    for revision_id, collection, item in _collection_changes(into, revisions_of_into):
        key = item_key(item)
        if not _present(into, collection, key):
            continue
        entry = ItemEntry(collection, encode_value(key), encode_value(item), Origin.INTO)
        if revision_id in {revision.id for revision in merging}:
            from_source.append(entry)
            operations.append(RemoveItem(into_id, collection, key))
        elif revision_id > last_merge:
            added_since.append(entry)
    restored: list[Restore] = []
    skipped: list[RecordId] = []
    for referrer in referrers:
        record_type = RECORD_TYPES[referrer.record.KIND]
        for revision in referrer.revisions:
            for change in revision.changes:
                operation = _inverse(referrer.record_id, record_type, referrer.record, change)
                if operation is None:
                    skipped.append(referrer.record_id)
                else:
                    restored.append(Restore(referrer.record_id, operation))
                    operations.append(operation)
    return UnmergePlan(
        (*operations, Unmerge(source_id, into_id)),
        tuple(from_source),
        tuple(added_since),
        tuple(restored),
        tuple(dict.fromkeys(skipped)),
    )


def _inverse(
    record_id: RecordId, record_type: type[Record], record: Record, change: Mapping[str, Json]
) -> Operation | None:
    """The operation that undoes a change of a Merge, or `None` when the record has since
    moved on from what the Merge wrote there."""
    match change["op"]:
        case "set":
            name = str(change["field"])
            hints = get_type_hints(record_type)
            if encode_value(getattr(record, name)) != change["new"]:
                return None
            return SetField(record_id, name, decode_value(hints[name], change["old"]), record.KIND)
        case "add":
            collection = str(change["collection"])
            item = decode_item(record_type, collection, change["item"])
            if not _present(record, collection, item_key(item)):
                return None
            return RemoveItem(record_id, collection, item_key(item), record.KIND)
        case "remove":
            collection = str(change["collection"])
            item = decode_item(record_type, collection, change["item"])
            if _present(record, collection, item_key(item)):
                return None
            return AddItem(record_id, collection, item, record.KIND)
        case "change":
            collection = str(change["collection"])
            new = decode_item(record_type, collection, change["new"])
            old = decode_item(record_type, collection, change["old"])
            current = next(
                (i for i in getattr(record, collection) if item_key(i) == item_key(new)), None
            )
            if current is None or encode_value(current) != encode_value(new):
                return None
            return ChangeItem(record_id, collection, old, record.KIND)
    return None


__all__ = [
    "Contradiction",
    "FieldDifference",
    "Found",
    "ItemEntry",
    "Origin",
    "Plan",
    "Referrer",
    "Restore",
    "UnmergePlan",
    "merge_of",
    "merge_submission",
    "plan_merge",
    "plan_unmerge",
]


def merge_of(content: Content) -> Merge | Unmerge | None:
    """The Merge, Duplicate retirement, or Unmerge the content holds, if any."""
    for operation in content.operations:
        if isinstance(operation, Merge | Unmerge):
            return operation
    return None
