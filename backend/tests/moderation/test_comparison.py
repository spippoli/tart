"""Contribution and moderation spec, Submission page, criterion 52: the text summary of a
geometry comparison, which is all there is without WebGL2. Every geometry is fictional."""

import pytest
from archive_fixtures import IN_ROME, point, square

from tart.archive import Geometry, GeometryKind
from tart.moderation import summarise

LONGITUDE, LATITUDE = IN_ROME
DEGREE = 111_320


def moved(east: float = 0, north: float = 0) -> Geometry:
    return point(LONGITUDE + east / (DEGREE * 0.745), LATITUDE + north / DEGREE)


def test_a_new_geometry_has_only_its_vertex_count() -> None:
    summary = summarise(None, square(12.48, 41.89, 12.49, 41.90))

    assert (summary.vertices_before, summary.vertices_after) == (None, 4)
    assert summary.largest_shift_metres is None and summary.shift_direction is None
    assert summary.area_change_square_metres is None


@pytest.mark.parametrize(
    ("east", "north", "direction"),
    [(0, 50, "N"), (50, 0, "E"), (0, -50, "S"), (-50, 0, "W"), (36, 36, "NE"), (-36, -36, "SW")],
)
def test_a_moved_point_says_how_far_and_towards_where(
    east: float, north: float, direction: str
) -> None:
    summary = summarise(moved(), moved(east, north))

    assert summary.largest_shift_metres == pytest.approx(50, abs=1.5)
    assert summary.shift_direction == direction


def test_a_point_that_did_not_move_has_no_direction() -> None:
    summary = summarise(moved(), moved())

    assert summary.largest_shift_metres == 0
    assert summary.shift_direction is None


def test_the_largest_shift_is_that_of_the_vertex_that_moved_most() -> None:
    before = Geometry(GeometryKind.LINE, ((12.48, 41.89), (12.481, 41.89), (12.482, 41.89)))
    after = Geometry(GeometryKind.LINE, ((12.48, 41.89), (12.481, 41.8902), (12.482, 41.89)))

    summary = summarise(before, after)

    assert summary.largest_shift_metres == pytest.approx(22, abs=1)
    assert summary.shift_direction == "N"
    assert (summary.vertices_before, summary.vertices_after) == (3, 3)


def test_a_vertex_added_to_a_polygon_is_counted_and_measured_from_the_nearest_one() -> None:
    before = square(12.480, 41.893, 12.484, 41.897)
    after = Geometry(
        GeometryKind.POLYGON,
        (
            (12.480, 41.893),
            (12.484, 41.893),
            (12.486, 41.895),
            (12.484, 41.897),
            (12.480, 41.897),
            (12.480, 41.893),
        ),
    )

    summary = summarise(before, after)

    assert (summary.vertices_before, summary.vertices_after) == (4, 5)
    assert summary.largest_shift_metres is not None and summary.largest_shift_metres > 100
    assert summary.area_change_square_metres is not None
    assert summary.area_change_square_metres > 0


def test_a_smaller_polygon_has_a_negative_change_of_surface() -> None:
    summary = summarise(
        square(12.480, 41.893, 12.490, 41.897), square(12.480, 41.893, 12.484, 41.897)
    )

    assert summary.area_change_square_metres == pytest.approx(-221_000, rel=0.05)
