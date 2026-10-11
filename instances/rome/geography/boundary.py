# /// script
# requires-python = ">=3.14"
# dependencies = ["shapely==2.1.2"]
# ///
"""Rebuild boundary.geojson from OpenStreetMap: `uv run boundary.py [overpass.json]`.

Runs boundary.overpassql against the Overpass API, assembles Roma Capitale and
Vatican City from their member ways, and keeps the outer perimeter of the two
together (Vatican City's hole filled). The perimeter is then simplified to about
20 m, after a small outward buffer, so that no part of the municipal area falls
outside it; the script checks that before writing. The output is a Derivative
Database of OpenStreetMap, under the ODbL (see README.md).
"""

import json
import math
import sys
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from shapely import Polygon, ops, polygonize, unary_union
from shapely.geometry import LineString, MultiPolygon, mapping, shape

HERE = Path(__file__).parent
OVERPASS = "https://overpass-api.de/api/interpreter"
TOLERANCE_M = 20.0
BUFFERS_M = (5.0, 10.0, 15.0, 20.0, 25.0, 30.0)

# A local equirectangular projection in metres: accurate enough over one city.
LATITUDE_0 = math.radians(41.9)
METRES_PER_DEGREE = 111_320.0


def to_metres(lon: float, lat: float) -> tuple[float, float]:
    return lon * METRES_PER_DEGREE * math.cos(LATITUDE_0), lat * METRES_PER_DEGREE


def to_degrees(x: float, y: float) -> tuple[float, float]:
    return x / (METRES_PER_DEGREE * math.cos(LATITUDE_0)), y / METRES_PER_DEGREE


def fetch(query: str) -> dict:
    body = urllib.parse.urlencode({"data": query}).encode()
    request = urllib.request.Request(OVERPASS, body, {"User-Agent": "tart-rome-boundary"})
    with urllib.request.urlopen(request, timeout=300) as response:
        return json.load(response)


def area_of(relation: dict) -> Polygon | MultiPolygon:
    """Every face the relation's ways enclose, holes filled."""
    lines = [
        LineString([to_metres(point["lon"], point["lat"]) for point in member["geometry"]])
        for member in relation["members"]
        if member["type"] == "way" and member.get("geometry")
    ]
    faces = polygonize([unary_union(lines)])
    return unary_union(list(faces.geoms))


def outer_perimeter(geometry: Polygon | MultiPolygon) -> Polygon | MultiPolygon:
    polygons = geometry.geoms if isinstance(geometry, MultiPolygon) else [geometry]
    shells = [Polygon(polygon.exterior) for polygon in polygons]
    return unary_union(shells) if len(shells) > 1 else shells[0]


def rounded(geometry: Polygon | MultiPolygon) -> dict:
    """GeoJSON in degrees, 6 decimals (about 0.1 m)."""
    projected = ops.transform(lambda x, y: to_degrees(x, y), geometry)
    return json.loads(json.dumps(mapping(projected)), parse_float=lambda v: round(float(v), 6))


def main() -> int:
    if len(sys.argv) > 1:  # a saved Overpass answer, to rebuild without querying again
        data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    else:
        data = fetch((HERE / "boundary.overpassql").read_text(encoding="utf-8"))
    relations = [element for element in data["elements"] if element["type"] == "relation"]
    if len(relations) != 2:
        print(f"expected Roma Capitale and Vatican City, got {len(relations)} relations")
        return 1
    municipal = unary_union([area_of(relation) for relation in relations])
    perimeter = outer_perimeter(municipal)

    for buffer in BUFFERS_M:
        simplified = outer_perimeter(
            perimeter.buffer(buffer, join_style="mitre").simplify(TOLERANCE_M)
        )
        geometry = rounded(simplified)
        check = ops.transform(lambda x, y: to_metres(x, y), shape(geometry))
        if check.contains(perimeter):
            break
    else:
        print("no buffer keeps the whole municipal area inside the simplified perimeter")
        return 1

    feature = {
        "type": "Feature",
        "properties": {
            "name": "Roma Capitale, Vatican City included",
            "source": "OpenStreetMap, relations "
            + ", ".join(str(relation["id"]) for relation in relations),
            "osm_base": data["osm3s"]["timestamp_osm_base"],
            "built": datetime.now(UTC).strftime("%Y-%m-%d"),
            "method": f"outer perimeter, {buffer:g} m outward buffer, "
            f"{TOLERANCE_M:g} m simplification; see boundary.py",
            "license": "ODbL-1.0",
            "attribution": "© OpenStreetMap contributors",
        },
        "geometry": geometry,
    }
    (HERE / "boundary.geojson").write_text(json.dumps(feature) + "\n", encoding="utf-8")
    print(f"boundary.geojson written: {buffer:g} m buffer, {count(geometry)} positions")
    return 0


def count(geometry: dict) -> int:
    rings = (
        geometry["coordinates"]
        if geometry["type"] == "Polygon"
        else [ring for polygon in geometry["coordinates"] for ring in polygon]
    )
    return sum(len(ring) for ring in rings)


if __name__ == "__main__":
    sys.exit(main())
