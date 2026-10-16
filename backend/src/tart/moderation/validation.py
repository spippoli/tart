"""The rules a Submission's content must satisfy before the archive's own rules apply
(contribution-and-moderation spec, Submission model and Submission form, validation rules).

    check_content(submission, content)
    changeset = materialize(content)     # what the write operation applies

`check_content` holds the rules of the model: the primary target, the related-record rule
of ADR 0007, and what a new Artwork needs. Every rule of the archive records model (required
fields, boundary, citations, ...) is checked by running `materialize(content)` through the
write operation, which the persistence layer does without storing anything.
"""

from dataclasses import replace

from tart.archive.changeset import Changeset, Create
from tart.archive.records import (
    Area,
    Artist,
    Artwork,
    DocumentationItem,
    HistoryEvent,
    HistoryEventType,
    Kind,
    Location,
    New,
)
from tart.moderation.content import Content
from tart.moderation.errors import ModerationError
from tart.moderation.model import Submission

CREATABLE = frozenset({Kind.ARTWORK, Kind.ARTIST, Kind.LOCATION, Kind.AREA})
"""The kinds a Submission may create as its primary target; the others are created only
inline, within a Submission on another record."""

assert {Artwork.KIND, Artist.KIND, Location.KIND, Area.KIND} == CREATABLE


def _primary(content: Content, kind: Kind) -> Create:
    """The record the Submission creates as its primary target: the first of its kind."""
    for operation in content.operations:
        if isinstance(operation, Create) and operation.record.KIND is kind:
            return operation
    raise ModerationError("moderation.primary_record_required")


def _documentation_of(content: Content, artwork: New) -> list[tuple[New, DocumentationItem]]:
    """The Documentation items the content creates about the new Artwork, with their refs."""
    return [
        (operation.ref, operation.record)
        for operation in content.operations
        if isinstance(operation, Create)
        and isinstance(operation.record, DocumentationItem)
        and artwork in operation.record.artworks
    ]


def check_content(submission: Submission, content: Content) -> None:
    """Raise a `ModerationError` unless the content is a valid Submission on its target."""
    if content.conflicts:
        raise ModerationError("moderation.unresolved_conflicts")
    if submission.target_id is None:
        _check_create(submission, content)
    else:
        _check_edit(submission, content)


def _check_create(submission: Submission, content: Content) -> None:
    if submission.target_kind not in CREATABLE:
        raise ModerationError("moderation.target_not_creatable")
    primary = _primary(content, submission.target_kind)
    for operation in content.operations:
        if not isinstance(operation, Create) and not isinstance(operation.target, New):
            raise ModerationError("moderation.second_record_edited")
    if submission.target_kind is Kind.ARTWORK:
        if not _documentation_of(content, primary.ref):
            raise ModerationError("moderation.documentation_required")
        if content.initial_condition is None:
            raise ModerationError("moderation.initial_condition_required")


def _check_edit(submission: Submission, content: Content) -> None:
    if len(submission.base_revisions) != 1:
        raise ModerationError("moderation.base_revision_required")
    if not content.operations:
        raise ModerationError("moderation.empty_changeset")
    for operation in content.operations:
        if isinstance(operation, Create):
            continue
        if operation.target != submission.target_id and not isinstance(operation.target, New):
            raise ModerationError("moderation.second_record_edited")


def materialize(content: Content) -> Changeset:
    """The changeset the write operation applies: the operations, and for a new Artwork the
    Condition record its initial Condition stands for, dated to the latest Observed date of
    its Documentation items and citing that item."""
    if content.initial_condition is None:
        return content.operations
    primary = next(
        (
            operation
            for operation in content.operations
            if isinstance(operation, Create) and isinstance(operation.record, Artwork)
        ),
        None,
    )
    if primary is None or not isinstance(artwork := primary.record, Artwork):
        return content.operations
    documents = _documentation_of(content, primary.ref)
    if not documents:
        raise ModerationError("moderation.documentation_required")
    cited, latest = _latest(documents)
    taken = {event.id.key for event in artwork.history_events if isinstance(event.id, New)}
    key = f"{primary.ref.key}-condition-recorded"
    while key in taken:
        key += "-"
    record = HistoryEvent(
        id=New(key),
        type=HistoryEventType.CONDITION_RECORDED,
        observed_date=latest.observed_date,
        condition=content.initial_condition,
        citations=(cited,),
    )
    events = (*artwork.history_events, record)
    return tuple(
        replace(operation, record=replace(artwork, history_events=events))
        if operation is primary
        else operation
        for operation in content.operations
    )


def _latest(
    documents: list[tuple[New, DocumentationItem]],
) -> tuple[New, DocumentationItem]:
    """The document of the most recent Observed date; an undated one only when none is
    dated, and the last listed on a tie."""
    best = documents[0]
    for document in documents:
        key = document[1].observed_date.chronological_key
        best_key = best[1].observed_date.chronological_key
        if key is not None and (best_key is None or key >= best_key):
            best = document
    return best
