"""`/api/contributions`: drafts, autosave, submit, retract, "Start again from this", conversion,
and decisions (Contribution and moderation spec, Lifecycle, Rate limits, Terms of use).

    GET    /api/contributions                    the User's Submissions, drafts included
    POST   /api/contributions                    start a draft: a new record, or an edit of one
    GET    /api/contributions/terms              whether the Review step asks for acceptance
    GET    /api/contributions/{id}               the Submission, for its Submitter and Moderators
    PUT    /api/contributions/{id}/working-copy  autosave the Submitter's private copy
    POST   /api/contributions/{id}/submit        submit, revise, or resubmit (the status decides)
    POST   /api/contributions/{id}/retract       the Submitter withdraws it before a decision
    DELETE /api/contributions/{id}               delete a draft with its media
    POST   /api/contributions/{id}/start-again   a new draft from a rejected or retracted one
    POST   /api/contributions/{id}/convert       a draft that adds its documentation to an Artwork
    POST   /api/contributions/{id}/decision      a Moderator approves, rejects, or requests changes
    POST   /api/contributions/{id}/notes         a Moderator adds a Moderation note
    GET    /api/contributions/{id}/comparison    the current record against the proposed data

A Submission answers 404 to everyone but its Submitter and the Moderators. The API never
names a Moderator to the Submitter, and never sends them a Moderation note: the log reads
"a Moderator". A Submitter's email address is sent to no one. Refusals carry a stable,
translatable error code `{"code": ...}` (ADR 0008); the per-User limits answer 429 with the
code and `retry_after`.
"""

from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from tart import moderation
from tart.api.auth import (
    SIGN_IN_REQUIRED,
    Clock,
    Error,
    current_user,
    get_clock,
    get_configuration,
    get_engine,
    get_key,
)
from tart.api.limits import LimitedError, limited
from tart.api.media import get_storage
from tart.archive.errors import ArchiveRuleViolation
from tart.archive.records import Kind
from tart.archive.rules import InstanceRules
from tart.archive_persistence import rules_from_instance
from tart.archive_read import (
    Reader,
    RecordMergedError,
    RecordNotFoundError,
    RecordWithdrawnError,
    Viewer,
)
from tart.archive_read import views as archive_views
from tart.auth.sessions import SessionUser
from tart.auth.tables import user_account
from tart.config import Configuration
from tart.moderation import (
    ActorKind,
    Decision,
    DecisionRules,
    ModerationError,
    Status,
    Submission,
    Verdict,
)
from tart.moderation_persistence import (
    archive_access,
    contribution,
    service,
    store,
    terms,
)
from tart.moderation_persistence import comparison as compare
from tart.moderation_persistence.limits import LimitReached
from tart.storage import Storage

router = APIRouter(prefix="/api/contributions")

_STATUS = {
    "moderation.forbidden": 403,
    "moderation.own_submission": 403,
    "moderation.not_submitter": 403,
    "moderation.unknown_submission": 404,
    "moderation.unknown_target": 404,
    "moderation.invalid_transition": 409,
    "moderation.already_decided": 409,
    "moderation.outdated": 409,
    "moderation.cannot_rebase": 409,
    "moderation.cannot_start_again": 409,
    "moderation.cannot_convert": 409,
    "moderation.target_withdrawn": 409,
    "moderation.target_merged": 409,
    "moderation.terms_not_accepted": 409,
}
"""Every other `ModerationError` and every `ArchiveRuleViolation` is a 422."""

_ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": Error},
    403: {"model": Error},
    404: {"model": Error},
    409: {"model": Error},
    422: {"model": Error},
    429: {"model": LimitedError},
}


def get_archive_rules(request: Request) -> InstanceRules:
    """The archive's rules from the Instance configuration, built once."""
    state = request.app.state
    if not hasattr(state, "archive_rules"):
        state.archive_rules = rules_from_instance(state.configuration.instance)
    return state.archive_rules


def _refused(code: str, status: int) -> JSONResponse:
    return JSONResponse({"code": code}, status_code=status)


def _failure(error: Exception) -> JSONResponse:
    if isinstance(error, LimitReached):
        return limited(error.code, error.wait)
    code = error.code  # type: ignore[attr-defined]
    return _refused(code, _STATUS.get(code, 422) if isinstance(error, ModerationError) else 422)


FAILURES = (ModerationError, ArchiveRuleViolation, LimitReached)


type Caller = SessionUser | None


class Person(BaseModel):
    number: int
    display_name: str


class ActorOut(BaseModel):
    role: Literal["submitter", "moderator", "system"]
    user: Person | None = None
    """Moderators only: who acted. A Moderator's identity is never sent to anyone else."""


class LogEntryOut(BaseModel):
    event: str
    at: datetime
    round: int | None
    message: str | None
    reason: str | None
    actor: ActorOut
    related_submission: int | None
    """The other Submission of a retry or conversion link."""


class NoteOut(BaseModel):
    author: Person
    at: datetime
    text: str


class SubmissionOut(BaseModel):
    id: int
    status: Status
    target_kind: Kind
    intent: Literal["create", "edit"]
    target_id: int | None
    base_revisions: list[int]
    labels: list[str]
    """Derived from the changeset, never entered."""
    version: int
    """The state a Moderator decides on; a decision on an older one is refused."""
    submitter: Person
    created_at: datetime
    first_submitted_at: datetime | None
    rounds: int
    last_round: Any | None
    """The changeset of the last submitted round; null in a stub."""
    working_copy: Any | None = None
    """The Submitter's private copy: the draft, or the revision in progress. Submitter only."""
    working_copy_discarded: bool = False
    """A decision discarded the working copy. Submitter only."""
    last_autosave_at: datetime | None = None
    decisions: list[Verdict] = []
    """What the caller may decide on now: a Moderator's options for this status, none on their
    own Submission under `self_approval = false`, no approval while Outdated."""
    notes: list[NoteOut] = []
    """The Moderation notes, immutable and in order. Moderators only: always empty otherwise."""
    outdated: list[str]
    """Why the last round is Outdated, empty when it is not."""
    expires_at: datetime | None
    """When a Submission in `changes requested` is retracted if nothing is saved."""
    retry_of: int | None
    converts: int | None
    stub: bool
    log: list[LogEntryOut]


class SubmissionSummary(BaseModel):
    id: int
    status: Status
    target_kind: Kind
    intent: Literal["create", "edit"]
    target_id: int | None
    labels: list[str]
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None


class SubmissionList(BaseModel):
    items: list[SubmissionSummary]


async def people_of(connection: AsyncConnection, ids: set[int]) -> dict[int, Person]:
    if not ids:
        return {}
    rows = await connection.execute(
        select(user_account.c.id, user_account.c.display_name).where(user_account.c.id.in_(ids))
    )
    return {row.id: Person(number=row.id, display_name=row.display_name) for row in rows}


def _labels(submission: Submission) -> list[str]:
    return list(moderation.labels_of(submission))


def intent_of(submission: Submission) -> Literal["create", "edit"]:
    return moderation.derive_kind(submission).intent.value  # type: ignore[return-value]


def _expires_at(submission: Submission, expiry_days: int) -> datetime | None:
    return moderation.expiry_deadline(submission, expiry_days)


def _summary(submission: Submission, expiry_days: int) -> SubmissionSummary:
    last = [submission.created_at, submission.last_autosave_at, *(e.at for e in submission.log)]
    return SubmissionSummary(
        id=submission.id,
        status=submission.status,
        target_kind=submission.target_kind,
        intent=intent_of(submission),
        target_id=submission.target_id,
        labels=_labels(submission),
        created_at=submission.created_at,
        updated_at=max(each for each in last if each is not None),
        expires_at=_expires_at(submission, expiry_days),
    )


def _decisions(
    submission: Submission, viewer: SessionUser, self_approval: bool, outdated: bool
) -> list[Verdict]:
    """The decisions this caller may take now: a Moderator's, by status; none on their own
    Submission under `self_approval = false`; no approval of an Outdated one."""
    if not viewer.moderator or (viewer.id == submission.submitter_id and not self_approval):
        return []
    return [
        verdict
        for verdict in Verdict
        if (submission.status, moderation.Action(verdict.value)) in moderation.TRANSITIONS
        and not (verdict is Verdict.APPROVE and outdated)
        and submission.rounds
    ]


async def _detail(
    connection: AsyncConnection,
    submission: Submission,
    viewer: SessionUser,
    configuration: Configuration,
) -> SubmissionOut:
    settings = configuration.instance.settings
    expiry_days = settings.community.draft_expiry_days
    own = viewer.id == submission.submitter_id
    ids = {submission.submitter_id}
    if viewer.moderator:
        ids |= {e.actor.user_id for e in submission.log if e.actor.user_id is not None}
        ids |= {note.author_id for note in submission.notes}
    people = await people_of(connection, ids)
    pseudonym = Person(number=submission.submitter_id, display_name="")

    def actor(entry: moderation.LogEntry) -> ActorOut:
        if entry.actor.kind is ActorKind.SYSTEM:
            return ActorOut(role="system")
        if entry.actor.user_id == submission.submitter_id:
            return ActorOut(role="submitter")
        return ActorOut(
            role="moderator",
            user=people.get(entry.actor.user_id or 0) if viewer.moderator else None,
        )

    outdated: list[str] = []
    if submission.status in {Status.SUBMITTED, Status.CHANGES_REQUESTED} and submission.rounds:
        outdated = [reason.value for reason in await service.outdated(connection, submission.id)]
    return SubmissionOut(
        id=submission.id,
        status=submission.status,
        target_kind=submission.target_kind,
        intent=intent_of(submission),
        target_id=submission.target_id,
        base_revisions=list(submission.base_revisions),
        labels=_labels(submission),
        version=submission.version,
        submitter=people.get(submission.submitter_id, pseudonym),
        created_at=submission.created_at,
        first_submitted_at=submission.first_submitted_at,
        rounds=len(submission.rounds),
        last_round=submission.rounds[-1].snapshot if submission.rounds else None,
        working_copy=submission.working_copy if own else None,
        working_copy_discarded=submission.working_copy_discarded if own else False,
        last_autosave_at=submission.last_autosave_at if own else None,
        decisions=_decisions(submission, viewer, settings.community.self_approval, bool(outdated)),
        notes=[
            NoteOut(
                author=people.get(note.author_id, Person(number=note.author_id, display_name="")),
                at=note.at,
                text=note.text,
            )
            for note in submission.notes
        ]
        if viewer.moderator
        else [],
        outdated=outdated,
        expires_at=_expires_at(submission, expiry_days),
        retry_of=submission.retry_of,
        converts=submission.converts,
        stub=submission.reduced_at is not None,
        log=[
            LogEntryOut(
                event=entry.event.value,
                at=entry.at,
                round=entry.round,
                message=entry.message,
                reason=entry.reason,
                actor=actor(entry),
                related_submission=entry.related,
            )
            for entry in submission.log
        ],
    )


async def _visible(
    connection: AsyncConnection, submission_id: int, user: SessionUser
) -> Submission | None:
    """The Submission, if the caller is its Submitter or a Moderator; else as if absent."""
    submission = await store.load(connection, submission_id)
    if submission is None or not (user.moderator or user.id == submission.submitter_id):
        return None
    return submission


def _expiry_days(configuration: Configuration) -> int:
    return configuration.instance.settings.community.draft_expiry_days


async def _detail_of(
    engine: AsyncEngine, submission_id: int, user: SessionUser, configuration: Configuration
) -> SubmissionOut | JSONResponse:
    async with engine.begin() as connection:
        submission = await _visible(connection, submission_id, user)
        if submission is None:
            return _refused("moderation.unknown_submission", 404)
        return await _detail(connection, submission, user, configuration)


async def _hidden(
    engine: AsyncEngine, submission_id: int, user: SessionUser
) -> JSONResponse | None:
    """404 unless the caller may see the Submission at all."""
    async with engine.connect() as connection:
        if await _visible(connection, submission_id, user) is None:
            return _refused("moderation.unknown_submission", 404)
    return None


class TermsState(BaseModel):
    version: int
    """The current `terms.version`."""
    accepted_version: int | None
    acceptance_required: bool
    """Whether the Review and submit step carries the acceptance checkbox."""


@router.get("/terms", response_model=TermsState, responses={401: {"model": Error}})
async def terms_state(
    user: Annotated[Caller, Depends(current_user)],
    configuration: Annotated[Configuration, Depends(get_configuration)],
    engine: Annotated[AsyncEngine, Depends(get_engine)],
) -> TermsState | JSONResponse:
    """The terms the User must have accepted to submit, and the version they accepted."""
    if user is None:
        return _refused(SIGN_IN_REQUIRED, 401)
    current = configuration.instance.settings.terms.version
    async with engine.connect() as connection:
        accepted = await terms.accepted_version(connection, user.id)
    return TermsState(
        version=current,
        accepted_version=accepted,
        acceptance_required=terms.acceptance_needed(accepted, current),
    )


@router.get("", response_model=SubmissionList, responses={401: {"model": Error}})
async def my_contributions(
    user: Annotated[Caller, Depends(current_user)],
    configuration: Annotated[Configuration, Depends(get_configuration)],
    engine: Annotated[AsyncEngine, Depends(get_engine)],
    status: Status | None = None,
) -> SubmissionList | JSONResponse:
    """The User's own Submissions, drafts included, the latest first; filter by status."""
    if user is None:
        return _refused(SIGN_IN_REQUIRED, 401)
    expiry_days = _expiry_days(configuration)
    async with engine.connect() as connection:
        found = [
            await store.load(connection, each)
            for each in await store.of_submitter(connection, user.id, status)
        ]
    return SubmissionList(items=[_summary(each, expiry_days) for each in found if each])


class StartBody(BaseModel):
    target_kind: Kind | None = None
    """The kind of the new record; for an edit, the kind of the record (optional)."""
    target_id: int | None = None
    """The record to edit; absent for a new record."""


@router.post("", status_code=201, response_model=SubmissionOut, responses=_ERRORS)
async def start_draft(
    body: StartBody,
    user: Annotated[Caller, Depends(current_user)],
    configuration: Annotated[Configuration, Depends(get_configuration)],
    engine: Annotated[AsyncEngine, Depends(get_engine)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> SubmissionOut | JSONResponse:
    """Start a contribution as a draft. A new record is created only of the kinds a
    Submission may create as its primary target; an edit stores the record's current
    Revision as its Base revision. At most 20 drafts are open at once."""
    if user is None:
        return _refused(SIGN_IN_REQUIRED, 401)
    try:
        async with engine.begin() as connection:
            draft = await contribution.start(
                connection,
                user.id,
                body.target_kind,
                body.target_id,
                clock(),
                expiry_days=_expiry_days(configuration),
            )
            return await _detail(connection, draft, user, configuration)
    except FAILURES as error:
        return _failure(error)


@router.get(
    "/{submission_id}",
    response_model=SubmissionOut,
    responses={401: {"model": Error}, 404: {"model": Error}},
)
async def read_submission(
    submission_id: int,
    user: Annotated[Caller, Depends(current_user)],
    configuration: Annotated[Configuration, Depends(get_configuration)],
    engine: Annotated[AsyncEngine, Depends(get_engine)],
) -> SubmissionOut | JSONResponse:
    """A Submission, for its Submitter and for Moderators only."""
    if user is None:
        return _refused(SIGN_IN_REQUIRED, 401)
    return await _detail_of(engine, submission_id, user, configuration)


@router.get(
    "/{submission_id}/target",
    response_model=archive_views.EditSource,
    responses=_ERRORS,
)
async def edit_source(
    submission_id: int,
    user: Annotated[Caller, Depends(current_user)],
    engine: Annotated[AsyncEngine, Depends(get_engine)],
) -> archive_views.EditSource | JSONResponse:
    """The record an edit Submission changes, as its editor starts from it: stored fields
    with Redactions applied, the words of the records it links to, and, for a Location, how
    many Artworks it carries. A Submission that creates a record has none (404)."""
    if user is None:
        return _refused(SIGN_IN_REQUIRED, 401)
    async with engine.connect() as connection:
        submission = await _visible(connection, submission_id, user)
        if submission is None:
            return _refused("moderation.unknown_submission", 404)
        if submission.target_id is None:
            return _refused("moderation.unknown_target", 404)
        try:
            return await Reader(connection, Viewer(moderator=False)).editable(
                submission.target_kind, submission.target_id
            )
        except RecordNotFoundError, RecordWithdrawnError, RecordMergedError:
            return _refused("moderation.unknown_target", 404)


class WorkingCopyBody(BaseModel):
    content: dict[str, Any]
    """`{"operations": [...], "initial_condition": ...}`, validated only on submit."""


class Saved(BaseModel):
    last_autosave_at: datetime


@router.put("/{submission_id}/working-copy", response_model=Saved, responses=_ERRORS)
async def autosave(
    submission_id: int,
    body: WorkingCopyBody,
    user: Annotated[Caller, Depends(current_user)],
    engine: Annotated[AsyncEngine, Depends(get_engine)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> Saved | JSONResponse:
    """Store the Submitter's private copy. Nothing is validated: the form never blocks.
    A twenty-first uploaded Documentation item is refused (`moderation.too_many_files`)."""
    if user is None:
        return _refused(SIGN_IN_REQUIRED, 401)
    if (hidden := await _hidden(engine, submission_id, user)) is not None:
        return hidden
    try:
        async with engine.begin() as connection:
            saved = await contribution.autosave(
                connection, submission_id, user.id, body.content, clock()
            )
    except FAILURES as error:
        return _failure(error)
    assert saved.last_autosave_at is not None
    return Saved(last_autosave_at=saved.last_autosave_at)


class SubmitBody(BaseModel):
    content: dict[str, Any] | None = None
    """The changeset to submit; absent, the stored working copy."""
    note: str | None = None
    """The optional note to Moderators, one per round."""
    accept_terms: bool = False
    """The Review step's acceptance, needed only when `/terms` says so."""


@router.post("/{submission_id}/submit", response_model=SubmissionOut, responses=_ERRORS)
async def submit(
    submission_id: int,
    body: SubmitBody,
    user: Annotated[Caller, Depends(current_user)],
    configuration: Annotated[Configuration, Depends(get_configuration)],
    engine: Annotated[AsyncEngine, Depends(get_engine)],
    clock: Annotated[Clock, Depends(get_clock)],
    key: Annotated[bytes, Depends(get_key)],
    rules: Annotated[InstanceRules, Depends(get_archive_rules)],
) -> SubmissionOut | JSONResponse:
    """Submit a draft, revise a `submitted` Submission, or resubmit one with changes
    requested; each opens a new round. The content must validate against the current
    archive, and the User must have accepted the current terms. Submissions and
    resubmissions are limited to 20 per 24 hours (revisions are not)."""
    if user is None:
        return _refused(SIGN_IN_REQUIRED, 401)
    if (hidden := await _hidden(engine, submission_id, user)) is not None:
        return hidden
    try:
        async with engine.begin() as connection:
            submitted = await contribution.submit(
                connection,
                submission_id,
                user.id,
                body.content,
                clock(),
                rules,
                terms_version=configuration.instance.settings.terms.version,
                accept_terms=body.accept_terms,
                key=key,
                note=body.note,
            )
            return await _detail(connection, submitted, user, configuration)
    except FAILURES as error:
        return _failure(error)


@router.post("/{submission_id}/retract", response_model=SubmissionOut, responses=_ERRORS)
async def retract(
    submission_id: int,
    user: Annotated[Caller, Depends(current_user)],
    configuration: Annotated[Configuration, Depends(get_configuration)],
    engine: Annotated[AsyncEngine, Depends(get_engine)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> SubmissionOut | JSONResponse:
    """The Submitter withdraws a `submitted` or `changes requested` Submission."""
    if user is None:
        return _refused(SIGN_IN_REQUIRED, 401)
    if (hidden := await _hidden(engine, submission_id, user)) is not None:
        return hidden
    try:
        async with engine.begin() as connection:
            retracted = await service.retract(connection, submission_id, user.id, clock())
            return await _detail(connection, retracted, user, configuration)
    except FAILURES as error:
        return _failure(error)


@router.delete("/{submission_id}", status_code=204, response_model=None, responses=_ERRORS)
async def delete_draft(
    submission_id: int,
    user: Annotated[Caller, Depends(current_user)],
    engine: Annotated[AsyncEngine, Depends(get_engine)],
    storage: Annotated[Storage, Depends(get_storage)],
) -> Response:
    """Delete a draft with its media. Deleting a retry or a conversion draft leaves the
    Submission it came from as it was."""
    if user is None:
        return _refused(SIGN_IN_REQUIRED, 401)  # type: ignore[return-value]
    if (hidden := await _hidden(engine, submission_id, user)) is not None:
        return hidden  # type: ignore[return-value]
    try:
        await contribution.delete_draft(engine, storage, submission_id, user.id)
    except FAILURES as error:
        return _failure(error)  # type: ignore[return-value]
    return Response(status_code=204)


@router.post(
    "/{submission_id}/start-again", status_code=201, response_model=SubmissionOut, responses=_ERRORS
)
async def start_again(
    submission_id: int,
    user: Annotated[Caller, Depends(current_user)],
    configuration: Annotated[Configuration, Depends(get_configuration)],
    engine: Annotated[AsyncEngine, Depends(get_engine)],
    storage: Annotated[Storage, Depends(get_storage)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> SubmissionOut | JSONResponse:
    """ "Start again from this": a draft pre-filled from the last round of a rejected or
    retracted Submission, its files copied, an edit rebased onto the current Revision. Both
    Submissions record the link."""
    if user is None:
        return _refused(SIGN_IN_REQUIRED, 401)
    if (hidden := await _hidden(engine, submission_id, user)) is not None:
        return hidden
    try:
        async with engine.begin() as connection:
            draft = await contribution.start_again(
                connection,
                storage,
                submission_id,
                user.id,
                clock(),
                expiry_days=_expiry_days(configuration),
            )
            return await _detail(connection, draft, user, configuration)
    except FAILURES as error:
        return _failure(error)


class ConvertBody(BaseModel):
    target_id: int
    """The existing Artwork that the new one duplicates."""


@router.post(
    "/{submission_id}/convert", status_code=201, response_model=SubmissionOut, responses=_ERRORS
)
async def convert(
    submission_id: int,
    body: ConvertBody,
    user: Annotated[Caller, Depends(current_user)],
    configuration: Annotated[Configuration, Depends(get_configuration)],
    engine: Annotated[AsyncEngine, Depends(get_engine)],
    storage: Annotated[Storage, Depends(get_storage)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> SubmissionOut | JSONResponse:
    """Convert a `changes requested` new Artwork into a draft that adds its Documentation
    items and History events to an existing Artwork. The original stays as it is until the
    draft is submitted, which retracts it ("Converted into …")."""
    if user is None:
        return _refused(SIGN_IN_REQUIRED, 401)
    if (hidden := await _hidden(engine, submission_id, user)) is not None:
        return hidden
    try:
        async with engine.begin() as connection:
            draft = await contribution.convert(
                connection,
                storage,
                submission_id,
                user.id,
                body.target_id,
                clock(),
                expiry_days=_expiry_days(configuration),
            )
            return await _detail(connection, draft, user, configuration)
    except FAILURES as error:
        return _failure(error)


class DecisionBody(BaseModel):
    verdict: Verdict
    version: int
    """The `version` the Moderator saw; if the Submission moved on, the decision is refused."""
    reason: str | None = None
    """A key of the Decision message reasons, for a rejection or changes requested."""
    text: str | None = None
    """The free text of the Decision message; approval takes none."""


@router.post("/{submission_id}/decision", response_model=SubmissionOut, responses=_ERRORS)
async def decide(
    submission_id: int,
    body: DecisionBody,
    user: Annotated[Caller, Depends(current_user)],
    configuration: Annotated[Configuration, Depends(get_configuration)],
    engine: Annotated[AsyncEngine, Depends(get_engine)],
    clock: Annotated[Clock, Depends(get_clock)],
    rules: Annotated[InstanceRules, Depends(get_archive_rules)],
) -> SubmissionOut | JSONResponse:
    """A Moderator approves, rejects, or requests changes on the last submitted round.

    Approval writes the archive in the same transaction. The first of two concurrent
    decisions wins (`moderation.already_decided`); `self_approval = false` refuses a
    decision on one's own Submission.
    """
    if user is None:
        return _refused(SIGN_IN_REQUIRED, 401)
    if not user.moderator:
        return _refused("moderation.forbidden", 403)
    if (hidden := await _hidden(engine, submission_id, user)) is not None:
        return hidden
    settings = configuration.instance.settings
    decision_rules = DecisionRules(
        self_approval=settings.community.self_approval,
        reasons=frozenset(
            entry.key for entry in configuration.instance.vocabularies["decision_reasons"]
        ),
    )
    decision = None
    if body.reason is not None or body.text is not None:
        decision = Decision(body.reason or "", body.text or "")
    now = clock()
    try:
        async with engine.begin() as connection:
            if body.verdict is Verdict.APPROVE:
                if decision is not None:
                    raise ModerationError("moderation.approval_has_message")
                approval = await service.approve(
                    connection, submission_id, user.id, body.version, decision_rules, rules, now
                )
                decided = approval.submission
            else:
                decided = await service.decide(
                    connection,
                    submission_id,
                    user.id,
                    body.verdict,
                    body.version,
                    decision_rules,
                    now,
                    decision=decision,
                )
            return await _detail(connection, decided, user, configuration)
    except FAILURES as error:
        return _failure(error)


class NoteBody(BaseModel):
    text: str


@router.post(
    "/{submission_id}/notes", status_code=201, response_model=SubmissionOut, responses=_ERRORS
)
async def add_note(
    submission_id: int,
    body: NoteBody,
    user: Annotated[Caller, Depends(current_user)],
    configuration: Annotated[Configuration, Depends(get_configuration)],
    engine: Annotated[AsyncEngine, Depends(get_engine)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> SubmissionOut | JSONResponse:
    """A Moderator adds a Moderation note: immutable, with author and date, read by
    Moderators only. It is not a decision, so a Moderator may add one to their own
    Submission whatever `self_approval` says."""
    if user is None:
        return _refused(SIGN_IN_REQUIRED, 401)
    if not user.moderator:
        return _refused("moderation.forbidden", 403)
    if (hidden := await _hidden(engine, submission_id, user)) is not None:
        return hidden
    try:
        async with engine.begin() as connection:
            noted = await service.add_note(connection, submission_id, user.id, body.text, clock())
            return await _detail(connection, noted, user, configuration)
    except FAILURES as error:
        return _failure(error)


class ImageSideOut(BaseModel):
    file: str
    """The upload id: the image is `/api/media/{file}/view`, at full size `/large`."""
    observed_date: Any
    creator_credit: str | None
    licence: str | None
    alt_text: str | None
    item_id: int | None
    """The Documentation item; null for the proposed file."""


class ImageComparisonOut(BaseModel):
    proposed: ImageSideOut
    current: ImageSideOut | None
    """The Artwork's most recent image Documentation item, null when it has none."""


class NearLocationOut(BaseModel):
    id: int
    distance_metres: float


class GeometrySummaryOut(BaseModel):
    vertices_before: int | None
    vertices_after: int
    largest_shift_metres: float | None
    shift_direction: str | None
    """A compass point: N, NE, E, SE, S, SW, W, or NW."""
    area_change_square_metres: float | None


class GeometryComparisonOut(BaseModel):
    record_kind: Kind
    target_id: int | None
    current: Any | None
    """GeoJSON; null for a new record."""
    proposed: Any
    summary: GeometrySummaryOut
    near_locations: list[NearLocationOut]
    """For a Location: the others within the proximity rule."""
    locations_entering: int | None
    locations_leaving: int | None
    """For an Area: the Locations its polygon takes in and lets go."""


class OperationCurrent(BaseModel):
    index: int
    """The position of the operation in the last round's `operations`."""
    current: Any | None
    """The field or item it changes, as it is now; null when it has none."""


class RoundOut(BaseModel):
    number: int
    submitted_at: datetime
    snapshot: Any | None
    """The changeset of the round; null in a stub."""


class ComparisonOut(BaseModel):
    current_revision: int | None
    """The target's latest Revision; compare with `base_revisions`."""
    operations: list[OperationCurrent]
    images: list[ImageComparisonOut]
    geometries: list[GeometryComparisonOut]
    rounds: list[RoundOut]
    """Every submitted round, so that the page can set one beside the previous."""


@router.get(
    "/{submission_id}/comparison",
    response_model=ComparisonOut,
    responses={401: {"model": Error}, 404: {"model": Error}},
)
async def comparison(
    submission_id: int,
    user: Annotated[Caller, Depends(current_user)],
    engine: Annotated[AsyncEngine, Depends(get_engine)],
) -> ComparisonOut | JSONResponse:
    """What the last submitted round changes, against the archive as it is now: the value
    each operation replaces, the proposed image beside the Artwork's latest one, and the
    proposed geometry against the current one with a summary in numbers. For the Submitter
    and Moderators only."""
    if user is None:
        return _refused(SIGN_IN_REQUIRED, 401)
    async with engine.connect() as connection:
        submission = await _visible(connection, submission_id, user)
        if submission is None:
            return _refused("moderation.unknown_submission", 404)
        compared = await compare.compare(connection, submission)
        revision = (
            (await archive_access.target_state(connection, submission.target_id)).revision_id  # type: ignore[union-attr]
            if submission.target_id is not None
            else None
        )
    return ComparisonOut(
        current_revision=revision,
        operations=[
            OperationCurrent(index=index, current=value)
            for index, value in sorted(compared.current_values.items())
        ],
        images=[
            ImageComparisonOut(
                proposed=ImageSideOut(**vars(each.proposed)),
                current=ImageSideOut(**vars(each.current)) if each.current else None,
            )
            for each in compared.images
        ],
        geometries=[
            GeometryComparisonOut(
                record_kind=each.record_kind,
                target_id=each.target_id,
                current=each.current,
                proposed=each.proposed,
                summary=GeometrySummaryOut(**vars(each.summary)),
                near_locations=[NearLocationOut(**vars(near)) for near in each.near_locations],
                locations_entering=each.locations_entering,
                locations_leaving=each.locations_leaving,
            )
            for each in compared.geometries
        ],
        rounds=[
            RoundOut(number=each.number, submitted_at=each.submitted_at, snapshot=each.snapshot)
            for each in submission.rounds
        ],
    )
