"""JSON forms of archive values, for Revision change lists and stored dates and periods."""

from dataclasses import fields, is_dataclass
from datetime import date
from enum import StrEnum
from typing import Any

from tart.archive.geometry import Geometry
from tart.archive.records import New
from tart.archive.uncertain_date import Period, Precision, Qualifier, UncertainDate

type Json = bool | int | float | str | list[Json] | dict[str, Json] | None


def encode(value: Any) -> Json:
    """The JSON form of a field value or a collection item."""
    match value:
        case None | bool() | int() | float():
            return value
        case StrEnum():
            return value.value
        case str():
            return value
        case New():
            raise ValueError(f"unresolved reference to the new record {value.key!r}")
        case UncertainDate():
            return encode_uncertain_date(value)
        case Period():
            return encode_period(value)
        case Geometry():
            return value.to_geojson()
        case tuple() | list():
            return [encode(item) for item in value]
        case _ if is_dataclass(value) and not isinstance(value, type):
            return {field.name: encode(getattr(value, field.name)) for field in fields(value)}
    raise TypeError(f"cannot encode {value!r}")


def encode_uncertain_date(value: UncertainDate) -> dict[str, Json]:
    return {
        "precision": value.precision.value,
        "qualifier": value.qualifier.value if value.qualifier else None,
        "first": value.first.isoformat() if value.first else None,
        "second": value.second.isoformat() if value.second else None,
    }


def decode_uncertain_date(value: dict[str, Any]) -> UncertainDate:
    return UncertainDate(
        Precision(value["precision"]),
        Qualifier(value["qualifier"]) if value.get("qualifier") else None,
        date.fromisoformat(value["first"]) if value.get("first") else None,
        date.fromisoformat(value["second"]) if value.get("second") else None,
    )


def encode_period(value: Period) -> dict[str, Json]:
    return {
        "start": encode_uncertain_date(value.start) if value.start else None,
        "end": encode_uncertain_date(value.end) if value.end else None,
    }


def decode_period(value: dict[str, Any]) -> Period:
    return Period(
        decode_uncertain_date(value["start"]) if value.get("start") else None,
        decode_uncertain_date(value["end"]) if value.get("end") else None,
    )
