"""The rules one record must satisfy on its own, given the Instance configuration.

Rules across records (references, Attribution citations and Aliases, Crew
membership cycles, one Location per image) are checked by the write operation,
which can see the other records.
"""

import re
from collections.abc import Mapping
from dataclasses import MISSING, dataclass, fields
from datetime import date
from typing import Any
from zoneinfo import ZoneInfo

from tart.archive.errors import ArchiveRuleViolation
from tart.archive.geometry import Boundary, GeometryKind
from tart.archive.records import (
    Area,
    Artist,
    Artwork,
    Certainty,
    DocumentationItem,
    Location,
    Medium,
    Record,
    RightsBasis,
    Source,
    item_key,
)
from tart.archive.uncertain_date import Period, UncertainDate

PLACE_DESCRIPTION_MAX_LENGTH = 200
ALT_TEXT_MAX_LENGTH = 250

_URL = re.compile(r"^https?://\S+$")


@dataclass(frozen=True)
class InstanceRules:
    """What the Instance configuration says about records."""

    boundary: Boundary
    time_zone: ZoneInfo
    expression_types: Mapping[str, bool]
    """Open vocabulary keys, each with whether it is retired."""
    surface_types: Mapping[str, bool]
    file_licences: frozenset[str]


def _vocabulary_keys(
    vocabulary: Mapping[str, bool], keys: tuple[str, ...], previous: tuple[str, ...], code: str
) -> None:
    """Every key is in the vocabulary; a retired one only where the record already had it."""
    for key in keys:
        if key not in vocabulary or (vocabulary[key] and key not in previous):
            raise ArchiveRuleViolation(code)


def _present_fields(record: Record) -> None:
    """Required fields have a value, and no text field is blank: an absent value is `None`."""
    for field in fields(record):  # type: ignore[arg-type]
        value = getattr(record, field.name)
        required = field.default is MISSING
        if required and (value is None or (isinstance(value, str) and not value.strip())):
            raise ArchiveRuleViolation(f"{record.KIND}.{field.name}_required")
        if isinstance(value, str) and not value.strip():
            raise ArchiveRuleViolation(f"{record.KIND}.{field.name}_blank")
        for item in value if isinstance(value, tuple) else ():
            for text in (item, getattr(item, "alias", None), getattr(item, "note", None)):
                if isinstance(text, str) and not text.strip():
                    raise ArchiveRuleViolation(f"{record.KIND}.{field.name}_blank")


def _unique_items(record: Record) -> None:
    for collection in record.COLLECTIONS:
        keys = [item_key(item) for item in getattr(record, collection)]
        if len(keys) != len(set(keys)):
            raise ArchiveRuleViolation(f"{record.KIND}.{collection}_duplicated")


def _dates(value: Any) -> list[UncertainDate]:
    if isinstance(value, UncertainDate):
        return [value]
    if isinstance(value, Period):
        return [date for date in (value.start, value.end) if date is not None]
    return []


def _new_dates(record: Record, before: Record | None) -> list[UncertainDate]:
    """The Uncertain dates the change introduces, including those inside items."""
    values: list[Any] = []
    for field in fields(record):  # type: ignore[arg-type]
        value = getattr(record, field.name)
        if before is not None and getattr(before, field.name) == value:
            continue
        values += list(value) if isinstance(value, tuple) else [value]
    found: list[UncertainDate] = []
    for value in values:
        found += _dates(value)
        found += _dates(getattr(value, "period", None))
    return found


def _url(value: str | None, code: str) -> None:
    if value is not None and not _URL.match(value):
        raise ArchiveRuleViolation(code)


def check_record(
    record: Record, before: Record | None, rules: InstanceRules, submitted_on: date
) -> None:
    """Raise `ArchiveRuleViolation` unless the record satisfies the rules of its kind.

    `before` is the record as currently stored, `None` for a new one; `submitted_on`
    is the date of the Submission, in the Instance's time zone.
    """
    _present_fields(record)
    _unique_items(record)
    for uncertain_date in _new_dates(record, before):
        uncertain_date.range(submitted_on)  # rejects a date after the Submission
    match record:
        case Artwork():
            _check_artwork(record, before, rules)
        case Location():
            _check_location(record, before, rules)
        case Area():
            if record.geometry.kind is not GeometryKind.POLYGON:
                raise ArchiveRuleViolation("area.geometry_not_polygon")
        case Artist():
            _check_crew_periods(record)
        case Source():
            _url(record.url, "source.url_invalid")
        case DocumentationItem():
            _check_documentation_item(record, before, rules)


def _check_crew_periods(record: Artist) -> None:
    """Memberships in the same collective may repeat only over periods that do not overlap."""
    memberships = record.crew_memberships
    for index, membership in enumerate(memberships):
        for other in memberships[index + 1 :]:
            if other.collective != membership.collective:
                continue
            if (
                membership.period is None
                or other.period is None
                or membership.period.overlaps(other.period)
            ):
                raise ArchiveRuleViolation("crew_membership.periods_overlap")


def _check_artwork(record: Artwork, before: Record | None, rules: InstanceRules) -> None:
    if not record.expression_types:
        raise ArchiveRuleViolation("artwork.expression_types_required")
    if len(set(record.expression_types)) != len(record.expression_types):
        raise ArchiveRuleViolation("artwork.expression_types_duplicated")
    previous = before.expression_types if isinstance(before, Artwork) else ()
    _vocabulary_keys(
        rules.expression_types,
        record.expression_types,
        previous,
        "artwork.expression_type_unknown",
    )
    for attribution in record.attributions:
        if attribution.certainty is Certainty.CONFIRMED and not attribution.citations:
            raise ArchiveRuleViolation("attribution.confirmed_requires_citation")
        if len(set(attribution.citations)) != len(attribution.citations):
            raise ArchiveRuleViolation("attribution.citations_duplicated")


def _check_location(record: Location, before: Record | None, rules: InstanceRules) -> None:
    if not rules.boundary.covers(record.geometry):
        raise ArchiveRuleViolation("location.outside_boundary")
    if record.uncertainty_radius is not None:
        if not (record.approximate and record.geometry.kind is GeometryKind.POINT):
            raise ArchiveRuleViolation("location.radius_requires_approximate_point")
        if record.uncertainty_radius <= 0:
            raise ArchiveRuleViolation("location.radius_not_positive")
    previous = (before.surface_type,) if isinstance(before, Location) else ()
    _vocabulary_keys(
        rules.surface_types, (record.surface_type,), previous, "location.surface_type_unknown"
    )
    description = record.place_description
    if description is not None:
        if len(description) > PLACE_DESCRIPTION_MAX_LENGTH:
            raise ArchiveRuleViolation("location.place_description_too_long")
        if "\n" in description or "\r" in description:
            raise ArchiveRuleViolation("location.place_description_not_one_line")


_FILE_FIELDS = ("file", "licence", "creator_credit", "rights_basis")
_FIELDS_BY_MEDIUM = {
    Medium.IMAGE: {*_FILE_FIELDS, "origin_url", "alt_text"},
    Medium.PDF: {*_FILE_FIELDS, "origin_url"},
    Medium.TEXT: {"text", "language"},
    Medium.LINK: {"url", "language"},
}
_REQUIRED_BY_MEDIUM = {
    Medium.IMAGE: {*_FILE_FIELDS, "alt_text"},
    Medium.PDF: set(_FILE_FIELDS),
    Medium.TEXT: {"text"},
    Medium.LINK: {"url"},
}


def _check_documentation_item(
    record: DocumentationItem, before: Record | None, rules: InstanceRules
) -> None:
    if isinstance(before, DocumentationItem):
        for name in DocumentationItem.IMMUTABLE:
            if getattr(record, name) != getattr(before, name):
                raise ArchiveRuleViolation(f"documentation_item.{name}_immutable")
    if not record.artworks:
        raise ArchiveRuleViolation("documentation_item.artworks_required")
    optional = {"file", "licence", "creator_credit", "rights_basis", "origin_url"}
    optional |= {"alt_text", "text", "url", "language"}
    allowed = _FIELDS_BY_MEDIUM[record.medium]
    for name in sorted(optional):
        value = getattr(record, name)
        if value is None and name in _REQUIRED_BY_MEDIUM[record.medium]:
            raise ArchiveRuleViolation(f"documentation_item.{name}_required")
        if value is not None and name not in allowed:
            raise ArchiveRuleViolation(f"documentation_item.{name}_not_applicable")
    if record.rights_basis is RightsBasis.THIRD_PARTY and record.origin_url is None:
        raise ArchiveRuleViolation("documentation_item.origin_url_required")
    if record.alt_text is not None and len(record.alt_text) > ALT_TEXT_MAX_LENGTH:
        raise ArchiveRuleViolation("documentation_item.alt_text_too_long")
    if (
        record.licence is not None
        and (before is None or record.licence != getattr(before, "licence", None))
        and record.licence not in rules.file_licences
    ):
        raise ArchiveRuleViolation("documentation_item.licence_not_allowed")
    _url(record.origin_url, "documentation_item.origin_url_invalid")
    _url(record.url, "documentation_item.url_invalid")
