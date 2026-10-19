"""Merge, Duplicate retirement, and Unmerge, in the archive's terms (ADR 0018).

    after = redirect_references(record, old=7, new=9)       # a record that referenced 7

A Merge folds a record `old` into `new`: every record that referenced `old` is rewritten to
reference `new`. Only references are rewritten; the items of `old` that `new` should keep are
added to it by the changeset. Two references that become one are written once; two items that
become one and say something (two Attributions to the Artist, two Crew memberships of the same
period) are a contradiction the Submission has to resolve first.
"""

from dataclasses import replace
from typing import Any

from tart.archive.errors import ArchiveRuleViolation
from tart.archive.records import (
    Area,
    Artist,
    Artwork,
    Attribution,
    DocumentationItem,
    HistoryEvent,
    Location,
    Record,
    RecordId,
    Ref,
    Series,
    Site,
    Source,
)


def _ref(ref: Ref | None, old: RecordId, new: RecordId) -> Ref | None:
    return new if ref == old else ref


def _refs(refs: tuple[Ref, ...], old: RecordId, new: RecordId) -> tuple[Ref, ...]:
    """The links with `old` replaced by `new`, once each, in order."""
    return tuple(dict.fromkeys(new if ref == old else ref for ref in refs))


def _event(event: HistoryEvent, old: RecordId, new: RecordId) -> HistoryEvent:
    return replace(
        event,
        citations=_refs(event.citations, old, new),
        covering=_ref(event.covering, old, new),
    )


def _attribution(attribution: Attribution, old: RecordId, new: RecordId) -> Attribution:
    return replace(
        attribution,
        artist=_ref(attribution.artist, old, new),  # type: ignore[arg-type]
        citations=_refs(attribution.citations, old, new),
    )


def _unique(items: tuple[Any, ...], code: str) -> tuple[Any, ...]:
    keys = [item.key for item in items]
    if len(set(keys)) != len(keys):
        raise ArchiveRuleViolation(code)
    return items


def redirect_references(record: Record, old: RecordId, new: RecordId) -> Record:
    """The record with every link to `old` pointing to `new`.

    Raises `ArchiveRuleViolation` when the rewrite leaves the record with two Attributions to
    one Artist (`attribution.duplicate_artist`) or two Crew memberships that are one
    (`crew_membership.duplicate`).
    """
    match record:
        case Artwork():
            attributions = tuple(_attribution(each, old, new) for each in record.attributions)
            return replace(
                record,
                location=_ref(record.location, old, new),  # type: ignore[arg-type]
                series=_refs(record.series, old, new),
                sources=_refs(record.sources, old, new),
                attributions=_unique(attributions, "attribution.duplicate_artist"),
                history_events=tuple(_event(each, old, new) for each in record.history_events),
            )
        case Location():
            return replace(record, site=_ref(record.site, old, new))
        case Artist():
            memberships = tuple(
                replace(each, collective=_ref(each.collective, old, new))
                for each in record.crew_memberships
            )
            return replace(
                record,
                areas=_refs(record.areas, old, new),
                sources=_refs(record.sources, old, new),
                crew_memberships=_unique(memberships, "crew_membership.duplicate"),
            )
        case DocumentationItem():
            return replace(
                record,
                artworks=_refs(record.artworks, old, new),
                location=_ref(record.location, old, new),
            )
        case Site() | Area() | Series():
            return replace(record, sources=_refs(record.sources, old, new))
        case Source():
            return record
    return record
