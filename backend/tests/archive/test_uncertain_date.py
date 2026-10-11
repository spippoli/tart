"""Uncertain date: construction, derived range, and chronological key (archive-records spec)."""

from datetime import date, datetime

import pytest

from tart.archive import ArchiveRuleViolation, DateRange, Precision, Qualifier, UncertainDate

SUBMITTED_ON = date(2026, 10, 11)

DAY = date(2016, 3, 12)
MONTH = date(2016, 3, 1)
YEAR = date(2016, 1, 1)
DECADE = date(1990, 1, 1)


def _range(
    precision: Precision, qualifier: Qualifier, first: date, second: date | None = None
) -> DateRange:
    return UncertainDate(precision, qualifier, first, second).range(SUBMITTED_ON)


# Criterion 39: the derived range for every precision x qualifier.
@pytest.mark.parametrize(
    ("precision", "qualifier", "value", "earliest", "latest"),
    [
        (Precision.DAY, Qualifier.EXACT, DAY, date(2016, 3, 12), date(2016, 3, 12)),
        (Precision.DAY, Qualifier.CIRCA, DAY, date(2016, 3, 11), date(2016, 3, 13)),
        (Precision.DAY, Qualifier.BEFORE, DAY, None, date(2016, 3, 11)),
        (Precision.DAY, Qualifier.AFTER, DAY, date(2016, 3, 13), SUBMITTED_ON),
        (Precision.MONTH, Qualifier.EXACT, MONTH, date(2016, 3, 1), date(2016, 3, 31)),
        (Precision.MONTH, Qualifier.CIRCA, MONTH, date(2016, 2, 1), date(2016, 4, 30)),
        (Precision.MONTH, Qualifier.BEFORE, MONTH, None, date(2016, 2, 29)),
        (Precision.MONTH, Qualifier.AFTER, MONTH, date(2016, 4, 1), SUBMITTED_ON),
        (Precision.YEAR, Qualifier.EXACT, YEAR, date(2016, 1, 1), date(2016, 12, 31)),
        (Precision.YEAR, Qualifier.CIRCA, YEAR, date(2015, 1, 1), date(2017, 12, 31)),
        (Precision.YEAR, Qualifier.BEFORE, YEAR, None, date(2015, 12, 31)),
        (Precision.YEAR, Qualifier.AFTER, YEAR, date(2017, 1, 1), SUBMITTED_ON),
        (Precision.DECADE, Qualifier.EXACT, DECADE, date(1990, 1, 1), date(1999, 12, 31)),
        (Precision.DECADE, Qualifier.CIRCA, DECADE, date(1980, 1, 1), date(2009, 12, 31)),
        (Precision.DECADE, Qualifier.BEFORE, DECADE, None, date(1989, 12, 31)),
        (Precision.DECADE, Qualifier.AFTER, DECADE, date(2000, 1, 1), SUBMITTED_ON),
    ],
)
def test_criterion_39_range_for_every_precision_and_qualifier(
    precision: Precision, qualifier: Qualifier, value: date, earliest: date | None, latest: date
) -> None:
    assert _range(precision, qualifier, value) == DateRange(earliest, latest)


@pytest.mark.parametrize(
    ("precision", "first", "second", "earliest", "latest"),
    [
        (Precision.DAY, date(2016, 3, 12), date(2016, 3, 20), date(2016, 3, 12), date(2016, 3, 20)),
        (Precision.MONTH, date(2016, 3, 1), date(2016, 5, 1), date(2016, 3, 1), date(2016, 5, 31)),
        (Precision.YEAR, date(2014, 1, 1), date(2015, 1, 1), date(2014, 1, 1), date(2015, 12, 31)),
        (Precision.DECADE, DECADE, date(2000, 1, 1), date(1990, 1, 1), date(2009, 12, 31)),
    ],
)
def test_criterion_39_exact_from_to_spans_the_first_start_to_the_second_end(
    precision: Precision, first: date, second: date, earliest: date, latest: date
) -> None:
    assert _range(precision, Qualifier.EXACT, first, second) == DateRange(earliest, latest)


def test_criterion_39_unknown_has_both_bounds_open() -> None:
    assert UncertainDate.unknown().range(SUBMITTED_ON) == DateRange(None, None)


@pytest.mark.parametrize(
    ("precision", "qualifier", "value"),
    [
        (Precision.DAY, Qualifier.EXACT, SUBMITTED_ON),
        (Precision.DAY, Qualifier.CIRCA, SUBMITTED_ON),
        (Precision.MONTH, Qualifier.EXACT, date(2026, 10, 1)),
        (Precision.MONTH, Qualifier.CIRCA, date(2026, 9, 1)),
        (Precision.YEAR, Qualifier.EXACT, date(2026, 1, 1)),
        (Precision.YEAR, Qualifier.CIRCA, date(2025, 1, 1)),
        (Precision.DECADE, Qualifier.EXACT, date(2020, 1, 1)),
        (Precision.DECADE, Qualifier.CIRCA, date(2010, 1, 1)),
    ],
)
def test_criterion_39_no_latest_bound_is_after_the_submission_date(
    precision: Precision, qualifier: Qualifier, value: date
) -> None:
    assert _range(precision, qualifier, value).latest == SUBMITTED_ON


def test_criterion_39_before_is_also_truncated_at_the_submission_date() -> None:
    assert _range(Precision.YEAR, Qualifier.BEFORE, date(2027, 1, 1)).latest == SUBMITTED_ON


@pytest.mark.parametrize("qualifier", [Qualifier.CIRCA, Qualifier.BEFORE, Qualifier.AFTER])
def test_criterion_39_a_second_value_is_rejected_unless_exact(qualifier: Qualifier) -> None:
    with pytest.raises(ArchiveRuleViolation) as raised:
        UncertainDate(Precision.YEAR, qualifier, date(2014, 1, 1), date(2015, 1, 1))

    assert raised.value.code == "uncertain_date.second_value_requires_exact"


def test_a_second_value_must_be_later_than_the_first() -> None:
    with pytest.raises(ArchiveRuleViolation) as raised:
        UncertainDate(Precision.YEAR, Qualifier.EXACT, date(2015, 1, 1), date(2014, 1, 1))

    assert raised.value.code == "uncertain_date.second_value_not_later"


@pytest.mark.parametrize(
    ("qualifier", "first"),
    [(Qualifier.EXACT, None), (None, date(2016, 1, 1)), (Qualifier.EXACT, date(2016, 1, 1))],
)
def test_unknown_has_no_value_and_no_qualifier(
    qualifier: Qualifier | None, first: date | None
) -> None:
    with pytest.raises(ArchiveRuleViolation) as raised:
        UncertainDate(Precision.UNKNOWN, qualifier, first)

    assert raised.value.code == "uncertain_date.unknown_takes_no_value"


@pytest.mark.parametrize("precision", [Precision.DAY, Precision.MONTH, Precision.YEAR])
def test_a_known_precision_needs_a_qualifier_and_a_value(precision: Precision) -> None:
    with pytest.raises(ArchiveRuleViolation) as no_qualifier:
        UncertainDate(precision, None, date(2016, 1, 1))
    with pytest.raises(ArchiveRuleViolation) as no_value:
        UncertainDate(precision, Qualifier.EXACT, None)

    assert no_qualifier.value.code == "uncertain_date.qualifier_required"
    assert no_value.value.code == "uncertain_date.value_required"


@pytest.mark.parametrize(
    ("precision", "value"),
    [
        (Precision.MONTH, date(2016, 3, 12)),
        (Precision.YEAR, date(2016, 3, 1)),
        (Precision.DECADE, date(1995, 1, 1)),
        (Precision.DECADE, date(1990, 2, 1)),
    ],
)
def test_a_value_must_be_the_first_day_of_its_precision(precision: Precision, value: date) -> None:
    with pytest.raises(ArchiveRuleViolation) as raised:
        UncertainDate(precision, Qualifier.EXACT, value)

    assert raised.value.code == "uncertain_date.value_not_at_precision"


@pytest.mark.parametrize(
    ("precision", "value"),
    [
        (Precision.DAY, date(2026, 10, 12)),
        (Precision.MONTH, date(2026, 11, 1)),
        (Precision.YEAR, date(2027, 1, 1)),
    ],
)
def test_a_date_entirely_after_the_submission_date_is_rejected(
    precision: Precision, value: date
) -> None:
    with pytest.raises(ArchiveRuleViolation) as raised:
        _range(precision, Qualifier.EXACT, value)

    assert raised.value.code == "uncertain_date.after_submission"


def test_after_a_value_ending_on_the_submission_date_is_rejected() -> None:
    with pytest.raises(ArchiveRuleViolation) as raised:
        _range(Precision.DAY, Qualifier.AFTER, SUBMITTED_ON)

    assert raised.value.code == "uncertain_date.after_submission"


# Chronological key: the midpoint of the base range of the entered values.
@pytest.mark.parametrize(
    ("uncertain_date", "key"),
    [
        (UncertainDate(Precision.YEAR, Qualifier.EXACT, YEAR), datetime(2016, 7, 2)),
        (UncertainDate(Precision.YEAR, Qualifier.CIRCA, YEAR), datetime(2016, 7, 2)),
        (
            UncertainDate(Precision.YEAR, Qualifier.EXACT, date(2014, 1, 1), date(2015, 1, 1)),
            datetime(2015, 1, 1),
        ),
        (UncertainDate(Precision.DAY, Qualifier.EXACT, DAY), datetime(2016, 3, 12, 12)),
        (UncertainDate(Precision.MONTH, Qualifier.EXACT, MONTH), datetime(2016, 3, 16, 12)),
        (UncertainDate(Precision.DECADE, Qualifier.EXACT, DECADE), datetime(1995, 1, 1)),
        (UncertainDate(Precision.YEAR, Qualifier.BEFORE, YEAR), datetime(2016, 1, 1)),
        (UncertainDate(Precision.YEAR, Qualifier.AFTER, YEAR), datetime(2017, 1, 1)),
        (UncertainDate(Precision.MONTH, Qualifier.AFTER, MONTH), datetime(2016, 4, 1)),
    ],
)
def test_the_chronological_key_is_the_midpoint_of_the_entered_values(
    uncertain_date: UncertainDate, key: datetime
) -> None:
    assert uncertain_date.chronological_key == key


def test_an_unknown_date_has_no_chronological_key() -> None:
    assert UncertainDate.unknown().chronological_key is None


def test_the_chronological_key_ignores_the_submission_date_truncation() -> None:
    this_year = UncertainDate(Precision.YEAR, Qualifier.EXACT, date(2026, 1, 1))

    assert this_year.range(SUBMITTED_ON).latest == SUBMITTED_ON
    assert this_year.chronological_key == datetime(2026, 7, 2, 12)
