"""The Uncertain date value and the period built from two of them (archive-records spec)."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import StrEnum

from tart.archive.errors import ArchiveRuleViolation

_ONE_DAY = timedelta(days=1)


class Precision(StrEnum):
    DAY = "day"
    MONTH = "month"
    YEAR = "year"
    DECADE = "decade"
    UNKNOWN = "unknown"


class Qualifier(StrEnum):
    EXACT = "exact"
    CIRCA = "circa"
    BEFORE = "before"
    AFTER = "after"


@dataclass(frozen=True)
class DateRange:
    """Day-precise earliest and latest bounds, both inclusive; `None` is an open bound."""

    earliest: date | None
    latest: date | None


def _months_in_unit(precision: Precision) -> int:
    return {Precision.MONTH: 1, Precision.YEAR: 12, Precision.DECADE: 120}[precision]


def _shift(value: date, precision: Precision, units: int) -> date:
    """The value `units` units of the precision later (earlier when negative)."""
    if precision is Precision.DAY:
        return value + units * _ONE_DAY
    months = value.year * 12 + value.month - 1 + units * _months_in_unit(precision)
    return date(months // 12, months % 12 + 1, 1)


def _base_range(value: date, precision: Precision) -> tuple[date, date]:
    """The first and the last day the value covers at its precision."""
    if precision is Precision.DAY:
        return value, value
    return value, _shift(value, precision, 1) - _ONE_DAY


def _is_at_precision(value: date, precision: Precision) -> bool:
    match precision:
        case Precision.DAY:
            return True
        case Precision.MONTH:
            return value.day == 1
        case Precision.YEAR:
            return (value.month, value.day) == (1, 1)
        case _:
            return (value.month, value.day) == (1, 1) and value.year % 10 == 0


def _start_of(day: date) -> datetime:
    return datetime(day.year, day.month, day.day)


@dataclass(frozen=True)
class UncertainDate:
    """A historical date: a precision, a qualifier, and one or two values at that precision.

    Each value is the first day of the unit it names: `date(2016, 3, 1)` is March 2016
    at `month` precision, `date(1990, 1, 1)` the 1990s at `decade` precision. A second
    value, allowed only with `exact`, gives the "from-to" form. `unknown` has no value
    and no qualifier.
    """

    precision: Precision
    qualifier: Qualifier | None = None
    first: date | None = None
    second: date | None = None

    @classmethod
    def unknown(cls) -> UncertainDate:
        return cls(Precision.UNKNOWN)

    def __post_init__(self) -> None:
        if self.precision is Precision.UNKNOWN:
            if self.qualifier is not None or self.first is not None or self.second is not None:
                raise ArchiveRuleViolation("uncertain_date.unknown_takes_no_value")
            return
        if self.qualifier is None:
            raise ArchiveRuleViolation("uncertain_date.qualifier_required")
        if self.first is None:
            raise ArchiveRuleViolation("uncertain_date.value_required")
        values = [self.first] if self.second is None else [self.first, self.second]
        if not all(_is_at_precision(value, self.precision) for value in values):
            raise ArchiveRuleViolation("uncertain_date.value_not_at_precision")
        if self.second is not None:
            if self.qualifier is not Qualifier.EXACT:
                raise ArchiveRuleViolation("uncertain_date.second_value_requires_exact")
            if self.second <= self.first:
                raise ArchiveRuleViolation("uncertain_date.second_value_not_later")

    def _entered_span(self) -> tuple[date, date]:
        """From the first day of the first value to the last day of the last value."""
        assert self.first is not None
        start, _ = _base_range(self.first, self.precision)
        _, end = _base_range(self.second or self.first, self.precision)
        return start, end

    def range(self, submitted_on: date) -> DateRange:
        """The earliest-to-latest range, used only for filtering by overlap.

        No latest bound is later than the date of the Submission. A date that lies
        entirely after it has no range and is rejected.
        """
        if self.precision is Precision.UNKNOWN:
            return DateRange(None, None)
        assert self.first is not None
        start, end = self._entered_span()
        earliest: date | None
        match self.qualifier:
            case Qualifier.EXACT:
                earliest, latest = start, end
            case Qualifier.CIRCA:
                earliest = _base_range(_shift(self.first, self.precision, -1), self.precision)[0]
                latest = _base_range(_shift(self.first, self.precision, 1), self.precision)[1]
            case Qualifier.BEFORE:
                earliest, latest = None, start - _ONE_DAY
            case _:
                earliest, latest = end + _ONE_DAY, submitted_on
        latest = min(latest, submitted_on)
        if earliest is not None and earliest > latest:
            raise ArchiveRuleViolation("uncertain_date.after_submission")
        return DateRange(earliest, latest)

    @property
    def chronological_key(self) -> datetime | None:
        """The instant that orders this date among others; `None` for an unknown date.

        It is the midpoint of the entered values' span, ignoring the widening of
        `circa`; `before X` is the start of X and `after X` the end of X. Callers
        break ties by the later approval, then by id.
        """
        if self.precision is Precision.UNKNOWN:
            return None
        start, end = self._entered_span()
        start_instant, end_instant = _start_of(start), _start_of(end + _ONE_DAY)
        match self.qualifier:
            case Qualifier.BEFORE:
                return start_instant
            case Qualifier.AFTER:
                return end_instant
            case _:
                return start_instant + (end_instant - start_instant) / 2


@dataclass(frozen=True)
class Period:
    """An Artist's period of activity or a Crew membership period.

    It has a start, an end, or both; with neither there is no period. The start's
    chronological key must not be later than the end's. No flag says that the period
    is ongoing.
    """

    start: UncertainDate | None = None
    end: UncertainDate | None = None

    def __post_init__(self) -> None:
        if self.start is None and self.end is None:
            raise ArchiveRuleViolation("period.empty")
        start_key = self.start.chronological_key if self.start else None
        end_key = self.end.chronological_key if self.end else None
        if start_key is not None and end_key is not None and start_key > end_key:
            raise ArchiveRuleViolation("period.start_after_end")

    def _bounds(self) -> tuple[datetime | None, datetime | None]:
        """The chronological keys of the start and the end; `None` is open."""
        return (
            self.start.chronological_key if self.start else None,
            self.end.chronological_key if self.end else None,
        )

    def overlaps(self, other: Period) -> bool:
        """Whether the two periods share any instant, comparing chronological keys.

        A missing start or end, or an `unknown` one, is open; equal keys overlap.
        """
        start, end = self._bounds()
        other_start, other_end = other._bounds()
        ends_before = end is not None and other_start is not None and end < other_start
        starts_after = start is not None and other_end is not None and other_end < start
        return not (ends_before or starts_after)
