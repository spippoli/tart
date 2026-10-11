"""Location and Area geometries, and the Instance boundary they are checked against.

Geometries are WGS 84 longitude-latitude positions, read and written as GeoJSON
(`Point`, `LineString`, `Polygon`). The checks are planar, which is exact enough at
the scale of one city.
"""

import itertools
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from tart.archive.errors import ArchiveRuleViolation

type Position = tuple[float, float]
"""`(longitude, latitude)`."""


class GeometryKind(StrEnum):
    POINT = "Point"
    LINE = "LineString"
    POLYGON = "Polygon"


@dataclass(frozen=True)
class Geometry:
    """A point, a line, or a simple polygon without holes.

    A polygon's positions are its closed ring: the last position repeats the first.
    """

    kind: GeometryKind
    positions: tuple[Position, ...]

    def __post_init__(self) -> None:
        for longitude, latitude in self.positions:
            if not (
                math.isfinite(longitude)
                and math.isfinite(latitude)
                and -180 <= longitude <= 180
                and -90 <= latitude <= 90
            ):
                raise ArchiveRuleViolation("geometry.invalid_position")
        distinct = len(set(self.positions))
        match self.kind:
            case GeometryKind.POINT:
                if len(self.positions) != 1:
                    raise ArchiveRuleViolation("geometry.invalid")
            case GeometryKind.LINE:
                if distinct < 2:
                    raise ArchiveRuleViolation("geometry.invalid")
            case GeometryKind.POLYGON:
                if self.positions[0] != self.positions[-1] or distinct < 3:
                    raise ArchiveRuleViolation("geometry.invalid")
                if not _is_simple_ring(self.positions):
                    raise ArchiveRuleViolation("geometry.self_intersecting")
                if _ring_area(self.positions) == 0:
                    raise ArchiveRuleViolation("geometry.invalid")

    @classmethod
    def from_geojson(cls, geojson: Mapping[str, Any]) -> Geometry:
        """A geometry from a GeoJSON geometry object; a polygon with holes is refused."""
        try:
            kind = GeometryKind(geojson["type"])
            coordinates = geojson["coordinates"]
            match kind:
                case GeometryKind.POINT:
                    positions = (_position(coordinates),)
                case GeometryKind.LINE:
                    positions = tuple(_position(position) for position in coordinates)
                case GeometryKind.POLYGON:
                    if len(coordinates) != 1:
                        raise ArchiveRuleViolation("geometry.polygon_with_holes")
                    positions = tuple(_position(position) for position in coordinates[0])
        except (KeyError, TypeError, ValueError, IndexError) as error:
            if isinstance(error, ArchiveRuleViolation):
                raise
            raise ArchiveRuleViolation("geometry.invalid") from None
        return cls(kind, positions)

    def to_geojson(self) -> dict[str, Any]:
        coordinates: Any
        match self.kind:
            case GeometryKind.POINT:
                coordinates = list(self.positions[0])
            case GeometryKind.LINE:
                coordinates = [list(position) for position in self.positions]
            case GeometryKind.POLYGON:
                coordinates = [[list(position) for position in self.positions]]
        return {"type": self.kind.value, "coordinates": coordinates}

    def segments(self) -> list[tuple[Position, Position]]:
        return list(zip(self.positions, self.positions[1:], strict=False))


def _position(value: Sequence[Any]) -> Position:
    if len(value) != 2:
        raise ValueError("a position is a longitude and a latitude")
    longitude, latitude = value
    if isinstance(longitude, bool) or isinstance(latitude, bool):
        raise ValueError("not a number")
    return float(longitude), float(latitude)


def _orientation(a: Position, b: Position, c: Position) -> float:
    """Positive when a, b, c turn counter-clockwise, negative when clockwise, 0 if collinear."""
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _on_segment(a: Position, b: Position, point: Position) -> bool:
    """Whether a point collinear with a-b lies on the segment."""
    return min(a[0], b[0]) <= point[0] <= max(a[0], b[0]) and min(a[1], b[1]) <= point[1] <= max(
        a[1], b[1]
    )


def _intersect(p1: Position, p2: Position, q1: Position, q2: Position) -> bool:
    """Whether two closed segments share any point."""
    d1, d2 = _orientation(q1, q2, p1), _orientation(q1, q2, p2)
    d3, d4 = _orientation(p1, p2, q1), _orientation(p1, p2, q2)
    if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and (
        (d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)
    ):
        return True
    return (
        (d1 == 0 and _on_segment(q1, q2, p1))
        or (d2 == 0 and _on_segment(q1, q2, p2))
        or (d3 == 0 and _on_segment(p1, p2, q1))
        or (d4 == 0 and _on_segment(p1, p2, q2))
    )


def _cross(p1: Position, p2: Position, q1: Position, q2: Position) -> bool:
    """Whether two segments cross each other at a point inside both."""
    d1, d2 = _orientation(q1, q2, p1), _orientation(q1, q2, p2)
    d3, d4 = _orientation(p1, p2, q1), _orientation(p1, p2, q2)
    return d1 * d2 < 0 and d3 * d4 < 0


def _ring_area(ring: Sequence[Position]) -> float:
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in itertools.pairwise(ring)) / 2


def _is_simple_ring(ring: Sequence[Position]) -> bool:
    """Whether a closed ring touches itself only where consecutive edges meet."""
    # Repeated consecutive positions are harmless; drop them before comparing edges.
    points = [ring[0]]
    for position in ring[1:]:
        if position != points[-1]:
            points.append(position)
    edges = list(itertools.pairwise(points))
    count = len(edges)
    for i in range(count):
        for j in range(i + 1, count):
            adjacent = j == i + 1 or (i == 0 and j == count - 1)
            if not adjacent:
                if _intersect(*edges[i], *edges[j]):
                    return False
                continue
            # Adjacent edges share one vertex; they may not fold back over each other.
            (a, b), (c, d) = edges[i], edges[j]
            shared, first, second = (b, a, d) if b == c else (a, b, c)
            if _orientation(shared, first, second) == 0 and (
                (first[0] - shared[0]) * (second[0] - shared[0])
                + (first[1] - shared[1]) * (second[1] - shared[1])
                > 0
            ):
                return False
    return True


def _inside_ring(point: Position, ring: Sequence[Position]) -> bool | None:
    """Whether a point is inside a closed ring; `None` when it lies on the ring."""
    inside = False
    x, y = point
    for a, b in itertools.pairwise(ring):
        if _orientation(a, b, point) == 0 and _on_segment(a, b, point):
            return None
        if (a[1] > y) != (b[1] > y):
            crossing = a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
            if x < crossing:
                inside = not inside
    return inside


@dataclass(frozen=True)
class Boundary:
    """The Instance boundary: one or more polygons, each an outer ring and its holes."""

    polygons: tuple[tuple[tuple[Position, ...], ...], ...]

    @classmethod
    def from_geojson(cls, geojson: Mapping[str, Any]) -> Boundary:
        """From the configuration's validated Polygon or MultiPolygon geometry."""
        polygons = (
            [geojson["coordinates"]]
            if geojson["type"] == "Polygon"
            else list(geojson["coordinates"])
        )
        return cls(
            tuple(
                tuple(tuple(_position(position) for position in ring) for ring in polygon)
                for polygon in polygons
            )
        )

    def _rings(self) -> list[tuple[Position, ...]]:
        return [ring for polygon in self.polygons for ring in polygon]

    def covers_point(self, point: Position) -> bool:
        """Whether the point is inside the boundary or on its edge."""
        for outer, *holes in self.polygons:
            inside = _inside_ring(point, outer)
            if inside is None:
                return True
            if inside:
                return all(_inside_ring(point, hole) is not True for hole in holes)
        return False

    def covers(self, geometry: Geometry) -> bool:
        """Whether the whole geometry lies inside the boundary (its edge included)."""
        if not all(self.covers_point(position) for position in geometry.positions):
            return False
        edges = [edge for ring in self._rings() for edge in itertools.pairwise(ring)]
        for segment in geometry.segments():
            if any(_cross(*segment, *edge) for edge in edges):
                return False
            # A segment between two covered vertices may still leave through a hole
            # or a gap that it only touches at vertices: its midpoint tells.
            midpoint = (
                (segment[0][0] + segment[1][0]) / 2,
                (segment[0][1] + segment[1][1]) / 2,
            )
            if not self.covers_point(midpoint):
                return False
        if geometry.kind is GeometryKind.POLYGON:
            # A hole of the boundary may sit entirely inside the polygon.
            for _, *holes in self.polygons:
                for hole in holes:
                    if _inside_ring(hole[0], geometry.positions):
                        return False
        return True
