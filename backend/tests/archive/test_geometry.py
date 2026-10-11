"""Location geometries: their shape and the Instance boundary (archive-records spec, Location)."""

import pytest

from tart.archive import ArchiveRuleViolation, Boundary, Geometry, GeometryKind

# A fictional boundary: a 10 x 10 square with a 2 x 2 hole in its middle.
WITH_HOLE = Boundary.from_geojson(
    {
        "type": "Polygon",
        "coordinates": [
            [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]],
            [[4, 4], [6, 4], [6, 6], [4, 6], [4, 4]],
        ],
    }
)
# Two separate squares.
TWO_PARTS = Boundary.from_geojson(
    {
        "type": "MultiPolygon",
        "coordinates": [
            [[[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]]],
            [[[3, 0], [5, 0], [5, 2], [3, 2], [3, 0]]],
        ],
    }
)


def _polygon(*positions: tuple[float, float]) -> Geometry:
    return Geometry(GeometryKind.POLYGON, (*positions, positions[0]))


def _line(*positions: tuple[float, float]) -> Geometry:
    return Geometry(GeometryKind.LINE, positions)


def _point(x: float, y: float) -> Geometry:
    return Geometry(GeometryKind.POINT, ((x, y),))


def test_criterion_10_a_self_intersecting_polygon_is_rejected() -> None:
    with pytest.raises(ArchiveRuleViolation) as raised:
        _polygon((0, 0), (2, 2), (2, 0), (0, 2))  # a bow tie

    assert raised.value.code == "geometry.self_intersecting"


@pytest.mark.parametrize(
    "positions",
    [
        ((0, 0), (4, 0), (4, 4), (2, 0), (0, 4)),  # a vertex touching an edge
        ((0, 0), (4, 0), (4, 4), (4, 2), (4, 0.5)),  # an edge folding back on the previous one
    ],
)
def test_criterion_10_a_polygon_touching_itself_is_rejected(
    positions: tuple[tuple[float, float], ...],
) -> None:
    with pytest.raises(ArchiveRuleViolation) as raised:
        _polygon(*positions)

    assert raised.value.code == "geometry.self_intersecting"


def test_a_simple_polygon_is_accepted_in_either_direction() -> None:
    concave = ((0, 0), (4, 0), (4, 4), (2, 1), (0, 4))

    _polygon(*concave)
    _polygon(*reversed(concave))


def test_a_polygon_with_holes_is_refused() -> None:
    with pytest.raises(ArchiveRuleViolation) as raised:
        Geometry.from_geojson(
            {
                "type": "Polygon",
                "coordinates": [
                    [[0, 0], [4, 0], [4, 4], [0, 4], [0, 0]],
                    [[1, 1], [2, 1], [2, 2], [1, 1]],
                ],
            }
        )

    assert raised.value.code == "geometry.polygon_with_holes"


@pytest.mark.parametrize(
    "geojson",
    [
        {"type": "MultiPoint", "coordinates": [[1, 1]]},
        {"type": "Point", "coordinates": [200, 1]},
        {"type": "Point", "coordinates": [1]},
        {"type": "LineString", "coordinates": [[1, 1], [1, 1]]},
        {"type": "Polygon", "coordinates": [[[0, 0], [1, 1], [2, 2], [0, 0]]]},
        {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1]]]},
    ],
)
def test_malformed_geometries_are_refused(geojson: dict[str, object]) -> None:
    with pytest.raises(ArchiveRuleViolation):
        Geometry.from_geojson(geojson)


def test_geojson_round_trips() -> None:
    for geometry in (_point(1, 2), _line((0, 0), (1, 1)), _polygon((0, 0), (1, 0), (1, 1))):
        assert Geometry.from_geojson(geometry.to_geojson()) == geometry


@pytest.mark.parametrize(
    "geometry",
    [
        _point(1, 1),
        _point(0, 5),  # on the edge
        _line((1, 1), (9, 1)),
        _polygon((1, 1), (3, 1), (3, 3), (1, 3)),
    ],
)
def test_criterion_10_geometries_inside_the_boundary_are_accepted(geometry: Geometry) -> None:
    assert WITH_HOLE.covers(geometry)


@pytest.mark.parametrize(
    "geometry",
    [
        _point(11, 1),
        _point(5, 5),  # in the hole
        _line((1, 1), (12, 1)),  # leaves through the outer edge
        _line((1, 5), (9, 5)),  # crosses the hole
        _line((4, 4), (6, 6)),  # runs inside the hole between two of its corners
        _polygon((1, 1), (9, 1), (9, 9), (1, 9)),  # surrounds the hole
        _polygon((8, 8), (12, 8), (12, 9)),
    ],
)
def test_criterion_10_geometries_outside_the_boundary_are_rejected(geometry: Geometry) -> None:
    assert not WITH_HOLE.covers(geometry)


def test_a_multipolygon_boundary_covers_each_part_but_not_the_gap() -> None:
    assert TWO_PARTS.covers(_point(1, 1))
    assert TWO_PARTS.covers(_point(4, 1))
    assert not TWO_PARTS.covers(_point(2.5, 1))
    assert not TWO_PARTS.covers(_line((1, 1), (4, 1)))
