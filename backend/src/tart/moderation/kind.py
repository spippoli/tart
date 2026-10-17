"""A Submission's derived kind and labels (contribution-and-moderation spec, Submission model).

Both are computed from the target and the changeset, never stored and never entered by the
Submitter. Merge, Duplicate retirement, and Unmerge have their own tickets and add their kinds.

    kind = derive_kind(submission)             # an Artwork, created
    labels = derive_labels(content)            # {Label.ADDS_DOCUMENTATION, ...}
"""

from dataclasses import dataclass
from enum import StrEnum

from tart.archive.changeset import AddItem, ChangeItem, Create, RemoveItem
from tart.archive.errors import ArchiveRuleViolation
from tart.archive.history import CONDITION_CHANGING
from tart.archive.records import Artwork, DocumentationItem, HistoryEvent, Kind
from tart.moderation.content import Content, decode_content
from tart.moderation.errors import ModerationError
from tart.moderation.model import Submission
from tart.moderation.validation import materialize


class Intent(StrEnum):
    CREATE = "create"
    EDIT = "edit"


@dataclass(frozen=True)
class SubmissionKind:
    target_kind: Kind
    intent: Intent


class Label(StrEnum):
    ADDS_DOCUMENTATION = "adds_documentation"
    ADDS_HISTORY_EVENT = "adds_history_event"
    CHANGES_ATTRIBUTION = "changes_attribution"
    CHANGES_CONDITION = "changes_condition"


def derive_kind(submission: Submission) -> SubmissionKind:
    """The primary target's kind, created when the Submission has no target record yet."""
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


def labels_of(submission: Submission) -> tuple[str, ...]:
    """The labels of what the Submission shows now: its stub, its last round, or its
    working copy; none when that content cannot be read."""
    if submission.stub is not None:
        return tuple(submission.stub["labels"])  # type: ignore[index, call-overload]
    raw = submission.rounds[-1].snapshot if submission.rounds else submission.working_copy
    if raw is None:
        return ()
    try:
        return tuple(
            label.value for label in derive_labels(decode_content(raw, submission.target_kind))
        )
    except ModerationError, ArchiveRuleViolation:
        return ()
