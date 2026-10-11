"""Revisions: one per record that an approved Submission creates or changes.

A Revision holds its provenance and a change list: each changed field with its
previous and new value, and each added, changed, or removed item. A record's first
Revision lists its initial values. Changes are JSON values, as stored.
"""

from dataclasses import dataclass, fields
from datetime import datetime

from tart.archive.codec import Json, encode
from tart.archive.records import Kind, Record, RecordId, item_key


@dataclass(frozen=True)
class Provenance:
    """Who produced a change and when: the approved Submission behind a Revision.

    The approving Moderator is recorded but never public.
    """

    submission_id: int
    submitter_id: int
    moderator_id: int
    submitted_at: datetime
    """When the Submission was first submitted."""
    approved_at: datetime


@dataclass(frozen=True)
class Revision:
    id: int
    record_id: RecordId
    kind: Kind
    provenance: Provenance
    changes: tuple[dict[str, Json], ...]


def _is_empty(value: object) -> bool:
    return value is None or value == ()


def change_list(before: Record | None, after: Record) -> tuple[dict[str, Json], ...]:
    """The changes from `before` (`None` for a new record) to `after`, in field order."""
    changes: list[dict[str, Json]] = []
    for field in fields(after):  # type: ignore[arg-type]
        name = field.name
        new = getattr(after, name)
        old = getattr(before, name) if before is not None else None
        if name in after.COLLECTIONS:
            old_items = {item_key(item): item for item in (old or ())}
            new_items = {item_key(item): item for item in new}
            for key, item in old_items.items():
                if key not in new_items:
                    changes.append({"op": "remove", "collection": name, "item": encode(item)})
                elif new_items[key] != item:
                    changes.append(
                        {
                            "op": "change",
                            "collection": name,
                            "old": encode(item),
                            "new": encode(new_items[key]),
                        }
                    )
            for key, item in new_items.items():
                if key not in old_items:
                    changes.append({"op": "add", "collection": name, "item": encode(item)})
        elif new != old and not (_is_empty(new) and _is_empty(old)):
            changes.append({"op": "set", "field": name, "old": encode(old), "new": encode(new)})
    return tuple(changes)
