"""The lifecycle state machine and the permission rules (contribution-and-moderation spec,
Lifecycle and Roles and permissions).

    submission = submit(submission, actor, now, snapshot)
    submission = decide(submission, actor, Verdict.REJECT, now, decision=..., rules=...)

Every function takes the Submission and returns the next one, or raises a
`ModerationError` with a stable code. A transition not in `TRANSITIONS` does not exist.
"""

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from enum import StrEnum

from tart.archive.codec import Json
from tart.moderation.errors import ModerationError
from tart.moderation.model import (
    FINAL,
    Actor,
    ActorKind,
    Decision,
    Event,
    LogEntry,
    ModerationNote,
    Round,
    Status,
    Submission,
)


class Action(StrEnum):
    SUBMIT = "submit"
    REVISE = "revise"
    RESUBMIT = "resubmit"
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_CHANGES = "request_changes"
    RETRACT = "retract"
    EXPIRE = "expire"
    CONVERT = "convert"


TRANSITIONS: dict[tuple[Status, Action], tuple[Status, Event]] = {
    (Status.DRAFT, Action.SUBMIT): (Status.SUBMITTED, Event.SUBMITTED),
    (Status.SUBMITTED, Action.REVISE): (Status.SUBMITTED, Event.REVISED),
    (Status.CHANGES_REQUESTED, Action.RESUBMIT): (Status.SUBMITTED, Event.RESUBMITTED),
    (Status.SUBMITTED, Action.APPROVE): (Status.APPROVED, Event.APPROVED),
    (Status.SUBMITTED, Action.REJECT): (Status.REJECTED, Event.REJECTED),
    (Status.CHANGES_REQUESTED, Action.REJECT): (Status.REJECTED, Event.REJECTED),
    (Status.SUBMITTED, Action.REQUEST_CHANGES): (
        Status.CHANGES_REQUESTED,
        Event.CHANGES_REQUESTED,
    ),
    (Status.SUBMITTED, Action.RETRACT): (Status.RETRACTED, Event.RETRACTED),
    (Status.CHANGES_REQUESTED, Action.RETRACT): (Status.RETRACTED, Event.RETRACTED),
    (Status.CHANGES_REQUESTED, Action.EXPIRE): (Status.RETRACTED, Event.EXPIRED),
    (Status.CHANGES_REQUESTED, Action.CONVERT): (Status.RETRACTED, Event.CONVERTED_INTO),
}
"""Exactly the transitions of the Lifecycle table."""

SUBMITTER_ACTIONS = frozenset({Action.SUBMIT, Action.REVISE, Action.RESUBMIT, Action.RETRACT})
DECISIONS = frozenset({Action.APPROVE, Action.REJECT, Action.REQUEST_CHANGES})


class Verdict(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_CHANGES = "request_changes"


@dataclass(frozen=True)
class DecisionRules:
    """What a decision is checked against."""

    self_approval: bool
    """`community.self_approval`."""
    reasons: frozenset[str]
    """The keys of the Decision message reasons, `duplicate` included."""


def _transition(submission: Submission, action: Action) -> tuple[Status, Event]:
    try:
        return TRANSITIONS[submission.status, action]
    except KeyError:
        raise ModerationError("moderation.invalid_transition") from None


def _apply(
    submission: Submission,
    action: Action,
    actor: Actor,
    now: datetime,
    *,
    snapshot: Json = None,
    message: str | None = None,
    reason: str | None = None,
    related: int | None = None,
) -> Submission:
    """Move to the next status, adding the log entry and, on a submission, the round."""
    status, event = _transition(submission, action)
    rounds = submission.rounds
    number = len(rounds) or None
    if action in {Action.SUBMIT, Action.REVISE, Action.RESUBMIT}:
        number = len(rounds) + 1
        rounds = (*rounds, Round(number, snapshot, now))
    entry = LogEntry(event, actor, now, number, message, reason, related)
    return replace(
        submission,
        status=status,
        rounds=rounds,
        log=(*submission.log, entry),
        # Every transition ends the working copy: a submission replaces it by its round.
        working_copy=None,
    )


def _require_submitter(submission: Submission, actor: Actor) -> None:
    if actor.kind is not ActorKind.USER or actor.user_id != submission.submitter_id:
        raise ModerationError("moderation.not_submitter")


def _action_for_submit(submission: Submission) -> Action:
    match submission.status:
        case Status.DRAFT:
            return Action.SUBMIT
        case Status.SUBMITTED:
            return Action.REVISE
        case Status.CHANGES_REQUESTED:
            return Action.RESUBMIT
    raise ModerationError("moderation.invalid_transition")


def submit(
    submission: Submission,
    actor: Actor,
    now: datetime,
    snapshot: Json,
    *,
    note: str | None = None,
) -> Submission:
    """Submit a draft, revise a `submitted` Submission, or resubmit after changes were
    requested; each opens a new numbered round. Validation, the terms, and the rate
    limits are checked by the caller before it calls this."""
    _require_submitter(submission, actor)
    return _apply(
        submission, _action_for_submit(submission), actor, now, snapshot=snapshot, message=note
    )


def retract(submission: Submission, actor: Actor, now: datetime) -> Submission:
    """The Submitter withdraws a Submission before a decision."""
    _require_submitter(submission, actor)
    return _apply(submission, Action.RETRACT, actor, now)


def check_moderator(actor: Actor, submission: Submission, rules: DecisionRules) -> None:
    """Whether the actor may take a decision on the Submission at all."""
    if actor.kind is not ActorKind.USER or not actor.moderator:
        raise ModerationError("moderation.forbidden")
    if actor.user_id == submission.submitter_id and not rules.self_approval:
        raise ModerationError("moderation.own_submission")


def decide(
    submission: Submission,
    actor: Actor,
    verdict: Verdict,
    now: datetime,
    *,
    expected_version: int,
    rules: DecisionRules,
    decision: Decision | None = None,
) -> Submission:
    """Approve, reject, or request changes; the first decision wins.

    `expected_version` is the `version` the Moderator saw. A decision taken while the
    Submitter's working copy is open applies to the last submitted round, and the copy
    is discarded.
    """
    check_moderator(actor, submission, rules)
    if submission.version != expected_version:
        raise ModerationError("moderation.already_decided")
    action = Action(verdict.value)
    _transition(submission, action)
    if verdict is Verdict.APPROVE:
        if decision is not None:
            raise ModerationError("moderation.approval_has_message")
        discarded = submission.working_copy is not None
        return replace(_apply(submission, action, actor, now), working_copy_discarded=discarded)
    if decision is None or not decision.text.strip():
        raise ModerationError("moderation.decision_text_required")
    if decision.reason not in rules.reasons:
        raise ModerationError("moderation.decision_reason_required")
    discarded = submission.working_copy is not None
    return replace(
        _apply(
            submission, action, actor, now, message=decision.text.strip(), reason=decision.reason
        ),
        working_copy_discarded=discarded,
    )


def add_note(submission: Submission, actor: Actor, now: datetime, text: str) -> Submission:
    """A Moderation note is not a decision: a Moderator may add one to their own Submission."""
    if actor.kind is not ActorKind.USER or not actor.moderator:
        raise ModerationError("moderation.forbidden")
    if not text.strip():
        raise ModerationError("moderation.note_required")
    assert actor.user_id is not None
    note = ModerationNote(actor.user_id, now, text.strip())
    return replace(submission, notes=(*submission.notes, note))


def save_working_copy(
    submission: Submission, actor: Actor, now: datetime, content: Json
) -> Submission:
    """Autosave the Submitter's private copy: the draft itself, or the copy being
    revised while a decision is pending. A final Submission has none."""
    _require_submitter(submission, actor)
    if submission.status in FINAL:
        raise ModerationError("moderation.invalid_transition")
    return replace(
        submission, working_copy=content, last_autosave_at=now, working_copy_discarded=False
    )


def rebase_working_copy(
    submission: Submission,
    actor: Actor,
    now: datetime,
    *,
    target_id: int,
    content: Json,
    base_revision: int | None = None,
    base_revisions: tuple[int, ...] | None = None,
) -> Submission:
    """The Submitter opens the editor on an Outdated edit: its Base revision (and, for a
    merged target, its target) moves to the current Revision and the rebased content is
    the working copy. The round the Moderators see does not change."""
    if submission.target_id is None:
        raise ModerationError("moderation.cannot_rebase")
    if base_revisions is None:
        assert base_revision is not None
        base_revisions = (base_revision,)
    moved = replace(submission, target_id=target_id, base_revisions=base_revisions)
    return save_working_copy(moved, actor, now, content)


def expiry_deadline(submission: Submission, expiry_days: int) -> datetime | None:
    """When an unanswered `changes requested` Submission is retracted: `draft_expiry_days`
    after the later of the request and the Submitter's last autosave."""
    requested = submission.changes_requested_at
    if requested is None:
        return None
    last = max(requested, submission.last_autosave_at or requested)
    return last + timedelta(days=expiry_days)


def expire(submission: Submission, now: datetime, expiry_days: int) -> Submission:
    """The system retracts a `changes requested` Submission left without a response."""
    deadline = expiry_deadline(submission, expiry_days)
    if deadline is None or now < deadline:
        raise ModerationError("moderation.invalid_transition")
    return _apply(submission, Action.EXPIRE, Actor.system(), now)


def convert(submission: Submission, now: datetime, conversion_id: int) -> Submission:
    """The system retracts a `changes requested` Submission whose conversion into a
    documentation Submission was submitted; the log reads "Converted into …"."""
    return _apply(submission, Action.CONVERT, Actor.system(), now, related=conversion_id)


def can_start_again(submission: Submission) -> bool:
    """A rejected or retracted Submission offers its Submitter "Start again from this"."""
    return submission.status in {Status.REJECTED, Status.RETRACTED}


def link(
    submission: Submission, event: Event, actor: Actor, now: datetime, other: int
) -> Submission:
    """Record a retry or conversion link in the log; the status does not change."""
    entry = LogEntry(event, actor, now, None, None, None, other)
    return replace(submission, log=(*submission.log, entry))


def check_can_start_again(submission: Submission, actor: Actor) -> None:
    _require_submitter(submission, actor)
    if not can_start_again(submission):
        raise ModerationError("moderation.cannot_start_again")


def check_can_convert(submission: Submission, actor: Actor) -> None:
    """Only the Submitter converts, and only a Submission waiting for them."""
    _require_submitter(submission, actor)
    if submission.status is not Status.CHANGES_REQUESTED:
        raise ModerationError("moderation.cannot_convert")


MEDIA_RETENTION = timedelta(days=30)
"""The media of a rejected or retracted Submission are deleted this long after its final
transition (a platform constant)."""
STUB_AFTER = timedelta(days=365)
"""Twelve months after the final transition the Submission is reduced to a stub."""


def media_deletion_due(submission: Submission, now: datetime) -> bool:
    final = submission.final_at
    return (
        submission.status in {Status.REJECTED, Status.RETRACTED}
        and final is not None
        and now >= final + MEDIA_RETENTION
    )


def stub_due(submission: Submission, now: datetime) -> bool:
    final = submission.final_at
    return (
        submission.status in {Status.REJECTED, Status.RETRACTED}
        and submission.reduced_at is None
        and final is not None
        and now >= final + STUB_AFTER
    )


def reduce_to_stub(submission: Submission, now: datetime, labels: list[str]) -> Submission:
    """Delete the changesets and round snapshots; what remains is the kind and labels
    (kept here), target, dates, round count, log, and links."""
    if not stub_due(submission, now):
        raise ModerationError("moderation.invalid_transition")
    rounds = tuple(replace(round_, snapshot=None) for round_ in submission.rounds)
    return replace(
        submission,
        rounds=rounds,
        working_copy=None,
        reduced_at=now,
        stub={"labels": labels},
    )


NEVER_EDITED_AFTER = timedelta(hours=24)
"""A draft with nothing entered by the Submitter is discarded this long after its creation."""


def draft_deadline(submission: Submission, expiry_days: int) -> datetime:
    """When the system deletes a draft (with its media).

    A draft is *never edited* when no autosave stored anything by the Submitter: values the
    entry point pre-filled do not count, so a retry or a conversion draft is not edited
    until its Submitter saves it. It is discarded 24 hours after its creation. An edited
    draft is *abandoned* `draft_expiry_days` after its last autosave.
    """
    if submission.last_autosave_at is None:
        return submission.created_at + NEVER_EDITED_AFTER
    return submission.last_autosave_at + timedelta(days=expiry_days)
