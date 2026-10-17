"""What the Submission page compares: the current record against the proposed data, an
image against the Artwork's latest image, a geometry against the one it replaces
(contribution-and-moderation spec, Submission page).

    comparison = await compare(connection, submission)

It reads the archive and never changes it. The comparison is of the last submitted round.
"""

import json
from dataclasses import dataclass
from datetime import datetime

from geoalchemy2 import Geometry as GeometryType
from sqlalchemy import cast, func, select
from sqlalchemy.ext.asyncio import AsyncConnection

from tart.archive.changeset import AddItem, ChangeItem, Create, RemoveItem, SetField
from tart.archive.codec import Json, decode_uncertain_date, encode, encode_uncertain_date
from tart.archive.geometry import Geometry
from tart.archive.records import Area, DocumentationItem, Kind, Location, Medium, item_key
from tart.archive_persistence import PostgresArchiveStore
from tart.archive_persistence import tables as t
from tart.moderation import GeometrySummary, Submission, decode_content, summarise
from tart.moderation_persistence.duplicates import PostgresDuplicateQuery

DATE_FLOOR = datetime.min
"""Sorts an unknown Observed date before every other."""


@dataclass(frozen=True)
class ImageSide:
    """One of the two images side by side, with what its caption says."""

    file: str
    """The upload id: `/api/media/{file}/view`."""
    observed_date: Json
    creator_credit: str | None
    licence: str | None
    alt_text: str | None
    item_id: int | None
    """The Documentation item; `None` for the proposed file."""


@dataclass(frozen=True)
class ImageComparison:
    proposed: ImageSide
    current: ImageSide | None
    """The most recent image Documentation item of the Artwork; `None` when it has none."""


@dataclass(frozen=True)
class NearLocationFound:
    id: int
    distance_metres: float


@dataclass(frozen=True)
class GeometryComparison:
    record_kind: Kind
    target_id: int | None
    current: Json
    """GeoJSON; `None` for a new record."""
    proposed: Json
    summary: GeometrySummary
    near_locations: tuple[NearLocationFound, ...]
    """For a Location: the others within the proximity rule, nearest first."""
    locations_entering: int | None
    locations_leaving: int | None
    """For an Area: how many Locations the proposed polygon takes in and lets go."""


@dataclass(frozen=True)
class Comparison:
    current_values: dict[int, Json]
    """By index of the round's operation: the field or item it changes, as it is now."""
    images: tuple[ImageComparison, ...]
    geometries: tuple[GeometryComparison, ...]


EMPTY = Comparison({}, (), ())


def _image_side(item: DocumentationItem, item_id: int | None) -> ImageSide:
    assert item.file is not None
    return ImageSide(
        item.file,
        encode_uncertain_date(item.observed_date),
        item.creator_credit,
        item.licence,
        item.alt_text,
        item_id,
    )


async def _latest_image(connection: AsyncConnection, artwork_id: int) -> ImageSide | None:
    """The Artwork's public image Documentation item with the latest Observed date."""
    rows = (
        await connection.execute(
            select(
                t.documentation_item.c.id,
                t.documentation_item.c.file,
                t.documentation_item.c.observed_date,
                t.documentation_item.c.creator_credit,
                t.documentation_item.c.licence,
                t.documentation_item.c.alt_text,
            )
            .join(
                t.documentation_item_artwork,
                t.documentation_item_artwork.c.item_id == t.documentation_item.c.id,
            )
            .join(t.record, t.record.c.id == t.documentation_item.c.id)
            .where(
                t.documentation_item_artwork.c.artwork_id == artwork_id,
                t.documentation_item.c.medium == Medium.IMAGE.value,
                t.documentation_item.c.file.is_not(None),
                t.record.c.withdrawn_at.is_(None),
                t.record.c.merged_into.is_(None),
            )
        )
    ).all()
    if not rows:
        return None

    def recency(row) -> tuple[datetime, int]:  # type: ignore[no-untyped-def]
        moment = decode_uncertain_date(row.observed_date).chronological_key
        return (moment.replace(tzinfo=None) if moment else DATE_FLOOR, row.id)

    latest = max(rows, key=recency)
    return ImageSide(
        latest.file,
        latest.observed_date,
        latest.creator_credit,
        latest.licence,
        latest.alt_text,
        latest.id,
    )


def _current_value(record: object, operation: object) -> Json:
    """The field or item that the operation changes, as the record has it now."""
    match operation:
        case SetField(field=field):
            value = getattr(record, field, None)
        case ChangeItem(collection=collection, item=item):
            key = item_key(item)
            value = next(
                (each for each in getattr(record, collection, ()) if item_key(each) == key), None
            )
        case RemoveItem(collection=collection, key=key):
            value = next(
                (each for each in getattr(record, collection, ()) if item_key(each) == key), None
            )
        case _:
            return None
    try:
        return encode(value)
    except TypeError, ValueError:
        return None


def _polygon(geometry: Geometry | None) -> object:
    return func.ST_SetSRID(func.ST_GeomFromGeoJSON(json.dumps(geometry.to_geojson())), 4326)


async def _locations_inside(connection: AsyncConnection, area: Geometry | None) -> set[int]:
    if area is None:
        return set()
    rows = await connection.scalars(
        select(t.location.c.id)
        .join(t.record, t.record.c.id == t.location.c.id)
        .where(
            t.record.c.withdrawn_at.is_(None),
            t.record.c.merged_into.is_(None),
            func.ST_Intersects(cast(t.location.c.geometry, GeometryType), _polygon(area)),
        )
    )
    return set(rows)


async def _geometry_comparison(
    connection: AsyncConnection,
    kind: Kind,
    target_id: int | None,
    current: Geometry | None,
    proposed: Geometry,
    radius: int | None,
) -> GeometryComparison:
    near: tuple[NearLocationFound, ...] = ()
    entering = leaving = None
    if kind is Kind.LOCATION:
        found = await PostgresDuplicateQuery(connection).locations_near(proposed, radius)
        near = tuple(
            NearLocationFound(each.id, round(each.distance, 1))
            for each in found
            if each.id != target_id
        )
    else:
        before = await _locations_inside(connection, current)
        after = await _locations_inside(connection, proposed)
        entering, leaving = len(after - before), len(before - after)
    return GeometryComparison(
        kind,
        target_id,
        current.to_geojson() if current else None,
        proposed.to_geojson(),
        summarise(current, proposed),
        near,
        entering,
        leaving,
    )


async def compare(connection: AsyncConnection, submission: Submission) -> Comparison:
    """The comparison of the Submission's last submitted round; empty for a draft or a stub."""
    if submission.reduced_at is not None or not submission.rounds:
        return EMPTY
    content = decode_content(submission.rounds[-1].snapshot, submission.target_kind)
    target = None
    if submission.target_id is not None:
        target = await PostgresArchiveStore(connection).get(submission.target_id)

    current_values: dict[int, Json] = {}
    images: list[ImageComparison] = []
    geometries: list[GeometryComparison] = []
    for index, operation in enumerate(content.operations):
        match operation:
            case Create(record=DocumentationItem(medium=Medium.IMAGE, file=str()) as item):
                artworks = [each for each in item.artworks if isinstance(each, int)]
                latest = await _latest_image(connection, artworks[0]) if artworks else None
                images.append(ImageComparison(_image_side(item, None), latest))
            case Create(record=Location() as place):
                geometries.append(
                    await _geometry_comparison(
                        connection,
                        Kind.LOCATION,
                        None,
                        None,
                        place.geometry,
                        place.uncertainty_radius,
                    )
                )
            case Create(record=Area() as area):
                geometries.append(
                    await _geometry_comparison(
                        connection, Kind.AREA, None, None, area.geometry, None
                    )
                )
            case SetField(target=changed, field="geometry", value=Geometry() as proposed) if (
                target is not None and changed == submission.target_id
            ):
                if isinstance(target, Location | Area):
                    radius = getattr(target, "uncertainty_radius", None)
                    geometries.append(
                        await _geometry_comparison(
                            connection,
                            target.KIND,
                            submission.target_id,
                            target.geometry,
                            proposed,
                            radius,
                        )
                    )
        match operation:
            case SetField(target=changed) | ChangeItem(target=changed) | RemoveItem(target=changed):
                if target is not None and changed == submission.target_id:
                    current_values[index] = _current_value(target, operation)
            case AddItem():
                pass
    return Comparison(current_values, tuple(images), tuple(geometries))
