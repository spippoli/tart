# Rome's boundary

`boundary.geojson` is the outer perimeter of Roma Capitale with Vatican City included
(its hole filled), simplified to about 20 m without leaving any part of the municipal
area outside. It is a MultiPolygon: the municipality has a small exclave to the north.

**Source and licence**: © OpenStreetMap contributors, from the administrative
boundary relations of Roma Capitale (`ref:ISTAT=058091`) and Vatican City. It is a
Derivative Database of OpenStreetMap and stays under the
[Open Database License 1.0](https://opendatacommons.org/licenses/odbl/1-0/)
([ADR 0016](../../../docs/adr/0016-licence-policy-for-map-assets-and-data.md)). The
GeoJSON's properties repeat the source, the relations, the OpenStreetMap timestamp,
and the method.

**Recreate it** (the ODbL "method to recreate"), in this directory:

```sh
uv run boundary.py                  # queries the Overpass API with boundary.overpassql
uv run boundary.py overpass.json    # or rebuilds from a saved Overpass answer
```

`boundary.overpassql` selects the two relations with their member ways' geometry;
`boundary.py` assembles them, keeps the outer perimeter, buffers it outward by the
smallest step (5 to 30 m) that keeps the whole municipal area inside after a 20 m
simplification, and checks that before writing. Commit the result after a review of
the change.
