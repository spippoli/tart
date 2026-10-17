"""The text summary of a geometry comparison (contribution-and-moderation spec, Submission page).

The Submission page overlays the current geometry and the proposed one on a map, and, below
it, says in words what changed. Without WebGL2 the words are all there is, so they carry the
whole comparison:

    summary = summarise(current, proposed)

Distances are planar, measured around the geometry's own latitude: exact enough at the scale
of one city, like the geometry checks of the archive.
"""

import math
from dataclasses import dataclass
from itertools import pairwise

from tart.archive.geometry import Geometry, GeometryKind, Position

METRES_PER_DEGREE = 111_320.0
"""Metres in a degree of latitude, and of longitude at the equator."""

COMPASS = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")


@dataclass(frozen=True)
class GeometrySummary:
    vertices_before: int | None
    """`None` for a new geometry."""
    vertices_after: int
    largest_shift_metres: float | None
    """How far the vertex that moved most moved; `None` for a new geometry."""
    shift_direction: str | None
    """Where it moved to, as a compass point (`N`, `NE`, ...); `None` when nothing moved."""
    area_change_square_metres: float | None
    """For two polygons: the surface after minus the surface before."""


def _vertices(geometry: Geometry) -> tuple[Position, ...]:
    """The distinct vertices: a polygon's closing position is not counted twice."""
    if geometry.kind is GeometryKind.POLYGON:
        return geometry.positions[:-1]
    return geometry.positions


def _offset(origin: Position, target: Position) -> tuple[float, float]:
    """Metres east and north from `origin` to `target`."""
    scale = math.cos(math.radians((origin[1] + target[1]) / 2))
    return (
        (target[0] - origin[0]) * METRES_PER_DEGREE * scale,
        (target[1] - origin[1]) * METRES_PER_DEGREE,
    )


def _compass(east: float, north: float) -> str:
    bearing = math.degrees(math.atan2(east, north)) % 360
    return COMPASS[round(bearing / 45) % 8]


def _surface(geometry: Geometry) -> float:
    """The area of a polygon in square metres (the shoelace formula on local metres)."""
    ring = geometry.positions
    origin = ring[0]
    points = [_offset(origin, position) for position in ring]
    twice = sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in pairwise(points))
    return abs(twice) / 2


def _largest_shift(
    before: tuple[Position, ...], after: tuple[Position, ...]
) -> tuple[float, str | None]:
    """With as many vertices as before, each moved from where it was; otherwise each
    vertex after is measured from the nearest vertex before."""
    best, direction = 0.0, None
    for index, vertex in enumerate(after):
        if len(before) == len(after):
            origin = before[index]
        else:
            origin = min(before, key=lambda each: math.hypot(*_offset(each, vertex)))
        east, north = _offset(origin, vertex)
        distance = math.hypot(east, north)
        if distance > best:
            best, direction = distance, _compass(east, north)
    return best, direction


def summarise(current: Geometry | None, proposed: Geometry) -> GeometrySummary:
    """What changes from the current geometry to the proposed one; `None` current is a new one."""
    after = _vertices(proposed)
    if current is None:
        return GeometrySummary(None, len(after), None, None, None)
    before = _vertices(current)
    shift, direction = _largest_shift(before, after)
    both_polygons = current.kind is proposed.kind is GeometryKind.POLYGON
    return GeometrySummary(
        len(before),
        len(after),
        round(shift, 1),
        direction,
        round(_surface(proposed) - _surface(current), 1) if both_polygons else None,
    )
