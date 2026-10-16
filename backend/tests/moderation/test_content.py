"""A Submission's content without a database: the JSON form of a changeset, the rules of
the model, the Condition record of a new Artwork, and derived kind and labels (contribution
and moderation spec, Submission model and Submission form). Every record is fictional."""

from dataclasses import replace
from datetime import UTC, date, datetime

import pytest
from archive_fixtures import artwork, event, image, location

from tart.archive import (
    AddItem,
    ArchiveRuleViolation,
    Artist,
    ArtistKind,
    Attribution,
    Certainty,
    ChangeItem,
    Condition,
    Create,
    CrewMembership,
    HistoryEventType,
    Kind,
    Medium,
    New,
    Period,
    Precision,
    Qualifier,
    RemoveItem,
    SetField,
    UncertainDate,
    decode_changeset,
    encode_changeset,
)
from tart.moderation import (
    Content,
    Intent,
    Label,
    ModerationError,
    Status,
    Submission,
    SubmissionKind,
    check_content,
    decode_content,
    derive_kind,
    derive_labels,
    encode_content,
    materialize,
)

LOCATION, ARTWORK, IMAGE, ARTIST = New("location"), New("artwork"), New("image"), New("artist")
NOW = datetime(2026, 9, 1, 10, 0, tzinfo=UTC)


def submission(
    kind: Kind = Kind.ARTWORK, target_id: int | None = None, base: int = 5
) -> Submission:
    return Submission(
        1, 2, kind, target_id, (base,) if target_id is not None else (), Status.DRAFT, NOW
    )


def new_artwork(**values: object) -> tuple[Create, ...]:
    return (
        Create(LOCATION, location()),
        Create(ARTWORK, artwork(LOCATION, **{"history_events": (), **values})),
        Create(IMAGE, image(ARTWORK)),
    )


def refused(subject: Submission, content: Content) -> str:
    with pytest.raises(ModerationError) as raised:
        check_content(subject, content)
    return raised.value.code


def test_a_changeset_survives_its_json_form() -> None:
    period = Period(UncertainDate(Precision.YEAR, Qualifier.EXACT, date(2019, 1, 1)), None)
    changeset = (
        *new_artwork(
            history_events=(event(HistoryEventType.CREATED, citations=(IMAGE,)),),
            attributions=(Attribution(ARTIST, Certainty.PROBABLE, alias="Nebbia"),),
        ),
        Create(
            ARTIST,
            Artist("Nebbia Finta", ArtistKind.INDIVIDUAL, period=period, aliases=("Nebbia",)),
        ),
        SetField(7, "title", "A fictional stencil"),
        AddItem(7, "history_events", event(HistoryEventType.DAMAGED)),
        ChangeItem(7, "attributions", Attribution(9, Certainty.DISPUTED)),
        RemoveItem(7, "attributions", 9),
    )
    of_an_artist = (
        AddItem(8, "crew_memberships", CrewMembership(10, period)),
        RemoveItem(8, "crew_memberships", (10, period)),
        AddItem(8, "aliases", "Nebbia"),
        RemoveItem(8, "aliases", "Nebbia"),
    )

    assert decode_changeset(encode_changeset(changeset), Kind.ARTWORK) == changeset
    assert decode_changeset(encode_changeset(of_an_artist), Kind.ARTIST) == of_an_artist


@pytest.mark.parametrize(
    "value",
    [
        "not a list",
        [{"op": "explode"}],
        [{"op": "set", "target": 7, "field": "unknown_field", "value": 1}],
        [{"op": "set", "target": 7, "field": "title", "value": 12}],
        [{"op": "add", "target": 7, "collection": "nothing", "item": 1}],
        [{"op": "set", "target": {"new": "missing"}, "field": "title", "value": "x"}],
    ],
)
def test_a_changeset_that_does_not_fit_is_refused_with_a_stable_code(value: object) -> None:
    with pytest.raises(ArchiveRuleViolation) as raised:
        decode_changeset(value, Kind.ARTWORK)  # type: ignore[arg-type]
    assert raised.value.code.startswith("changeset.")


def test_content_survives_its_json_form_and_a_snapshot_that_is_not_content_is_refused() -> None:
    content = Content(new_artwork(), Condition.MISSING)

    assert decode_content(encode_content(content), Kind.ARTWORK) == content
    for snapshot in ({"title": "First"}, "text", None, {"operations": [], "conflicts": 3}):
        with pytest.raises(ModerationError) as raised:
            decode_content(snapshot, Kind.ARTWORK)  # type: ignore[arg-type]
        assert raised.value.code == "moderation.malformed_content"


# Acceptance criterion 5.
def test_an_edit_of_a_second_existing_record_fails_validation() -> None:
    edit = submission(target_id=7)
    own = Content((SetField(7, "title", "Mine"),))
    other = Content((SetField(7, "title", "Mine"), SetField(8, "title", "Theirs")))
    linked = Content((AddItem(7, "series", 12),))
    related = Content(
        (
            Create(ARTIST, Artist("Nebbia Finta", ArtistKind.INDIVIDUAL)),
            AddItem(7, "attributions", Attribution(ARTIST, Certainty.PROBABLE)),
        )
    )

    check_content(edit, own)
    check_content(edit, linked)  # linking an existing record is allowed
    check_content(edit, related)  # so is creating a related one
    assert refused(edit, other) == "moderation.second_record_edited"


# Acceptance criterion 5.
def test_a_create_cannot_edit_an_existing_record() -> None:
    content = Content((*new_artwork(), SetField(8, "title", "Theirs")), Condition.INTACT)

    assert refused(submission(), content) == "moderation.second_record_edited"


# Acceptance criterion 14.
def test_a_new_artwork_needs_a_documentation_item_and_an_initial_condition() -> None:
    complete = Content(new_artwork(), Condition.INTACT)
    link = replace(
        image(ARTWORK),
        medium=Medium.LINK,
        url="https://example.org/fictional",
        file=None,
        licence=None,
        creator_credit=None,
        rights_basis=None,
        alt_text=None,
    )
    only_a_link = Content((*new_artwork()[:2], Create(IMAGE, link)), Condition.INTACT)
    elsewhere = Content(
        (*new_artwork()[:2], Create(IMAGE, image(New("another")))), Condition.INTACT
    )

    check_content(submission(), complete)
    check_content(submission(), only_a_link)  # a single link is enough
    assert refused(submission(), replace(complete, initial_condition=None)) == (
        "moderation.initial_condition_required"
    )
    assert refused(submission(), elsewhere) == "moderation.documentation_required"
    assert refused(submission(), Content(new_artwork()[:2], Condition.INTACT)) == (
        "moderation.documentation_required"
    )


def test_only_some_kinds_are_created_as_a_primary_target() -> None:
    for kind in (Kind.SITE, Kind.SERIES, Kind.SOURCE, Kind.DOCUMENTATION_ITEM):
        assert refused(submission(kind), Content(new_artwork())) == (
            "moderation.target_not_creatable"
        )


def test_an_edit_needs_one_base_revision_and_something_to_change() -> None:
    no_base = replace(submission(target_id=7), base_revisions=())

    assert refused(no_base, Content((SetField(7, "title", "x"),))) == (
        "moderation.base_revision_required"
    )
    assert refused(submission(target_id=7), Content(())) == "moderation.empty_changeset"


# Acceptance criterion 15.
def test_the_initial_condition_becomes_a_condition_record_dated_to_the_latest_document() -> None:
    earlier = UncertainDate(Precision.YEAR, Qualifier.EXACT, date(2019, 1, 1))
    later = UncertainDate(Precision.MONTH, Qualifier.EXACT, date(2024, 3, 1))
    older, newer, undated = New("older"), New("newer"), New("undated")
    content = Content(
        (
            *new_artwork()[:2],
            Create(older, image(ARTWORK, observed_date=earlier)),
            Create(newer, image(ARTWORK, observed_date=later)),
            Create(undated, image(ARTWORK, observed_date=UncertainDate.unknown())),
        ),
        Condition.MISSING,
    )

    artwork_record = next(
        op.record for op in materialize(content) if isinstance(op, Create) and op.ref == ARTWORK
    )

    (recorded,) = artwork_record.history_events  # type: ignore[union-attr]
    assert recorded.type is HistoryEventType.CONDITION_RECORDED
    assert recorded.condition is Condition.MISSING
    assert recorded.observed_date == later
    assert recorded.citations == (newer,)


# Acceptance criterion 9.
@pytest.mark.parametrize(
    ("target_kind", "target_id", "expected"),
    [
        (Kind.ARTWORK, None, SubmissionKind(Kind.ARTWORK, Intent.CREATE)),
        (Kind.ARTWORK, 7, SubmissionKind(Kind.ARTWORK, Intent.EDIT)),
        (Kind.ARTIST, None, SubmissionKind(Kind.ARTIST, Intent.CREATE)),
        (Kind.SOURCE, 7, SubmissionKind(Kind.SOURCE, Intent.EDIT)),
    ],
)
def test_the_kind_is_the_target_by_create_or_edit(
    target_kind: Kind, target_id: int | None, expected: SubmissionKind
) -> None:
    assert derive_kind(submission(target_kind, target_id)) == expected


# Acceptance criterion 9.
def test_the_labels_follow_the_changeset() -> None:
    attribution = Attribution(ARTIST, Certainty.PROBABLE)
    cases: list[tuple[Content, tuple[Label, ...]]] = [
        (
            Content(new_artwork(), Condition.INTACT),
            (Label.ADDS_DOCUMENTATION, Label.ADDS_HISTORY_EVENT, Label.CHANGES_CONDITION),
        ),
        (
            Content(new_artwork(attributions=(attribution,)), Condition.INTACT),
            (
                Label.ADDS_DOCUMENTATION,
                Label.ADDS_HISTORY_EVENT,
                Label.CHANGES_ATTRIBUTION,
                Label.CHANGES_CONDITION,
            ),
        ),
        (Content((SetField(7, "title", "x"),)), ()),
        (Content((Create(IMAGE, image(7)),)), (Label.ADDS_DOCUMENTATION,)),
        (
            Content((AddItem(7, "history_events", event(HistoryEventType.CREATED)),)),
            (Label.ADDS_HISTORY_EVENT,),
        ),
        (
            Content((AddItem(7, "history_events", event(HistoryEventType.COVERED)),)),
            (Label.ADDS_HISTORY_EVENT, Label.CHANGES_CONDITION),
        ),
        (
            Content((ChangeItem(7, "history_events", event(HistoryEventType.DAMAGED)),)),
            (Label.CHANGES_CONDITION,),
        ),
        (Content((RemoveItem(7, "attributions", 9),)), (Label.CHANGES_ATTRIBUTION,)),
        (Content((AddItem(7, "attributions", attribution),)), (Label.CHANGES_ATTRIBUTION,)),
    ]

    for content, labels in cases:
        assert derive_labels(content) == labels
