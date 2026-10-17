"""A Submission's derived kind and labels (contribution-and-moderation spec, Submission model).

Both are computed from the target and the changeset, never stored and never entered by the
Submitter. A Merge, a Duplicate retirement, and an Unmerge are told by the operation their
content holds.

    kind = derive_kind(submission)             # an Artwork, created
    labels = derive_labels(content)            # {Label.ADDS_DOCUMENTATION, ...}
"""

from dataclasses import dataclass
from enum import StrEnum

from tart.archive.changeset import AddItem, ChangeItem, Create, Merge, RemoveItem, Unmerge
from tart.archive.history import CONDITION_CHANGING
from tart.archive.records import Artwork, DocumentationItem, HistoryEvent, Kind
from tart.moderation.content import Content
from tart.moderation.model import Submission
from tart.moderation.validation import materialize


class Intent(StrEnum):
    CREATE = "create"
    EDIT = "edit"
    MERGE = "merge"
    RETIREMENT = "retirement"
    """A Duplicate retirement: a Merge of Documentation items, which are never merged."""
    UNMERGE = "unmerge"


@dataclass(frozen=True)
class SubmissionKind:
    target_kind: Kind
    intent: Intent


class Label(StrEnum):
    ADDS_DOCUMENTATION = "adds_documentation"
    ADDS_HISTORY_EVENT = "adds_history_event"
    CHANGES_ATTRIBUTION = "changes_attribution"
    CHANGES_CONDITION = "changes_condition"


def derive_kind(submission: Submission, content: Content | None = None) -> SubmissionKind:
    """The primary target's kind, created when the Submission has no target record yet.

    A Merge or an Unmerge is an edit of its content that holds the operation; the kind of the
    folded record tells a Duplicate retirement (a Documentation item) from a Merge.
    """
    if content is not None:
        for operation in content.operations:
            if isinstance(operation, Unmerge):
                return SubmissionKind(submission.target_kind, Intent.UNMERGE)
            if isinstance(operation, Merge):
                retired = submission.target_kind is Kind.DOCUMENTATION_ITEM
                return SubmissionKind(
                    submission.target_kind, Intent.RETIREMENT if retired else Intent.MERGE
                )
    intent = Intent.CREATE if submission.target_id is None else Intent.EDIT
    return SubmissionKind(submission.target_kind, intent)


def derive_labels(content: Content) -> tuple[Label, ...]:
    """What the changeset does beyond the fields it sets, in the order of `Label`.

    It reads the changeset as approval applies it, so the Condition record of a new
    Artwork counts. Removing a History event is not labelled: the changeset does not say
    which type the removed event had.
    """
    found: set[Label] = set()
    events: list[HistoryEvent] = []
    for operation in materialize(content):
        match operation:
            case Create(record=DocumentationItem()):
                found.add(Label.ADDS_DOCUMENTATION)
            case Create(record=Artwork() as artwork):
                events += artwork.history_events
                if artwork.history_events:
                    found.add(Label.ADDS_HISTORY_EVENT)
                if artwork.attributions:
                    found.add(Label.CHANGES_ATTRIBUTION)
            case AddItem(item=HistoryEvent() as event):
                events.append(event)
                found.add(Label.ADDS_HISTORY_EVENT)
            case ChangeItem(item=HistoryEvent() as event):
                events.append(event)
            case AddItem() | ChangeItem() | RemoveItem() if operation.collection == "attributions":
                found.add(Label.CHANGES_ATTRIBUTION)
    if any(event.type in CONDITION_CHANGING for event in events):
        found.add(Label.CHANGES_CONDITION)
    return tuple(label for label in Label if label in found)
