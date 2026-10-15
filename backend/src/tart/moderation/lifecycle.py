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
}
"""Exactly the transitions of the Lifecycle table. The conversion into a documentation
Submission, which retracts the original, belongs to the retry and conversion ticket."""

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
) -> Submission:
    """Move to the next status, adding the log entry and, on a submission, the round."""
    status, event = _transition(submission, action)
    rounds = submission.rounds
    number = len(rounds) or None
    if action in {Action.SUBMIT, Action.REVISE, Action.RESUBMIT}:
        number = len(rounds) + 1
        rounds = (*rounds, Round(number, snapshot, now))
    entry = LogEntry(event, actor, now, number, message, reason)
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
