"""`/api/contributions`: Merge, Duplicate retirement, and Unmerge (ADR 0018; contribution and
moderation spec, Merge, Duplicate retirement, Unmerge).

    POST /api/contributions/merge              start a Merge, or a Duplicate retirement, as a draft
    POST /api/contributions/unmerge            start an Unmerge as a draft
    GET  /api/contributions/merge-candidates   the likeliest survivors of a Merge of a record
    GET  /api/contributions/{id}/merge         the two records, the records to rewrite, the choices

They are Submissions like any other: they go through the routes of `contributions` to be
autosaved, submitted, and decided. Any signed-in User may propose them; approving is an
ordinary Moderator duty. Refusals carry a stable code (ADR 0008).
"""

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
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
)
from tart.api.contributions import (
    _ERRORS,
    FAILURES,
    Caller,
    SubmissionOut,
    _content_of,
    _detail,
    _expiry_days,
    _failure,
    _refused,
    _visible,
    get_archive_rules,
)
from tart.archive import Unmerge
from tart.archive.records import Kind
from tart.archive.rules import InstanceRules
from tart.archive_read import Reader, Viewer
from tart.archive_read import views as v
from tart.archive_read.reader import referenced_ids
from tart.config import Configuration
from tart.moderation.merge import ItemEntry
from tart.moderation_persistence import contribution
from tart.moderation_persistence import merging as merging_

router = APIRouter(prefix="/api/contributions")


class MergeBody(BaseModel):
    source_id: int
    """The record to fold: a duplicate, or for a Duplicate retirement the item to set aside."""
    into_id: int
    """The surviving record, of the same kind."""


@router.post("/merge", status_code=201, response_model=SubmissionOut, responses=_ERRORS)
async def start_merge(
    body: MergeBody,
    user: Annotated[Caller, Depends(current_user)],
    configuration: Annotated[Configuration, Depends(get_configuration)],
    engine: Annotated[AsyncEngine, Depends(get_engine)],
    clock: Annotated[Clock, Depends(get_clock)],
    rules: Annotated[InstanceRules, Depends(get_archive_rules)],
) -> SubmissionOut | JSONResponse:
    """Start a Merge of a record into another of the same kind (a Duplicate retirement for
    Documentation items) as a draft pre-filled with the default Merge. Both records must be
    public; the draft stores both current Revisions as its Base revisions. A retirement of
    items whose Artworks sit on different Locations is refused at once."""
    if user is None:
        return _refused(SIGN_IN_REQUIRED, 401)
    try:
        async with engine.begin() as connection:
            draft = await contribution.start_merge(
                connection,
                user.id,
                body.source_id,
                body.into_id,
                clock(),
                rules,
                expiry_days=_expiry_days(configuration),
            )
            return await _detail(connection, draft, user, configuration)
    except FAILURES as error:
        return _failure(error)


class UnmergeBody(BaseModel):
    source_id: int
    """The merged record, or the retired Documentation item, to bring back."""


@router.post("/unmerge", status_code=201, response_model=SubmissionOut, responses=_ERRORS)
async def start_unmerge(
    body: UnmergeBody,
    user: Annotated[Caller, Depends(current_user)],
    configuration: Annotated[Configuration, Depends(get_configuration)],
    engine: Annotated[AsyncEngine, Depends(get_engine)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> SubmissionOut | JSONResponse:
    """Start an Unmerge as a draft pre-filled from the Revisions of the Merge it undoes: the
    items it added to the survivor are removed, and the records that referenced the folded one
    are pointed back to it. The same call undoes a Duplicate retirement."""
    if user is None:
        return _refused(SIGN_IN_REQUIRED, 401)
    try:
        async with engine.begin() as connection:
            draft = await contribution.start_unmerge(
                connection,
                user.id,
                body.source_id,
                clock(),
                expiry_days=_expiry_days(configuration),
            )
            return await _detail(connection, draft, user, configuration)
    except FAILURES as error:
        return _failure(error)


async def _links(
    connection: AsyncConnection, ids: set[int], *, public: bool
) -> dict[int, v.RecordLink]:
    """Links to records. `public` keeps those the public lists; else merged ones too."""
    reader = Reader(connection, Viewer(moderator=True))
    if public:
        return {link.id: link for link in await reader.links(sorted(ids))}
    return await reader.known_links(sorted(ids))


class Candidates(BaseModel):
    source: v.RecordLink
    """The record to fold."""
    items: list[v.RecordLink]


@router.get("/merge-candidates", response_model=Candidates, responses=_ERRORS)
async def merge_candidates(
    source_id: int,
    user: Annotated[Caller, Depends(current_user)],
    engine: Annotated[AsyncEngine, Depends(get_engine)],
) -> Candidates | JSONResponse:
    """The public records that may be the survivor of a Merge of this one, likeliest first:
    nearby Locations (and the Artworks on them), records with an alike name, or the other
    items of the same Artworks. Any signed-in User may ask."""
    if user is None:
        return _refused(SIGN_IN_REQUIRED, 401)
    try:
        async with engine.connect() as connection:
            found = await merging_.candidates(connection, source_id)
            links = await _links(connection, {source_id, *found}, public=True)
    except FAILURES as error:
        return _failure(error)
    if source_id not in links:
        return _refused("moderation.unknown_target", 404)
    return Candidates(
        source=links[source_id], items=[links[each] for each in found if each in links]
    )


class ItemEntryOut(BaseModel):
    collection: str
    key: Any
    """What the operation that adds or removes the item names it by."""
    item: Any
    origin: Literal["source", "into"]


class FieldDifferenceOut(BaseModel):
    name: str
    source: Any
    into: Any


class ContradictionOut(BaseModel):
    kind: Literal[
        "two_creation_events", "competing_attributions", "different_disappearance_locations"
    ]
    key: Any = None
    """The Artist of competing Attributions."""
    item: Any = None
    """The folded record's Attribution, which the proposer may choose over the survivor's."""


class MergeReview(BaseModel):
    """What a Merge, Duplicate retirement, or Unmerge Submission shows beside its changeset:
    the two records, the records the approval rewrites, and what the proposer decides."""

    intent: Literal["merge", "retirement", "unmerge"]
    source: v.RecordLink
    into: v.RecordLink
    references: list[v.RecordLink]
    """The records that reference the folded one now: rewritten on approval, each with a
    Revision of its own. For an Unmerge, the records pointed back to it."""
    references_hidden: int
    """How many more there are that the page cannot name: withdrawn records."""
    items: list[ItemEntryOut]
    """Merge: the items of both records, to keep or drop."""
    fields: list[FieldDifferenceOut]
    """Merge: the fields whose values differ; the survivor's stay unless the changeset sets them."""
    contradictions: list[ContradictionOut]
    """Merge: what the result would say twice; they block only at submit."""
    from_source: list[ItemEntryOut]
    """Unmerge: the survivor's items that the Merge added, preselected for removal."""
    added_since: list[ItemEntryOut]
    """Unmerge: the items added to the survivor after the Merge, for the proposer to decide."""
    skipped: list[v.RecordLink]
    """Unmerge: referencing records that changed since the Merge in the same place."""
    records: dict[str, v.RecordLink]
    """The records that items and field values refer to, by id."""


def _entries(found: list[ItemEntry]) -> list[ItemEntryOut]:
    return [
        ItemEntryOut(collection=e.collection, key=e.key, item=e.item, origin=e.origin.value)
        for e in found
    ]


@router.get(
    "/{submission_id}/merge",
    response_model=MergeReview,
    responses={401: {"model": Error}, 404: {"model": Error}, 409: {"model": Error}},
)
async def read_merge(
    submission_id: int,
    user: Annotated[Caller, Depends(current_user)],
    engine: Annotated[AsyncEngine, Depends(get_engine)],
) -> MergeReview | JSONResponse:
    """The two records of a Merge, Duplicate retirement, or Unmerge Submission, the records
    its approval rewrites (listed afresh whenever you ask, so a Moderator always sees the
    current list), and the choices the proposer has: for the Submitter and Moderators only."""
    if user is None:
        return _refused(SIGN_IN_REQUIRED, 401)
    async with engine.connect() as connection:
        submission = await _visible(connection, submission_id, user)
        if submission is None:
            return _refused("moderation.unknown_submission", 404)
        content = _content_of(submission)
        merging = moderation.merge_of(content) if content is not None else None
        if merging is None:
            return _refused("moderation.not_a_merge", 409)
        retirement = submission.target_kind is Kind.DOCUMENTATION_ITEM
        intent = (
            "unmerge" if isinstance(merging, Unmerge) else "retirement" if retirement else "merge"
        )
        try:
            if isinstance(merging, Unmerge):
                _, restore = await merging_.unmerge_plan(connection, merging.source)
                references = [r.record_id for r in restore.restored]
                skipped = list(restore.skipped)
                items: list[ItemEntryOut] = []
                fields: list[FieldDifferenceOut] = []
                contradictions: list[ContradictionOut] = []
                from_source = _entries(list(restore.from_source))
                added_since = _entries(list(restore.added_since))
            else:
                plan = await merging_.merge_plan(connection, merging.source, merging.into)
                references = [
                    r.id for r in await merging_.references_of(connection, merging.source)
                ]
                skipped = []
                items = _entries(list(plan.items))
                fields = [
                    FieldDifferenceOut(name=d.name, source=d.source, into=d.into)
                    for d in plan.fields
                ]
                contradictions = [
                    ContradictionOut(kind=c.kind.value, key=c.key, item=c.item)  # type: ignore[arg-type]
                    for c in plan.contradictions
                ]
                from_source, added_since = [], []
        except FAILURES as error:
            return _failure(error)
        mentioned: set[int] = set()
        for entry in [*items, *from_source, *added_since]:
            mentioned |= referenced_ids(entry.collection, {"item": entry.item})
        for difference in fields:
            mentioned |= referenced_ids(
                difference.name, {"source": difference.source, "into": difference.into}
            )
        for contradiction in contradictions:
            mentioned |= referenced_ids("attributions", {"item": contradiction.item})
        links = await _links(
            connection, {merging.source, merging.into, *references, *skipped}, public=False
        )
        named = await _links(connection, mentioned, public=True)
    return MergeReview(
        intent=intent,
        source=links[merging.source],
        into=links[merging.into],
        references=[links[each] for each in references if each in links],
        references_hidden=sum(1 for each in references if each not in links),
        items=items,
        fields=fields,
        contradictions=contradictions,
        from_source=from_source,
        added_since=added_since,
        skipped=[links[each] for each in skipped if each in links],
        records={str(each): link for each, link in named.items()},
    )
