"""The changeset the write operation applies (ADR 0007).

A changeset is an ordered tuple of operations: create a whole new record, set a
field, or add, change, or remove an item of a collection (an Attribution, a Crew
membership, an Alias, a link to another record). There is no operation that
deletes a record: records leave public view only by Merge or Withdrawal.

A Merge, which folds a record into another of the same kind (a Documentation item's is a
Duplicate retirement), and an Unmerge, which brings it back, are operations too (ADR 0018).
The operations on the surviving record's items are ordinary ones beside them.
"""

from dataclasses import dataclass
from typing import Any

from tart.archive.records import Kind, New, Record, Ref


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
    kind: Kind | None = None
    """The kind of the target when it is not the Submission's own target (a Merge rewrites
    other kinds of records); the write operation does not read it."""


@dataclass(frozen=True)
class AddItem:
    target: Ref
    collection: str
    item: Any
    kind: Kind | None = None


@dataclass(frozen=True)
class ChangeItem:
    """Replace the item that has the same key as `item`."""

    target: Ref
    collection: str
    item: Any
    kind: Kind | None = None


@dataclass(frozen=True)
class RemoveItem:
    """Remove an item from a collection; the record it may link to stays."""

    target: Ref
    collection: str
    key: Any
    kind: Kind | None = None


@dataclass(frozen=True)
class Merge:
    """Fold the record `source` into the surviving record `into`, of the same kind.

    Writing it redirects `source` to `into` and rewrites every record that referenced
    `source` to reference `into`, each with a Revision of its own. The items of `source`
    that `into` should keep are added to it by ordinary operations beside this one.
    """

    source: int
    into: int


@dataclass(frozen=True)
class Unmerge:
    """Bring `source`, folded into `into` by a Merge, back under its own id."""

    source: int
    into: int


type Operation = Create | SetField | AddItem | ChangeItem | RemoveItem | Merge | Unmerge
type Changeset = tuple[Operation, ...]
