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
