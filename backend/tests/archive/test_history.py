"""The physical history: History event types, Condition, Condition group, Timeline, and
stratigraphy (archive-records spec, Physical history and Location). Every record here is
fictional.
"""

from dataclasses import replace
from datetime import UTC, date, datetime

import pytest
from archive_fixtures import OBSERVED, RULES, artwork

from tart.archive import (
    ApprovedEvent,
    ApprovedItem,
    ArchiveRuleViolation,
    Artwork,
    Condition,
    ConditionGroup,
    HistoryEvent,
    HistoryEventType,
    Medium,
    Precision,
    Qualifier,
    Stratum,
    UncertainDate,
    condition_group,
    creation_event,
    derive_condition,
    first_documentation,
    last_documented,
    stratigraphy,
    timeline,
)
from tart.archive.records import RECORD_TYPES, DocumentationItem
from tart.archive.rules import check_record

T = HistoryEventType
DAY_ONE = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
DAY_TWO = datetime(2026, 9, 2, 12, 0, tzinfo=UTC)
DAY_THREE = datetime(2026, 9, 3, 12, 0, tzinfo=UTC)
UNKNOWN = UncertainDate.unknown()


def year(value: int, qualifier: Qualifier = Qualifier.EXACT) -> UncertainDate:
    return UncertainDate(Precision.YEAR, qualifier, date(value, 1, 1))


def month(value: int, month_number: int) -> UncertainDate:
    return UncertainDate(Precision.MONTH, Qualifier.EXACT, date(value, month_number, 1))


_ids = iter(range(1, 10_000))


def approved(
    event_type: HistoryEventType,
    observed: UncertainDate = OBSERVED,
    at: datetime = DAY_ONE,
    **values: object,
) -> ApprovedEvent:
    if event_type is T.CONDITION_RECORDED:
        values.setdefault("condition", Condition.INTACT)
    event = HistoryEvent(next(_ids), event_type, observed, **values)  # type: ignore[arg-type]
    return ApprovedEvent(event, at)


def documented(observed: UncertainDate, at: datetime = DAY_ONE) -> ApprovedItem:
    item = DocumentationItem(Medium.TEXT, observed, (1,), text="A fictional account.")
    return ApprovedItem(next(_ids), item, at)


def _check(record: Artwork, before: Artwork | None = None) -> None:
    check_record(record, before, RULES, date(2026, 9, 1))


def _violation(record: Artwork) -> str:
    with pytest.raises(ArchiveRuleViolation) as raised:
        _check(record)
    return raised.value.code


def _with_events(*events: HistoryEvent) -> Artwork:
    return artwork(1, history_events=events)


def _event(event_type: HistoryEventType, **values: object) -> HistoryEvent:
    return HistoryEvent(next(_ids), event_type, OBSERVED, **values)  # type: ignore[arg-type]


# Criterion 38: the nine types, and the Condition each condition-changing type sets.


def test_criterion_38_the_history_event_types_are_exactly_the_nine() -> None:
    assert {member.value for member in HistoryEventType} == {
        "created",
        "condition_recorded",
        "deteriorated",
        "damaged",
        "modified",
        "covered",
        "removed",
        "destroyed",
        "attribution_changed",
    }


@pytest.mark.parametrize(
    ("event_type", "condition"),
    [
        (T.DETERIORATED, Condition.DETERIORATED),
        (T.DAMAGED, Condition.DAMAGED),
        (T.MODIFIED, Condition.MODIFIED),
        (T.COVERED, Condition.COVERED),
        (T.REMOVED, Condition.REMOVED),
        (T.DESTROYED, Condition.DESTROYED),
    ],
)
def test_criterion_38_each_condition_changing_type_sets_its_condition(
    event_type: HistoryEventType, condition: Condition
) -> None:
    reading = derive_condition([approved(T.CONDITION_RECORDED, year(2020)), approved(event_type)])

    assert reading.condition is condition


@pytest.mark.parametrize("condition", list(Condition))
def test_criterion_38_a_condition_record_sets_the_condition_it_states(
    condition: Condition,
) -> None:
    reading = derive_condition([approved(T.CONDITION_RECORDED, condition=condition)])

    assert reading.condition is condition


@pytest.mark.parametrize("event_type", [T.CREATED, T.ATTRIBUTION_CHANGED])
def test_criterion_38_creation_and_attribution_changes_set_no_condition(
    event_type: HistoryEventType,
) -> None:
    earlier = approved(T.DAMAGED, year(2020))

    reading = derive_condition([earlier, approved(event_type, year(2024))])

    assert reading.condition is Condition.DAMAGED
    assert reading.event == earlier


def test_criterion_38_only_a_condition_record_states_a_condition() -> None:
    assert _violation(_with_events(_event(T.CONDITION_RECORDED))) == (
        "history_event.condition_required"
    )
    assert _violation(
        _with_events(
            _event(T.CONDITION_RECORDED, condition=Condition.INTACT),
            _event(T.DAMAGED, condition=Condition.DAMAGED),
        )
    ) == ("history_event.condition_not_applicable")


def test_only_a_covered_event_links_the_covering_artwork() -> None:
    _check(_with_events(_event(T.COVERED, covering=2)))

    assert _violation(_with_events(_event(T.DESTROYED, covering=2))) == (
        "history_event.covering_not_applicable"
    )


def test_an_artwork_has_at_most_one_creation_event() -> None:
    record = _with_events(_event(T.DAMAGED), _event(T.CREATED), _event(T.CREATED))

    assert _violation(record) == "artwork.creation_event_duplicated"


def test_a_history_event_dated_after_the_submission_is_rejected() -> None:
    record = _with_events(replace(_event(T.DAMAGED), observed_date=year(2030)))

    assert _violation(record) == "uncertain_date.after_submission"


# Criterion 2: Condition is derived from the most recent public condition-changing event.


def test_criterion_2_the_condition_follows_the_most_recent_event_by_key() -> None:
    events = [
        approved(T.DAMAGED, year(2018)),
        approved(T.CONDITION_RECORDED, year(2016)),
        approved(T.COVERED, month(2019, 5)),
        approved(T.CONDITION_RECORDED, year(2017), condition=Condition.MISSING),
    ]

    reading = derive_condition(events)

    assert reading.condition is Condition.COVERED
    assert reading.event == events[2]
    assert reading.documented


def test_criterion_2_order_of_input_does_not_matter() -> None:
    events = [approved(T.DAMAGED, year(2018)), approved(T.DESTROYED, year(2021))]

    assert derive_condition(events) == derive_condition(reversed(events))


def test_criterion_2_a_restoration_is_a_condition_record_after_the_damage() -> None:
    reading = derive_condition(
        [
            approved(T.DAMAGED, year(2018)),
            approved(T.CONDITION_RECORDED, year(2020), condition=Condition.INTACT),
        ]
    )

    assert (reading.condition, reading.group) == (Condition.INTACT, ConditionGroup.PRESENT)


def test_criterion_2_no_record_kind_has_a_condition_field() -> None:
    for record_type in RECORD_TYPES.values():
        assert "condition" not in record_type.field_names()


# Criterion 40: ties go to the later approval; `unknown` never overrides a dated event.


def test_criterion_40_of_equal_keys_the_later_approved_event_wins() -> None:
    first = approved(T.DAMAGED, year(2016), at=DAY_TWO)
    second = approved(T.COVERED, year(2016, Qualifier.CIRCA), at=DAY_THREE)

    assert derive_condition([second, first]).condition is Condition.COVERED
    assert derive_condition([replace(second, approved_at=DAY_ONE), first]).condition is (
        Condition.DAMAGED
    )


def test_criterion_40_equal_keys_and_approvals_fall_back_to_the_id() -> None:
    lower, higher = approved(T.DAMAGED, at=DAY_ONE), approved(T.REMOVED, at=DAY_ONE)

    assert lower.id < higher.id
    assert derive_condition([higher, lower]).condition is Condition.REMOVED


def test_criterion_40_an_unknown_dated_event_never_overrides_a_dated_one() -> None:
    reading = derive_condition(
        [approved(T.DAMAGED, year(2010), at=DAY_ONE), approved(T.DESTROYED, UNKNOWN, at=DAY_THREE)]
    )

    assert reading.condition is Condition.DAMAGED


def test_criterion_40_among_unknown_dated_events_the_latest_approved_wins() -> None:
    reading = derive_condition(
        [
            approved(T.DESTROYED, UNKNOWN, at=DAY_THREE),
            approved(T.DAMAGED, UNKNOWN, at=DAY_TWO),
            approved(T.CREATED, year(2010), at=DAY_ONE),
        ]
    )

    assert reading.condition is Condition.DESTROYED
    assert reading.documented


# Criterion 41, the reading side: no public condition-changing event reads `unknown`.


def test_criterion_41_no_public_condition_changing_event_reads_state_not_documented() -> None:
    reading = derive_condition([approved(T.CREATED, year(2010))])

    assert (reading.condition, reading.group) == (Condition.UNKNOWN, ConditionGroup.UNKNOWN)
    assert reading.event is None
    assert not reading.documented


def test_criterion_41_a_recorded_unknown_condition_is_documented_and_dated() -> None:
    event = approved(T.CONDITION_RECORDED, year(2024), condition=Condition.UNKNOWN)

    reading = derive_condition([event])

    assert (reading.condition, reading.event, reading.documented) == (
        Condition.UNKNOWN,
        event,
        True,
    )


def test_criterion_41_an_artwork_needs_a_condition_changing_event() -> None:
    assert _violation(_with_events()) == "artwork.condition_changing_event_required"
    assert _violation(_with_events(_event(T.CREATED), _event(T.ATTRIBUTION_CHANGED))) == (
        "artwork.condition_changing_event_required"
    )
    _check(_with_events(_event(T.CREATED), _event(T.REMOVED)))


# Criterion 3, the reading side: a disappearance moves the group to *disappeared*.


@pytest.mark.parametrize(
    ("condition", "group"),
    [
        (Condition.INTACT, ConditionGroup.PRESENT),
        (Condition.DETERIORATED, ConditionGroup.PRESENT),
        (Condition.DAMAGED, ConditionGroup.PRESENT),
        (Condition.MODIFIED, ConditionGroup.PRESENT),
        (Condition.COVERED, ConditionGroup.DISAPPEARED),
        (Condition.REMOVED, ConditionGroup.DISAPPEARED),
        (Condition.DESTROYED, ConditionGroup.DISAPPEARED),
        (Condition.MISSING, ConditionGroup.DISAPPEARED),
        (Condition.UNKNOWN, ConditionGroup.UNKNOWN),
    ],
)
def test_criterion_3_every_condition_belongs_to_its_group(
    condition: Condition, group: ConditionGroup
) -> None:
    assert condition_group(condition) is group


@pytest.mark.parametrize("event_type", [T.COVERED, T.REMOVED, T.DESTROYED])
def test_criterion_3_a_disappearance_event_makes_the_group_disappeared(
    event_type: HistoryEventType,
) -> None:
    events = [approved(T.CONDITION_RECORDED, year(2016))]
    assert derive_condition(events).group is ConditionGroup.PRESENT

    reading = derive_condition([*events, approved(event_type, year(2024))])

    assert reading.group is ConditionGroup.DISAPPEARED


# Criterion 9: the creation date is unknown without a Creation event.


def test_criterion_9_without_a_creation_event_the_creation_date_is_unknown() -> None:
    events = [approved(T.CONDITION_RECORDED, year(2016))]
    items = [documented(year(2018)), documented(month(2015, 6))]

    assert creation_event(events) is None
    assert first_documentation(items) == items[1]


def test_criterion_9_the_creation_event_gives_the_creation_date() -> None:
    created = approved(T.CREATED, year(2012, Qualifier.BEFORE))

    assert creation_event([approved(T.DAMAGED), created]) == created


def test_first_and_last_documentation_order_by_key_with_the_later_approval_winning() -> None:
    early, tied, late = (
        documented(year(2016), at=DAY_ONE),
        documented(year(2016, Qualifier.CIRCA), at=DAY_TWO),
        documented(year(2020)),
    )
    undated = documented(UNKNOWN, at=DAY_THREE)

    assert first_documentation([late, early, tied, undated]) == tied
    assert last_documented([early, late, undated]) == late
    assert first_documentation([undated]) == undated
    assert first_documentation([]) is None


# Timeline.


def test_the_timeline_is_ascending_with_events_before_items_and_undated_last() -> None:
    created = approved(T.CREATED, year(2014))
    photo_2016 = documented(year(2016))
    damage_2016 = approved(T.DAMAGED, year(2016), at=DAY_TWO)
    covered = approved(T.COVERED, year(2019))
    undated_item = documented(UNKNOWN, at=DAY_ONE)
    undated_event = approved(T.CONDITION_RECORDED, UNKNOWN, at=DAY_TWO)

    result = timeline([covered, undated_event, damage_2016, created], [undated_item, photo_2016])

    assert result.dated == (created, damage_2016, photo_2016, covered)
    assert result.undated == (undated_event, undated_item)


def test_the_timeline_orders_equal_keys_of_one_kind_by_approval() -> None:
    later, earlier = approved(T.DAMAGED, at=DAY_TWO), approved(T.DETERIORATED, at=DAY_ONE)

    assert timeline([later, earlier], []).dated == (earlier, later)


# Criterion 43: the stratigraphy.


def test_criterion_43_stratigraphy_by_creation_or_first_documentation_most_recent_first() -> None:
    created_2010 = Stratum(1, approved(T.CREATED, year(2010)), documented(year(2021)))
    documented_2015 = Stratum(2, None, documented(year(2015)))
    created_2019 = Stratum(3, approved(T.CREATED, year(2019)), documented(year(2019)))

    assert stratigraphy([created_2010, documented_2015, created_2019]) == (3, 2, 1)


def test_criterion_43_covered_links_never_reorder_the_stratigraphy() -> None:
    # The older Artwork records that the newer one covers it; order still goes by date.
    covered = Stratum(1, approved(T.CREATED, year(2012)), None)
    covering = Stratum(2, approved(T.CREATED, year(2018)), None)
    inconsistent = Stratum(3, approved(T.CREATED, year(2020)), None)

    assert stratigraphy([covered, covering, inconsistent]) == (3, 2, 1)


def test_criterion_43_ties_go_to_the_later_approval() -> None:
    first = Stratum(1, approved(T.CREATED, year(2016), at=DAY_THREE), None)
    second = Stratum(2, approved(T.CREATED, year(2016, Qualifier.CIRCA), at=DAY_ONE), None)

    assert stratigraphy([second, first]) == (1, 2)


def test_criterion_43_an_undated_creation_falls_back_to_the_first_documentation() -> None:
    undated_creation = Stratum(1, approved(T.CREATED, UNKNOWN), documented(year(2022)))
    dated = Stratum(2, approved(T.CREATED, year(2018)), None)
    no_date = Stratum(3, None, documented(UNKNOWN))

    assert stratigraphy([no_date, dated, undated_creation]) == (1, 2, 3)
