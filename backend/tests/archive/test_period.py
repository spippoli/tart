"""Periods: an Artist's period of activity or a Crew membership period (archive-records spec)."""

from datetime import date

import pytest

from tart.archive import ArchiveRuleViolation, Period, Precision, Qualifier, UncertainDate


def _year(year: int, qualifier: Qualifier = Qualifier.EXACT) -> UncertainDate:
    return UncertainDate(Precision.YEAR, qualifier, date(year, 1, 1))


def test_criterion_46_a_start_with_a_later_key_than_the_end_is_rejected() -> None:
    with pytest.raises(ArchiveRuleViolation) as raised:
        Period(start=_year(2016), end=_year(2012))

    assert raised.value.code == "period.start_after_end"


def test_criterion_46_the_start_key_is_compared_with_the_end_key_ignoring_circa() -> None:
    # c. 2016 and 2016 share the key mid-2016, so neither is later than the other.
    period = Period(start=_year(2016, Qualifier.CIRCA), end=_year(2016))

    assert period.start == _year(2016, Qualifier.CIRCA)


def test_criterion_46_a_period_may_have_only_a_start_or_only_an_end() -> None:
    assert Period(start=_year(2010)).end is None
    assert Period(end=_year(2012)).start is None


def test_a_period_with_neither_start_nor_end_does_not_exist() -> None:
    with pytest.raises(ArchiveRuleViolation) as raised:
        Period()

    assert raised.value.code == "period.empty"


def test_an_unknown_bound_is_not_compared() -> None:
    period = Period(start=UncertainDate.unknown(), end=_year(2012))

    assert period.end == _year(2012)


def _period(start: int | None, end: int | None) -> Period:
    return Period(
        start=_year(start) if start is not None else None,
        end=_year(end) if end is not None else None,
    )


@pytest.mark.parametrize(
    ("first", "second", "overlap"),
    [
        ((2010, 2012), (2014, 2016), False),
        ((2014, 2016), (2010, 2012), False),
        ((2010, 2014), (2014, 2016), True),  # equal keys overlap
        ((2010, 2015), (2012, 2013), True),
        ((2010, None), (2016, 2018), True),  # open-ended: everything after its start
        ((2016, None), (2010, 2012), False),
        ((None, 2012), (2010, 2011), True),
        ((None, 2012), (2014, None), False),
    ],
)
def test_periods_overlap_by_chronological_key(
    first: tuple[int | None, int | None], second: tuple[int | None, int | None], overlap: bool
) -> None:
    assert _period(*first).overlaps(_period(*second)) is overlap
    assert _period(*second).overlaps(_period(*first)) is overlap


def test_an_unknown_end_is_open() -> None:
    unknown_end = Period(start=_year(2010), end=UncertainDate.unknown())

    assert unknown_end.overlaps(_period(2016, 2018))
