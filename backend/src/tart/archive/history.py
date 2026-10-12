"""The physical history: Condition, Condition group, Timeline, and stratigraphy
(archive-records spec, Physical history and Location).

Each derivation is a pure function over what the public can see: callers pass only
public History events and Documentation items, each with the approval time of the
Revision that introduced it. Every ordering uses the chronological key of the
Observed date; on equal keys the later approval wins, then the higher id.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from tart.archive.records import (
    Condition,
    DocumentationItem,
    EventId,
    HistoryEvent,
    HistoryEventType,
    RecordId,
)
from tart.archive.uncertain_date import UncertainDate


class ConditionGroup(StrEnum):
    """Whether the Artwork can still be seen where it is, never whether it is public."""

    PRESENT = "present"
    DISAPPEARED = "disappeared"
    UNKNOWN = "unknown"


_GROUPS = {
    Condition.INTACT: ConditionGroup.PRESENT,
    Condition.DETERIORATED: ConditionGroup.PRESENT,
    Condition.DAMAGED: ConditionGroup.PRESENT,
    Condition.MODIFIED: ConditionGroup.PRESENT,
    Condition.COVERED: ConditionGroup.DISAPPEARED,
    Condition.REMOVED: ConditionGroup.DISAPPEARED,
    Condition.DESTROYED: ConditionGroup.DISAPPEARED,
    Condition.MISSING: ConditionGroup.DISAPPEARED,
    Condition.UNKNOWN: ConditionGroup.UNKNOWN,
}

_SETS_CONDITION = {
    HistoryEventType.DETERIORATED: Condition.DETERIORATED,
    HistoryEventType.DAMAGED: Condition.DAMAGED,
    HistoryEventType.MODIFIED: Condition.MODIFIED,
    HistoryEventType.COVERED: Condition.COVERED,
    HistoryEventType.REMOVED: Condition.REMOVED,
    HistoryEventType.DESTROYED: Condition.DESTROYED,
}

CONDITION_CHANGING = frozenset({HistoryEventType.CONDITION_RECORDED, *_SETS_CONDITION})
"""The seven types that set a Condition."""


def condition_group(condition: Condition) -> ConditionGroup:
    return _GROUPS[condition]


def condition_set_by(event: HistoryEvent) -> Condition | None:
    """The Condition the event sets, or `None` for a type that sets none."""
    if event.type is HistoryEventType.CONDITION_RECORDED:
        return event.condition
    return _SETS_CONDITION.get(event.type)


@dataclass(frozen=True)
class ApprovedEvent:
    """A public History event, with the approval time of the Revision that introduced it."""

    event: HistoryEvent
    approved_at: datetime

    @property
    def id(self) -> EventId:
        assert isinstance(self.event.id, int)
        return self.event.id

    @property
    def observed_date(self) -> UncertainDate:
        return self.event.observed_date


@dataclass(frozen=True)
class ApprovedItem:
    """A public Documentation item, with the approval time of its latest Revision."""

    id: RecordId
    item: DocumentationItem
    approved_at: datetime

    @property
    def observed_date(self) -> UncertainDate:
        return self.item.observed_date


type Dated = ApprovedEvent | ApprovedItem


def _order(entry: Dated) -> tuple[datetime | None, datetime, int]:
    """Chronological key, then approval, then id: the later entry wins a tie."""
    return entry.observed_date.chronological_key, entry.approved_at, entry.id


def _latest[T: Dated](entries: Iterable[T]) -> T | None:
    """The most recent entry by key; an undated entry only when none is dated."""
    entries = list(entries)
    dated = [entry for entry in entries if entry.observed_date.chronological_key is not None]
    if dated:
        return max(dated, key=_order)
    return max(entries, key=lambda entry: (entry.approved_at, entry.id), default=None)


@dataclass(frozen=True)
class ConditionReading:
    """An Artwork's derived Condition and the event that sets it.

    Without a public condition-changing event the Condition is `unknown`, worded
    "state not documented", with no event and so no date: the only Condition shown
    without one.
    """

    condition: Condition
    event: ApprovedEvent | None

    @property
    def group(self) -> ConditionGroup:
        return condition_group(self.condition)

    @property
    def documented(self) -> bool:
        return self.event is not None


def derive_condition(events: Iterable[ApprovedEvent]) -> ConditionReading:
    """The Condition of the Artwork whose public History events these are."""
    latest = _latest(event for event in events if event.event.type in CONDITION_CHANGING)
    if latest is None:
        return ConditionReading(Condition.UNKNOWN, None)
    condition = condition_set_by(latest.event)
    assert condition is not None
    return ConditionReading(condition, latest)


def creation_event(events: Iterable[ApprovedEvent]) -> ApprovedEvent | None:
    """The Creation event; without one the creation date is unknown, never inferred."""
    return next((event for event in events if event.event.type is HistoryEventType.CREATED), None)


def first_documentation(items: Iterable[ApprovedItem]) -> ApprovedItem | None:
    """The public Documentation item that comes first by chronological key.

    On equal keys the later approval wins, as everywhere; an undated item counts only
    when none is dated.
    """
    items = list(items)
    keys = [item.observed_date.chronological_key for item in items]
    first = min((key for key in keys if key is not None), default=None)
    return _latest(item for item, key in zip(items, keys, strict=True) if key == first)


def last_documented(items: Iterable[ApprovedItem]) -> ApprovedItem | None:
    """The public Documentation item that comes last by chronological key."""
    return _latest(items)


@dataclass(frozen=True)
class Timeline:
    """An Artwork's public History events and Documentation items, ascending.

    It never holds Revisions, Submission log entries, Withdrawals, or Redactions.
    """

    dated: tuple[Dated, ...]
    undated: tuple[Dated, ...]
    """Entries with an `unknown` Observed date: the final "Undated" group."""


def timeline(events: Iterable[ApprovedEvent], items: Iterable[ApprovedItem]) -> Timeline:
    """Ascending by chronological key; on equal keys a History event precedes a
    Documentation item, then the earlier approval comes first. The undated group
    follows the same order without the key."""
    entries: list[Dated] = [*events, *items]

    def order(entry: Dated) -> tuple[object, ...]:
        return (
            entry.observed_date.chronological_key or datetime.min,
            isinstance(entry, ApprovedItem),
            entry.approved_at,
            entry.id,
        )

    ordered = sorted(entries, key=order)
    return Timeline(
        dated=tuple(entry for entry in ordered if entry.observed_date.chronological_key),
        undated=tuple(entry for entry in ordered if not entry.observed_date.chronological_key),
    )


@dataclass(frozen=True)
class Stratum:
    """One public Artwork on a Location, with what places it in the stratigraphy."""

    artwork_id: RecordId
    creation: ApprovedEvent | None
    first_documentation: ApprovedItem | None


def _stratum_date(stratum: Stratum) -> Dated | None:
    """The Creation event when it is dated, else the first documentation when dated."""
    for entry in (stratum.creation, stratum.first_documentation):
        if entry is not None and entry.observed_date.chronological_key is not None:
            return entry
    return None


def stratigraphy(strata: Iterable[Stratum]) -> tuple[RecordId, ...]:
    """The Artworks on a Location, most recent first.

    By the chronological key of the Creation event, or of the first documentation
    without one; ties as for the key. `covered` links never reorder it, and an
    Artwork with neither date comes last.
    """

    def order(stratum: Stratum) -> tuple[object, ...]:
        entry = _stratum_date(stratum)
        if entry is None:
            return (False, datetime.min, datetime.min, 0, stratum.artwork_id)
        return (True, *_order(entry), stratum.artwork_id)

    return tuple(stratum.artwork_id for stratum in sorted(strata, key=order, reverse=True))
