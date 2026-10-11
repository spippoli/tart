"""The changeset the write operation applies (ADR 0007).

A changeset is an ordered tuple of operations: create a whole new record, set a
field, or add, change, or remove an item of a collection (an Attribution, a Crew
membership, an Alias, a link to another record). There is no operation that
deletes a record: records leave public view only by Merge or Withdrawal.
"""

from dataclasses import dataclass
from typing import Any

from tart.archive.records import New, Record, Ref


@dataclass(frozen=True)
class Create:
    """A new record; `ref` is how the rest of the changeset refers to it."""

    ref: New
    record: Record


@dataclass(frozen=True)
class SetField:
    target: Ref
    field: str
    value: Any


@dataclass(frozen=True)
class AddItem:
    target: Ref
    collection: str
    item: Any


@dataclass(frozen=True)
class ChangeItem:
    """Replace the item that has the same key as `item`."""

    target: Ref
    collection: str
    item: Any


@dataclass(frozen=True)
class RemoveItem:
    """Remove an item from a collection; the record it may link to stays."""

    target: Ref
    collection: str
    key: Any


type Operation = Create | SetField | AddItem | ChangeItem | RemoveItem
type Changeset = tuple[Operation, ...]
