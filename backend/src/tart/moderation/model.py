"""The Submission aggregate: status, rounds, the Submission log, and Moderation notes.

All values are immutable; the lifecycle returns a new Submission. No framework or
persistence imports (contribution-and-moderation spec, Modules).
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from tart.archive.codec import Json
from tart.archive.records import Kind, RecordId

DUPLICATE_REASON = "duplicate"
"""The platform's Decision message reason, listed last in every vocabulary."""


class Status(StrEnum):
    """The closed Submission status vocabulary (ADR 0009)."""

    DRAFT = "draft"
    SUBMITTED = "submitted"
    CHANGES_REQUESTED = "changes_requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    RETRACTED = "retracted"


FINAL = frozenset({Status.APPROVED, Status.REJECTED, Status.RETRACTED})


class Event(StrEnum):
    """What a Submission log entry records."""

    SUBMITTED = "submitted"
    REVISED = "revised"
    RESUBMITTED = "resubmitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"
    RETRACTED = "retracted"
    EXPIRED = "expired"


class ActorKind(StrEnum):
    USER = "user"
    SYSTEM = "system"


@dataclass(frozen=True)
class Actor:
    """Who acts: a User with or without the Moderator role, or the system."""

    kind: ActorKind
    user_id: int | None = None
    moderator: bool = False

    @classmethod
    def user(cls, user_id: int, *, moderator: bool = False) -> Actor:
        return cls(ActorKind.USER, user_id, moderator)

    @classmethod
    def system(cls) -> Actor:
        return cls(ActorKind.SYSTEM)


@dataclass(frozen=True)
class Decision:
    """A Moderator's decision message: a reason of the vocabulary plus free text."""

    reason: str
    text: str


@dataclass(frozen=True)
class Round:
    """One submission or resubmission, with a snapshot of its changeset."""

    number: int
    snapshot: Json
    submitted_at: datetime


@dataclass(frozen=True)
class LogEntry:
    """One transition: its actor, date, and message.

    The message of a rejection or a changes-requested entry is the Decision message
    (`reason` names its reason); the message of a `submitted` entry is the Submitter's
    optional note to Moderators, one per round.
    """

    event: Event
    actor: Actor
    at: datetime
    round: int | None = None
    message: str | None = None
    reason: str | None = None


@dataclass(frozen=True)
class ModerationNote:
    """A remark only Moderators see; immutable, with author and date."""

    author_id: int
    at: datetime
    text: str


@dataclass(frozen=True)
class Submission:
    id: int
    submitter_id: int
    target_kind: Kind
    target_id: RecordId | None
    """The record an edit changes; `None` for a create."""
    base_revisions: tuple[int, ...]
    """The Revision of the target an edit was written against; two for a Merge."""
    status: Status
    created_at: datetime
    rounds: tuple[Round, ...] = ()
    log: tuple[LogEntry, ...] = ()
    notes: tuple[ModerationNote, ...] = ()
    working_copy: Json = None
    """The draft's content, or the Submitter's private copy while a decision is pending."""
    last_autosave_at: datetime | None = None
    working_copy_discarded: bool = field(default=False, compare=False)
    """A decision discarded an open working copy; the Submitter sees a notice."""

    @property
    def version(self) -> int:
        """The state a Moderator sees: it changes with every transition."""
        return len(self.log)

    @property
    def first_submitted_at(self) -> datetime | None:
        return self.rounds[0].submitted_at if self.rounds else None

    @property
    def changes_requested_at(self) -> datetime | None:
        if self.status is not Status.CHANGES_REQUESTED:
            return None
        return next(
            entry.at for entry in reversed(self.log) if entry.event is Event.CHANGES_REQUESTED
        )
