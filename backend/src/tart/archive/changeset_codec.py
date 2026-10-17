"""The JSON form of a changeset, as a Submission stores it (ADR 0007).

    json = encode_changeset(changeset)
    changeset = decode_changeset(json, Kind.ARTWORK)

A reference to a record the changeset creates is `{"new": key}`; a reference to an
existing record is its id. Decoding is driven by the dataclasses of the record kinds, so
a record kind that gains a field needs no change here. `target_kind` is the kind of the
existing record an edit changes; the kind of a new record comes from its `Create`.
Anything that does not fit raises `ArchiveRuleViolation("changeset.malformed")`.
"""

from collections.abc import Mapping
from dataclasses import MISSING, fields, is_dataclass
from types import NoneType, UnionType
from typing import Any, TypeAliasType, Union, get_args, get_origin, get_type_hints

from tart.archive.changeset import (
    AddItem,
    ChangeItem,
    Changeset,
    Create,
    Merge,
    Operation,
    RemoveItem,
    SetField,
    Unmerge,
)
from tart.archive.codec import Json, decode_period, decode_uncertain_date, encode
from tart.archive.errors import ArchiveRuleViolation
from tart.archive.geometry import Geometry
from tart.archive.records import RECORD_TYPES, Kind, New, Record
from tart.archive.uncertain_date import Period, UncertainDate

MALFORMED = "changeset.malformed"


def encode_value(value: Any) -> Json:
    """The JSON form of a record value, with `New` references."""
    match value:
        case New():
            return {"new": value.key}
        case tuple() | list():
            return [encode_value(item) for item in value]
        case UncertainDate() | Period() | Geometry():
            return encode(value)
        case _ if is_dataclass(value) and not isinstance(value, type):
            return {field.name: encode_value(getattr(value, field.name)) for field in fields(value)}
    return encode(value)


def encode_operation(operation: Operation) -> Json:
    encoded = _encode_operation(operation)
    kind = getattr(operation, "kind", None)
    if kind is not None and isinstance(encoded, dict):
        encoded["kind"] = kind.value
    return encoded


def _encode_operation(operation: Operation) -> Json:
    match operation:
        case Create(ref=ref, record=record):
            return {
                "op": "create",
                "ref": ref.key,
                "kind": record.KIND.value,
                "record": encode_value(record),
            }
        case SetField():
            return {
                "op": "set",
                "target": encode_value(operation.target),
                "field": operation.field,
                "value": encode_value(operation.value),
            }
        case AddItem() | ChangeItem():
            return {
                "op": "add" if isinstance(operation, AddItem) else "change",
                "target": encode_value(operation.target),
                "collection": operation.collection,
                "item": encode_value(operation.item),
            }
        case RemoveItem():
            return {
                "op": "remove",
                "target": encode_value(operation.target),
                "collection": operation.collection,
                "key": encode_value(operation.key),
            }
        case Merge() | Unmerge():
            return {
                "op": "merge" if isinstance(operation, Merge) else "unmerge",
                "source": operation.source,
                "into": operation.into,
            }
    raise TypeError(f"cannot encode {operation!r}")


def encode_changeset(changeset: Changeset) -> Json:
    return [encode_operation(operation) for operation in changeset]


def _object(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise TypeError("an object was expected")
    return value


def decode_value(type_: Any, value: Any) -> Any:
    """The value of the given type from its JSON form."""
    if isinstance(type_, TypeAliasType):
        return decode_value(type_.__value__, value)
    origin, args = get_origin(type_), get_args(type_)
    if origin in (Union, UnionType):
        return _decode_union(args, value)
    if origin is tuple:
        if not isinstance(value, list):
            raise TypeError("a list was expected")
        if len(args) == 2 and args[1] is Ellipsis:
            return tuple(decode_value(args[0], item) for item in value)
        if len(args) != len(value):
            raise ValueError("a list of another length was expected")
        return tuple(decode_value(arg, item) for arg, item in zip(args, value, strict=True))
    if type_ is Any:
        return value
    if type_ is bool or type_ is str:
        if not isinstance(value, type_):
            raise TypeError("another type was expected")
        return value
    if type_ is int or type_ is float:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise TypeError("a number was expected")
        return type_(value)
    if type_ is New:
        obj = _object(value)
        if set(obj) != {"new"} or not isinstance(obj["new"], str):
            raise TypeError("a reference to a new record was expected")
        return New(obj["new"])
    if type_ is UncertainDate:
        return decode_uncertain_date(_object(value))
    if type_ is Period:
        return decode_period(_object(value))
    if type_ is Geometry:
        return Geometry.from_geojson(_object(value))
    if isinstance(type_, type):
        if issubclass(type_, str):  # a StrEnum
            return type_(value)
        if is_dataclass(type_):
            return _decode_dataclass(type_, _object(value))
    raise TypeError(f"cannot decode {type_!r}")


def _decode_union(args: tuple[Any, ...], value: Any) -> Any:
    if value is None:
        if NoneType in args:
            return None
        raise TypeError("a value was expected")
    failure: Exception | None = None
    for arg in args:
        if arg is NoneType:
            continue
        try:
            return decode_value(arg, value)
        except (TypeError, ValueError, KeyError) as error:
            failure = error
    raise failure or TypeError("no alternative fits")


def _decode_dataclass(type_: type, obj: Mapping[str, Any], *, lenient: bool = False) -> Any:
    """`lenient` reads an absent or null required field as `None`, which the archive's
    rules then refuse with the field's own code, instead of refusing the whole snapshot."""
    hints = get_type_hints(type_)
    known = {field.name for field in fields(type_)}
    if not set(obj) <= known:
        raise ValueError("unknown fields")
    values = {
        name: decode_value(hints[name], value)
        for name, value in obj.items()
        if not (lenient and value is None)
    }
    if lenient:
        for field in fields(type_):
            required = field.default is MISSING and field.default_factory is MISSING
            if required and obj.get(field.name) is None:
                values[field.name] = None
    return type_(**values)


def item_type(record_type: type[Record], collection: str) -> Any:
    """The type of the items of a collection field of a record kind."""
    if collection not in record_type.COLLECTIONS:
        raise ArchiveRuleViolation("changeset.unknown_collection")
    return get_args(get_type_hints(record_type)[collection])[0]


def _key_type(item_type_: Any) -> Any:
    if isinstance(item_type_, type) and is_dataclass(item_type_):
        return get_type_hints(item_type_.key.fget)["return"]  # type: ignore[attr-defined]
    return item_type_


def decode_operation(
    value: Json, target_kinds: Mapping[str, Kind], target_kind: Kind | None
) -> Operation:
    """One operation. `target_kinds` gives the kind of each new record by key."""
    obj = _object(value)
    op = obj["op"]
    if op == "create":
        kind = Kind(obj["kind"])
        record = _decode_dataclass(RECORD_TYPES[kind], _object(obj["record"]), lenient=True)
        return Create(New(obj["ref"]), record)
    if op in ("merge", "unmerge"):
        source, into = decode_value(int, obj["source"]), decode_value(int, obj["into"])
        return Merge(source, into) if op == "merge" else Unmerge(source, into)
    target = decode_value(int | New, obj["target"])
    stated = Kind(obj["kind"]) if obj.get("kind") else None
    kind = target_kinds.get(target.key) if isinstance(target, New) else stated or target_kind
    if kind is None:
        raise ValueError("the target has no kind")
    record_type = RECORD_TYPES[kind]
    if op == "set":
        if obj["field"] not in record_type.field_names() or obj["field"] in record_type.COLLECTIONS:
            raise ArchiveRuleViolation("changeset.unknown_field")
        hints = get_type_hints(record_type)
        value = decode_value(hints[obj["field"]], obj["value"])
        return SetField(target, obj["field"], value, stated)
    collection = obj["collection"]
    items = item_type(record_type, collection)
    if op == "add":
        return AddItem(target, collection, decode_value(items, obj["item"]), stated)
    if op == "change":
        return ChangeItem(target, collection, decode_value(items, obj["item"]), stated)
    if op == "remove":
        return RemoveItem(target, collection, decode_value(_key_type(items), obj["key"]), stated)
    raise ValueError("unknown operation")


def decode_changeset(value: Json, target_kind: Kind | None) -> Changeset:
    """The changeset of its JSON form; `target_kind` is the kind an edit changes."""
    try:
        if not isinstance(value, list):
            raise TypeError("a list was expected")
        new_kinds = {
            _object(op)["ref"]: Kind(op["kind"])
            for op in value
            if isinstance(op, dict) and op.get("op") == "create"
        }
        return tuple(decode_operation(op, new_kinds, target_kind) for op in value)
    except ArchiveRuleViolation:
        raise
    except TypeError, ValueError, KeyError, AttributeError:
        raise ArchiveRuleViolation(MALFORMED) from None


def decode_item(record_type: type[Record], collection: str, value: Json) -> Any:
    """An item of a collection of a record kind, as a Revision's change list stores it."""
    try:
        return decode_value(item_type(record_type, collection), value)
    except ArchiveRuleViolation:
        raise
    except TypeError, ValueError, KeyError, AttributeError:
        raise ArchiveRuleViolation(MALFORMED) from None
