"""The Submission lifecycle and permission rules, without a database (contribution-and-moderation
spec, Lifecycle and Roles and permissions). Every identifier and text is fictional."""

from datetime import UTC, datetime, timedelta
from itertools import product

import pytest

from tart.archive import Kind
from tart.moderation import (
    TRANSITIONS,
    Action,
    Actor,
    Decision,
    DecisionRules,
    Event,
    ModerationError,
    Status,
    Submission,
    Verdict,
    add_note,
    convert,
    decide,
    draft_deadline,
    expire,
    expiry_deadline,
    media_deletion_due,
    reduce_to_stub,
    retract,
    save_working_copy,
    stub_due,
    submit,
)

NOW = datetime(2026, 9, 1, 10, 0, tzinfo=UTC)
SUBMITTER = Actor.user(1)
MODERATOR = Actor.user(2, moderator=True)
OTHER_MODERATOR = Actor.user(3, moderator=True)
RULES = DecisionRules(self_approval=False, reasons=frozenset({"people", "incomplete", "duplicate"}))
REASON = Decision("incomplete", "The second photo does not show the stencil.")


def at(hours: float = 0) -> datetime:
    return NOW + timedelta(hours=hours)


def draft(submitter: Actor = SUBMITTER) -> Submission:
    return Submission(7, submitter.user_id, Kind.ARTWORK, None, (), Status.DRAFT, NOW)


def submitted(submitter: Actor = SUBMITTER) -> Submission:
    return submit(draft(submitter), submitter, at(1), {"title": "First"}, note="Seen on a shutter")


def changes_requested(submitter: Actor = SUBMITTER) -> Submission:
    return decide(
        submitted(submitter),
        MODERATOR,
        Verdict.REQUEST_CHANGES,
        at(2),
        expected_version=1,
        rules=RULES,
        decision=REASON,
    )


def in_status(status: Status) -> Submission:
    match status:
        case Status.DRAFT:
            return draft()
        case Status.SUBMITTED:
            return submitted()
        case Status.CHANGES_REQUESTED:
            return changes_requested()
        case Status.APPROVED:
            return decide(
                submitted(), MODERATOR, Verdict.APPROVE, at(2), expected_version=1, rules=RULES
            )
        case Status.REJECTED:
            return decide(
                submitted(),
                MODERATOR,
                Verdict.REJECT,
                at(2),
                expected_version=1,
                rules=RULES,
                decision=REASON,
            )
        case _:
            return retract(submitted(), SUBMITTER, at(2))


def attempt(submission: Submission, action: Action) -> Submission:
    """Do `action` as the actor the table names for it, with valid arguments."""
    version = submission.version
    match action:
        case Action.SUBMIT | Action.REVISE | Action.RESUBMIT:
            return submit(submission, SUBMITTER, at(5), {"title": "Next"})
        case Action.RETRACT:
            return retract(submission, SUBMITTER, at(5))
        case Action.EXPIRE:
            return expire(submission, at(24 * 400), 90)
        case Action.CONVERT:
            return convert(submission, at(5), 99)
        case Action.APPROVE:
            return decide(
                submission, MODERATOR, Verdict.APPROVE, at(5), expected_version=version, rules=RULES
            )
        case _:
            return decide(
                submission,
                MODERATOR,
                Verdict(action.value),
                at(5),
                expected_version=version,
                rules=RULES,
                decision=REASON,
            )


SUBMITTING = frozenset({Action.SUBMIT, Action.REVISE, Action.RESUBMIT})


# Acceptance criterion 2.
@pytest.mark.parametrize(
    ("status", "action"), [pair for pair in product(Status, Action) if pair[1] not in SUBMITTING]
)
def test_the_status_transitions_are_exactly_those_of_the_lifecycle_table(
    status: Status, action: Action
) -> None:
    submission = in_status(status)

    if (status, action) in TRANSITIONS:
        assert attempt(submission, action).status is TRANSITIONS[status, action][0]
    else:
        with pytest.raises(ModerationError) as refused:
            attempt(submission, action)
        assert refused.value.code == "moderation.invalid_transition"


@pytest.mark.parametrize("status", list(Status))
def test_submitting_is_the_submit_revise_or_resubmit_the_status_allows(status: Status) -> None:
    submission = in_status(status)
    allowed = {
        Status.DRAFT: Event.SUBMITTED,
        Status.SUBMITTED: Event.REVISED,
        Status.CHANGES_REQUESTED: Event.RESUBMITTED,
    }

    if status in allowed:
        assert attempt(submission, Action.SUBMIT).log[-1].event is allowed[status]
    else:
        with pytest.raises(ModerationError) as refused:
            attempt(submission, Action.SUBMIT)
        assert refused.value.code == "moderation.invalid_transition"


def test_the_table_has_the_rows_of_the_spec_and_no_others() -> None:
    assert set(TRANSITIONS) == {
        (Status.DRAFT, Action.SUBMIT),
        (Status.SUBMITTED, Action.REVISE),
        (Status.CHANGES_REQUESTED, Action.RESUBMIT),
        (Status.SUBMITTED, Action.APPROVE),
        (Status.SUBMITTED, Action.REJECT),
        (Status.CHANGES_REQUESTED, Action.REJECT),
        (Status.SUBMITTED, Action.REQUEST_CHANGES),
        (Status.SUBMITTED, Action.RETRACT),
        (Status.CHANGES_REQUESTED, Action.RETRACT),
        (Status.CHANGES_REQUESTED, Action.EXPIRE),
        (Status.CHANGES_REQUESTED, Action.CONVERT),
    }


@pytest.mark.parametrize("final", [Status.APPROVED, Status.REJECTED, Status.RETRACTED])
def test_a_final_status_accepts_no_further_transition(final: Status) -> None:
    assert not [key for key in TRANSITIONS if key[0] is final]
    submission = in_status(final)
    with pytest.raises(ModerationError):
        retract(submission, SUBMITTER, at(9))
    with pytest.raises(ModerationError):
        submit(submission, SUBMITTER, at(9), {})
    with pytest.raises(ModerationError):
        save_working_copy(submission, SUBMITTER, at(9), {})


# Acceptance criterion 3.
def test_every_transition_adds_a_log_entry_and_each_submission_a_numbered_round() -> None:
    first = submitted()
    revised = submit(first, SUBMITTER, at(2), {"title": "Second"})
    asked = decide(
        revised,
        MODERATOR,
        Verdict.REQUEST_CHANGES,
        at(3),
        expected_version=revised.version,
        rules=RULES,
        decision=REASON,
    )
    resubmitted = submit(asked, SUBMITTER, at(4), {"title": "Third"}, note="Added the photo")
    withdrawn = retract(resubmitted, SUBMITTER, at(5))

    assert [(entry.event, entry.actor.user_id, entry.at) for entry in withdrawn.log] == [
        (Event.SUBMITTED, 1, at(1)),
        (Event.REVISED, 1, at(2)),
        (Event.CHANGES_REQUESTED, 2, at(3)),
        (Event.RESUBMITTED, 1, at(4)),
        (Event.RETRACTED, 1, at(5)),
    ]
    assert [(r.number, r.snapshot) for r in withdrawn.rounds] == [
        (1, {"title": "First"}),
        (2, {"title": "Second"}),
        (3, {"title": "Third"}),
    ]
    assert withdrawn.log[0].message == "Seen on a shutter"
    assert withdrawn.log[3].message == "Added the photo"
    assert withdrawn.first_submitted_at == at(1)


# Acceptance criterion 4.
@pytest.mark.parametrize("verdict", [Verdict.REJECT, Verdict.REQUEST_CHANGES])
def test_rejecting_or_requesting_changes_needs_a_reason_and_text(verdict: Verdict) -> None:
    submission = submitted()

    def refused(decision: Decision | None) -> str:
        with pytest.raises(ModerationError) as error:
            decide(
                submission,
                MODERATOR,
                verdict,
                at(2),
                expected_version=1,
                rules=RULES,
                decision=decision,
            )
        return error.value.code

    assert refused(None) == "moderation.decision_text_required"
    assert refused(Decision("incomplete", "   ")) == "moderation.decision_text_required"
    assert refused(Decision("", "Something")) == "moderation.decision_reason_required"
    assert refused(Decision("not_a_reason", "Something")) == "moderation.decision_reason_required"


@pytest.mark.parametrize("verdict", [Verdict.REJECT, Verdict.REQUEST_CHANGES])
def test_the_decision_message_is_stored_with_its_reason(verdict: Verdict) -> None:
    decided = decide(
        submitted(),
        MODERATOR,
        verdict,
        at(2),
        expected_version=1,
        rules=RULES,
        decision=Decision("duplicate", " Same wall as an approved record. "),
    )

    assert decided.log[-1].reason == "duplicate"
    assert decided.log[-1].message == "Same wall as an approved record."


def test_approving_accepts_no_decision_message() -> None:
    with pytest.raises(ModerationError) as error:
        decide(
            submitted(),
            MODERATOR,
            Verdict.APPROVE,
            at(2),
            expected_version=1,
            rules=RULES,
            decision=REASON,
        )

    assert error.value.code == "moderation.approval_has_message"


# Acceptance criterion 31 and 44.
def test_without_self_approval_every_decision_on_ones_own_submission_is_refused() -> None:
    own = submitted(MODERATOR)
    for verdict in Verdict:
        with pytest.raises(ModerationError) as error:
            decide(
                own,
                MODERATOR,
                verdict,
                at(2),
                expected_version=own.version,
                rules=RULES,
                decision=REASON,
            )
        assert error.value.code == "moderation.own_submission"


def test_without_self_approval_a_moderator_may_retract_revise_and_note_their_own() -> None:
    own = submitted(MODERATOR)

    noted = add_note(own, MODERATOR, at(2), "Checking the second file")
    revised = submit(noted, MODERATOR, at(3), {"title": "Revised"})
    withdrawn = retract(revised, MODERATOR, at(4))

    assert [note.text for note in noted.notes] == ["Checking the second file"]
    assert withdrawn.status is Status.RETRACTED


@pytest.mark.parametrize("verdict", list(Verdict))
def test_with_self_approval_a_moderator_decides_on_their_own_submission(verdict: Verdict) -> None:
    rules = DecisionRules(self_approval=True, reasons=RULES.reasons)
    own = submitted(MODERATOR)

    decided = decide(
        own,
        MODERATOR,
        verdict,
        at(2),
        expected_version=1,
        rules=rules,
        decision=REASON if verdict is not Verdict.APPROVE else None,
    )

    # Submitter and deciding Moderator coincide in the log.
    assert decided.submitter_id == decided.log[-1].actor.user_id == MODERATOR.user_id


def test_a_user_without_the_role_takes_no_decision_and_writes_no_note() -> None:
    for call in (
        lambda: decide(
            submitted(), SUBMITTER, Verdict.APPROVE, at(2), expected_version=1, rules=RULES
        ),
        lambda: add_note(submitted(), Actor.user(9), at(2), "Hello"),
    ):
        with pytest.raises(ModerationError) as error:
            call()
        assert error.value.code == "moderation.forbidden"


def test_only_the_submitter_submits_revises_and_retracts() -> None:
    for call in (
        lambda: retract(submitted(), MODERATOR, at(2)),
        lambda: submit(submitted(), MODERATOR, at(2), {}),
        lambda: submit(draft(), Actor.user(9), at(2), {}),
    ):
        with pytest.raises(ModerationError) as error:
            call()
        assert error.value.code == "moderation.not_submitter"


# Acceptance criterion 32.
def test_a_decision_on_a_state_the_moderator_did_not_see_is_refused() -> None:
    seen = submitted()
    first = decide(
        seen, MODERATOR, Verdict.APPROVE, at(2), expected_version=seen.version, rules=RULES
    )

    with pytest.raises(ModerationError) as error:
        decide(
            first,
            OTHER_MODERATOR,
            Verdict.REJECT,
            at(3),
            expected_version=seen.version,
            rules=RULES,
            decision=REASON,
        )

    assert error.value.code == "moderation.already_decided"


def test_a_revision_while_a_moderator_reads_makes_the_decision_stale() -> None:
    seen = submitted()
    revised = submit(seen, SUBMITTER, at(2), {"title": "Revised"})

    with pytest.raises(ModerationError) as error:
        decide(
            revised,
            MODERATOR,
            Verdict.APPROVE,
            at(3),
            expected_version=seen.version,
            rules=RULES,
        )

    assert error.value.code == "moderation.already_decided"


# Acceptance criterion 53.
def test_revising_a_submitted_submission_opens_a_new_round_and_keeps_the_status() -> None:
    revised = submit(submitted(), SUBMITTER, at(2), {"title": "Revised"})

    assert revised.status is Status.SUBMITTED
    assert [r.number for r in revised.rounds] == [1, 2]
    assert revised.log[-1].event is Event.REVISED
    assert revised.first_submitted_at == at(1)


def test_a_decision_with_a_working_copy_open_applies_to_the_last_round_and_discards_it() -> None:
    working = save_working_copy(submitted(), SUBMITTER, at(2), {"title": "Draft of a revision"})

    approved = decide(
        working, MODERATOR, Verdict.APPROVE, at(3), expected_version=working.version, rules=RULES
    )

    assert approved.status is Status.APPROVED
    assert [r.snapshot for r in approved.rounds] == [{"title": "First"}]
    assert approved.working_copy is None
    assert approved.working_copy_discarded

    saved_again = save_working_copy(submitted(), SUBMITTER, at(2), {"title": "x"})
    assert not saved_again.working_copy_discarded


def test_a_decision_without_a_working_copy_discards_nothing() -> None:
    approved = in_status(Status.APPROVED)

    assert not approved.working_copy_discarded


# Acceptance criterion 55.
def test_a_moderator_can_reject_but_not_approve_in_changes_requested() -> None:
    asked = changes_requested()

    with pytest.raises(ModerationError) as error:
        decide(
            asked, MODERATOR, Verdict.APPROVE, at(5), expected_version=asked.version, rules=RULES
        )
    rejected = decide(
        asked,
        MODERATOR,
        Verdict.REJECT,
        at(5),
        expected_version=asked.version,
        rules=RULES,
        decision=REASON,
    )

    assert error.value.code == "moderation.invalid_transition"
    assert rejected.status is Status.REJECTED


def test_changes_requested_expires_after_the_later_of_the_request_and_the_last_autosave() -> None:
    asked = changes_requested()
    requested = at(2)
    assert expiry_deadline(asked, 90) == requested + timedelta(days=90)

    worked = save_working_copy(asked, SUBMITTER, requested + timedelta(days=30), {"title": "x"})
    deadline = requested + timedelta(days=120)
    assert expiry_deadline(worked, 90) == deadline

    with pytest.raises(ModerationError):
        expire(worked, deadline - timedelta(seconds=1), 90)
    expired = expire(worked, deadline, 90)
    assert expired.status is Status.RETRACTED
    assert expired.log[-1].event is Event.EXPIRED
    assert expired.log[-1].actor == Actor.system()


def test_only_changes_requested_has_an_expiry_deadline() -> None:
    assert expiry_deadline(submitted(), 90) is None
    assert expiry_deadline(draft(), 90) is None


# Acceptance criterion 10: the draft clocks.
def test_a_draft_never_edited_is_discarded_24_hours_after_creation() -> None:
    assert draft_deadline(draft(), 90) == at(24)


def test_an_edited_draft_is_abandoned_the_expiry_after_its_last_autosave() -> None:
    saved = save_working_copy(draft(), SUBMITTER, at(30), {"title": "First"})

    assert draft_deadline(saved, 90) == at(30) + timedelta(days=90)


# The system retracts a Submission whose conversion was submitted.
def test_the_conversion_retracts_the_original_and_links_it_to_the_conversion() -> None:
    converted = convert(changes_requested(), at(9), 12)

    assert converted.status is Status.RETRACTED
    entry = converted.log[-1]
    assert (entry.event, entry.actor, entry.related) == (Event.CONVERTED_INTO, Actor.system(), 12)


# Acceptance criterion 56: retention of rejected and retracted Submissions.
def test_the_media_go_30_days_and_the_changesets_12_months_after_the_final_transition() -> None:
    rejected = decide(
        submitted(),
        MODERATOR,
        Verdict.REJECT,
        at(2),
        expected_version=1,
        rules=RULES,
        decision=REASON,
    )

    assert not media_deletion_due(rejected, at(2) + timedelta(days=30) - timedelta(seconds=1))
    assert media_deletion_due(rejected, at(2) + timedelta(days=30))
    assert not stub_due(rejected, at(2) + timedelta(days=364))
    stub = reduce_to_stub(rejected, at(2) + timedelta(days=365), ["adds_documentation"])
    assert [round_.snapshot for round_ in stub.rounds] == [None]
    assert (len(stub.rounds), stub.log, stub.stub) == (
        1,
        rejected.log,
        {"labels": ["adds_documentation"]},
    )
    assert not stub_due(stub, at(2) + timedelta(days=999))


@pytest.mark.parametrize("status", [Status.DRAFT, Status.SUBMITTED, Status.APPROVED])
def test_only_rejected_and_retracted_submissions_have_retention(status: Status) -> None:
    submission = in_status(status)
    far = at(24 * 900)

    assert not media_deletion_due(submission, far)
    assert not stub_due(submission, far)
