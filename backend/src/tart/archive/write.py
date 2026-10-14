"""The single write operation of the archive (archive-records spec, Modules).

    revisions = await apply_changeset(store, changeset, provenance, rules)

It applies a changeset to one or more records, checks every rule against the
result, and stores the records with one Revision for each record it creates or
changes, all through `store` inside its caller's transaction. Approval of a
Submission is its only caller (ADR 0002); until approval exists, tests and
development create records through it.
"""

from dataclasses import fields, is_dataclass, replace
from typing import Any

from tart.archive.changeset import AddItem, ChangeItem, Changeset, Create, Operation, SetField
from tart.archive.errors import ArchiveRuleViolation
from tart.archive.ports import ArchiveStore
from tart.archive.records import (
    Area,
    Artist,
    ArtistKind,
    Artwork,
    Attribution,
    Certainty,
    CrewMembership,
    DocumentationItem,
    HistoryEvent,
    Kind,
    Location,
    Medium,
    New,
    Record,
    RecordId,
    Series,
    Site,
    Source,
    item_key,
)
from tart.archive.revisions import Provenance, Revision, change_list
from tart.archive.rules import InstanceRules, check_record

_HOLDS_REFERENCES = (
    Record,
    Attribution,
    CrewMembership,
    HistoryEvent,
    SetField,
    AddItem,
    ChangeItem,
)


def _resolve(value: Any, ids: dict[str, RecordId]) -> Any:
    """The value with every `New` replaced by the id allocated to it."""
    if isinstance(value, New):
        if value.key not in ids:
            raise ArchiveRuleViolation("changeset.unknown_new_record")
        return ids[value.key]
    if isinstance(value, tuple):
        return tuple(_resolve(item, ids) for item in value)
    if isinstance(value, Create):
        return Create(value.ref, _resolve(value.record, ids))
    if isinstance(value, _HOLDS_REFERENCES) and is_dataclass(value):
        return replace(
            value,
            **{field.name: _resolve(getattr(value, field.name), ids) for field in fields(value)},
        )
    return value


class _Changes:
    """The records the changeset touches, before and after, over the stored archive."""

    def __init__(self, store: ArchiveStore) -> None:
        self.store = store
        self.before: dict[RecordId, Record | None] = {}
        self.after: dict[RecordId, Record] = {}

    async def current(self, record_id: RecordId) -> Record | None:
        """The record as the changeset leaves it."""
        if record_id in self.after:
            return self.after[record_id]
        return await self.store.get(record_id)

    async def touch(self, record_id: RecordId) -> Record:
        if record_id not in self.after:
            record = await self.store.get(record_id)
            if record is None:
                raise ArchiveRuleViolation("changeset.unknown_record")
            self.before[record_id] = record
            self.after[record_id] = record
        return self.after[record_id]

    def of_type[R: Record](self, record_type: type[R]) -> dict[RecordId, R]:
        return {
            record_id: record
            for record_id, record in self.after.items()
            if isinstance(record, record_type)
        }


def _apply(record: Record, operation: Operation) -> Record:
    match operation:
        case SetField(field=field, value=value):
            if field not in record.field_names() or field in record.COLLECTIONS:
                raise ArchiveRuleViolation("changeset.unknown_field")
            return replace(record, **{field: value})
        case AddItem(collection=collection) | ChangeItem(collection=collection):
            items = _collection(record, collection)
            key = item_key(operation.item)
            keys = [item_key(item) for item in items]
            if isinstance(operation, AddItem):
                if key in keys:
                    raise ArchiveRuleViolation("changeset.item_exists")
                return replace(record, **{collection: (*items, operation.item)})
            if key not in keys:
                raise ArchiveRuleViolation("changeset.unknown_item")
            changed = tuple(operation.item if item_key(item) == key else item for item in items)
            return replace(record, **{collection: changed})
        case _:
            items = _collection(record, operation.collection)
            if operation.key not in [item_key(item) for item in items]:
                raise ArchiveRuleViolation("changeset.unknown_item")
            kept = tuple(item for item in items if item_key(item) != operation.key)
            return replace(record, **{operation.collection: kept})


def _collection(record: Record, collection: str) -> tuple[Any, ...]:
    if collection not in record.COLLECTIONS:
        raise ArchiveRuleViolation("changeset.unknown_collection")
    return getattr(record, collection)


def _new_events(operation: Operation) -> tuple[HistoryEvent, ...]:
    """The History events the operation creates.

    A History event gets its id from the write operation, so a new one is named by
    `New`, in a namespace of its own: an event's key never names a record.
    """
    match operation:
        case Create(record=Artwork() as artwork):
            events = artwork.history_events
        case AddItem(item=HistoryEvent() as event):
            events = (event,)
        case ChangeItem(item=HistoryEvent(id=New())):
            raise ArchiveRuleViolation("changeset.unknown_item")
        case _:
            return ()
    if not all(isinstance(event.id, New) for event in events):
        raise ArchiveRuleViolation("changeset.history_event_not_new")
    return events


def _with_event_ids(operation: Operation, event_ids: dict[str, int]) -> Operation:
    """The operation with each new History event given its allocated id."""

    def named(event: HistoryEvent) -> HistoryEvent:
        assert isinstance(event.id, New)
        return replace(event, id=event_ids[event.id.key])

    match operation:
        case Create(record=Artwork() as artwork):
            events = tuple(named(event) for event in artwork.history_events)
            return Create(operation.ref, replace(artwork, history_events=events))
        case AddItem(item=HistoryEvent() as event):
            return replace(operation, item=named(event))
    return operation


def _references(record: Record) -> list[tuple[RecordId, tuple[Kind, ...]]]:
    """Every record this one links to, with the kinds the link accepts."""
    sources = [(source, (Kind.SOURCE,)) for source in getattr(record, "sources", ())]
    match record:
        case Artwork():
            citations = [
                (cited, (Kind.SOURCE, Kind.DOCUMENTATION_ITEM))
                for claim in (*record.attributions, *record.history_events)
                for cited in claim.citations
            ]
            covering = [
                (event.covering, (Kind.ARTWORK,))
                for event in record.history_events
                if event.covering is not None
            ]
            return [
                (record.location, (Kind.LOCATION,)),
                *[(series, (Kind.SERIES,)) for series in record.series],
                *[(attribution.artist, (Kind.ARTIST,)) for attribution in record.attributions],
                *citations,
                *covering,
                *sources,
            ]
        case Location():
            return [(record.site, (Kind.SITE,))] if record.site is not None else []
        case Artist():
            return [
                *[(area, (Kind.AREA,)) for area in record.areas],
                *[(crew.collective, (Kind.ARTIST,)) for crew in record.crew_memberships],
                *sources,
            ]
        case DocumentationItem():
            location = [(record.location, (Kind.LOCATION,))] if record.location is not None else []
            return [*[(artwork, (Kind.ARTWORK,)) for artwork in record.artworks], *location]
        case Site() | Area() | Series() | Source():
            return sources
    return []


async def _check_references(changes: _Changes) -> None:
    for record in changes.after.values():
        for record_id, kinds in _references(record):
            target = await changes.current(record_id)
            if target is None or target.KIND not in kinds:
                raise ArchiveRuleViolation("changeset.invalid_reference")


def _check_covering(changes: _Changes) -> None:
    for artwork_id, artwork in changes.of_type(Artwork).items():
        if any(event.covering == artwork_id for event in artwork.history_events):
            raise ArchiveRuleViolation("history_event.covering_itself")


async def _check_attributions(changes: _Changes) -> None:
    for artwork_id, artwork in changes.of_type(Artwork).items():
        before = changes.before[artwork_id]
        unchanged = set(before.attributions) if isinstance(before, Artwork) else set()
        for attribution in artwork.attributions:
            if attribution.alias is not None:
                artist = await changes.current(attribution.artist)
                assert isinstance(artist, Artist)
                if attribution.alias not in artist.aliases:
                    raise ArchiveRuleViolation("attribution.alias_not_of_artist")
            if attribution.certainty is Certainty.CONFIRMED and attribution not in unchanged:
                # A confirmed Attribution the change writes needs a public citation; a
                # record created by this changeset is public once it is approved.
                created = [
                    cited
                    for cited in attribution.citations
                    if cited in changes.before and changes.before[cited] is None
                ]
                if not created and not await changes.store.public_records(attribution.citations):
                    raise ArchiveRuleViolation("attribution.confirmed_requires_citation")


async def _check_aliases_in_use(changes: _Changes) -> None:
    for artist_id, artist in changes.of_type(Artist).items():
        before = changes.before[artist_id]
        if not isinstance(before, Artist):
            continue
        for alias in set(before.aliases) - set(artist.aliases):
            signed = await changes.store.artworks_signed_with(artist_id, alias)
            for artwork_id in signed | changes.of_type(Artwork).keys():
                artwork = await changes.current(artwork_id)
                assert isinstance(artwork, Artwork)
                if any(
                    attribution.artist == artist_id and attribution.alias == alias
                    for attribution in artwork.attributions
                ):
                    raise ArchiveRuleViolation("artist.alias_in_use")


async def _check_crews(changes: _Changes) -> None:
    for artist_id, artist in changes.of_type(Artist).items():
        # Every collective above this Artist, through any chain of memberships.
        seen: set[RecordId] = set()
        pending = [crew.collective for crew in artist.crew_memberships]
        while pending:
            collective_id = pending.pop()
            if collective_id == artist_id:
                raise ArchiveRuleViolation("crew_membership.cycle")
            if collective_id in seen:
                continue
            seen.add(collective_id)
            collective = await changes.current(collective_id)
            assert isinstance(collective, Artist)
            if collective.kind is not ArtistKind.COLLECTIVE:
                raise ArchiveRuleViolation("crew_membership.not_a_collective")
            pending += [crew.collective for crew in collective.crew_memberships]
        if artist.kind is ArtistKind.INDIVIDUAL:
            candidates = await changes.store.members_of(artist_id)
            for member_id in candidates | changes.of_type(Artist).keys():
                member = await changes.current(member_id)
                assert isinstance(member, Artist)
                if any(crew.collective == artist_id for crew in member.crew_memberships):
                    raise ArchiveRuleViolation("crew_membership.not_a_collective")


async def _check_images(changes: _Changes) -> None:
    """Every Artwork linked to one image Documentation item is on the same Location."""
    moved = [
        artwork_id
        for artwork_id, artwork in changes.of_type(Artwork).items()
        if isinstance(before := changes.before[artwork_id], Artwork)
        and before.location != artwork.location
    ]
    items = set(changes.of_type(DocumentationItem)) | await changes.store.documentation_items_of(
        moved
    )
    for item_id in items:
        item = await changes.current(item_id)
        assert isinstance(item, DocumentationItem)
        if item.medium is not Medium.IMAGE:
            continue
        locations = set()
        for artwork_id in item.artworks:
            artwork = await changes.current(artwork_id)
            assert isinstance(artwork, Artwork)
            locations.add(artwork.location)
        if len(locations) > 1:
            raise ArchiveRuleViolation("documentation_item.image_on_several_locations")


async def apply_changeset(
    store: ArchiveStore,
    changeset: Changeset,
    provenance: Provenance,
    rules: InstanceRules,
) -> tuple[Revision, ...]:
    """Apply the changeset and return one Revision per record it creates or changes.

    Raises `ArchiveRuleViolation` with a stable code, before anything is stored, when
    the result would break a rule. The caller's transaction makes the whole write
    atomic.
    """
    submitted_on = provenance.submitted_at.astimezone(rules.time_zone).date()
    ids: dict[str, RecordId] = {}
    event_ids: dict[str, int] = {}
    for operation in changeset:
        if isinstance(operation, Create):
            if operation.ref.key in ids:
                raise ArchiveRuleViolation("changeset.duplicate_new_record")
            ids[operation.ref.key] = await store.allocate_id(operation.record.KIND)
        for event in _new_events(operation):
            assert isinstance(event.id, New)
            if event.id.key in event_ids:
                raise ArchiveRuleViolation("changeset.duplicate_new_event")
            event_ids[event.id.key] = await store.allocate_history_event_id()

    changes = _Changes(store)
    for operation in changeset:
        resolved = _resolve(_with_event_ids(operation, event_ids), ids)
        if isinstance(resolved, Create):
            record_id = ids[resolved.ref.key]
            changes.before[record_id] = None
            changes.after[record_id] = resolved.record
        else:
            record = await changes.touch(resolved.target)
            changes.after[resolved.target] = _apply(record, resolved)

    for record_id, record in changes.after.items():
        check_record(record, changes.before[record_id], rules, submitted_on)
    await _check_references(changes)
    _check_covering(changes)
    await _check_attributions(changes)
    await _check_aliases_in_use(changes)
    await _check_crews(changes)
    await _check_images(changes)

    revisions: list[Revision] = []
    await store.watch(changes.after)
    for record_id, record in changes.after.items():
        before = changes.before[record_id]
        diff = change_list(before, record)
        if not diff:
            continue
        await store.save(record_id, record, new=before is None)
        revisions.append(await store.add_revision(record_id, record.KIND, provenance, diff))
    await store.settle([revision.record_id for revision in revisions], rules)
    return tuple(revisions)
