# Rome's map style

The reference style of [ADR 0017](../../../docs/adr/0017-map-cartography-style.md):
the tinted early-1900s plan, as two finished MapLibre styles, `style.light.json` and
`style.dark.json`, the dark one an ink negative of the same tokens
([Discovery spec, Map style ownership and serving](../../../docs/spec/discovery.md#map-style-ownership-and-serving)).
Validate the directory with `tart config check`; the platform's CI also runs
`gl-style-validate` on both files (`pnpm check:styles` in `frontend/`).

## The styles

- **Tokens**: `metadata.tart:tokens` holds every ADR 0017 token for its theme. The
  archive layers read `map.paper`, `map.ink`, `marker.ink`, and `map.label.district`;
  the others document the colours used in the layers. The accent comes from
  `instance.toml`. After changing a token, run `tart config check`: it re-checks every
  fill and label contrast.
- **Layers**, from the bottom: paper, parks, water ruled with thin lines inside its
  banks, buildings in one block tint with a key-plate outline, the ruins overlay,
  streets with continuous casings, rail (service and yard tracks only from z15), bridges,
  the city walls, then the labels. Tunnels, boundaries, points of interest, shields, and
  place names are not drawn; district names come from the archive's Areas, and the
  city's name is not on the map. No line is dashed or dotted: those are TART's signs.
- **Archive layers** go below `water-labels`, the first label layer.
- **Basemap**: the local Protomaps extract (`metadata.tart:basemap-schema` 4). Labels
  use the local OpenStreetMap names (`name`). The street and water geometry filters
  and widths come from the layers of [`@protomaps/basemaps`](https://github.com/protomaps/basemaps)
  5.7.2 (© Protomaps LLC, BSD-3-Clause). After a schema major change, rebuild the
  layers against the new schema and bump the key.

## Fonts and glyphs

- `fonts/`: Sorts Mill Goudy by Barry Schwartz, Regular and Italic, served through the
  style's `font-faces`; `fonts/OFL.txt` is its licence (SIL Open Font License 1.1, no
  Reserved Font Name).
- `fonts/SortsMillGoudy-SmallCaps.ttf`, for the archive's Site labels, is derived from
  the Regular: MapLibre applies no OpenType feature, so a copy of the font maps each
  lowercase letter to its small-cap glyph. Rebuild it in this directory with
  `uv run small_caps.py`.
- `glyphs/Noto Sans Regular/`: the Noto Sans glyphs for cluster counts and as the
  fallback, from [Protomaps' basemaps-assets](https://github.com/protomaps/basemaps-assets);
  `glyphs/OFL.txt` is its licence.

## The overlay

`overlay.geojson` holds the city walls (`barrier=city_wall` or `historic=citywalls`)
and the archaeological sites and ruins (`historic=archaeological_site` or `ruins`)
drawn as lines or areas within Roma Capitale and Vatican City. Each feature keeps its
`kind` (`wall` or `ruin`), its `name` when it has one, and its OpenStreetMap `id`.

**Source and licence**: © OpenStreetMap contributors. It is a Derivative Database of
OpenStreetMap and stays under the
[Open Database License 1.0](https://opendatacommons.org/licenses/odbl/1-0/)
([ADR 0016](../../../docs/adr/0016-licence-policy-for-map-assets-and-data.md)). It is
drawn by the style only and never flows into archive data.

**Recreate it** (the ODbL "method to recreate"), in this directory, with the Overpass
API, [osmtogeojson](https://github.com/tyrasd/osmtogeojson) (MIT), and `jq`:

```sh
curl -sS -A tart-rome-overlay --data-urlencode data@overlay.overpassql \
  https://overpass-api.de/api/interpreter > overpass.json
npx osmtogeojson@3.0.0-beta.5 overpass.json | jq -c -f overlay.jq > overlay.geojson
rm overpass.json
```

`overlay.overpassql` selects the features; `overlay.jq` keeps the properties the style
reads. The result must stay under 1 MB. Commit it after a review of the change.
