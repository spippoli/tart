# Research: MapLibre style and PMTiles basemap for TART's map cartography

Date: 2026-10-10. Status: research, not a decision.

Reader: the agent that will define TART's map cartography style. Inputs: ADR 0004 (plain MapLibre GL JS + `pmtiles` protocol in one map module, Caddy serves PMTiles same-origin with byte ranges), ADR 0009 (an Instance's configuration directory holds "a MapLibre style file … that references tiles by URL, plus attribution text that may not be empty"; the PMTiles file lives in a data volume), ADR 0015 (historical-map symbology: solid, dashed, and dotted squares for Condition groups; hatched area for approximate Location; color is redundant), README §13 (editorial, archival, restrained), §14 (i18n), §15 (map is core, dense clusters, disappeared artworks).

Versions checked on 2026-10-10: `maplibre-gl` 6.13.0, `@maplibre/maplibre-gl-style-spec` 26.4.4, `pmtiles` (JS) 4.5.0, go-pmtiles CLI 1.31.2, `@protomaps/basemaps` 5.7.2, Protomaps daily build `20261009` (tileset version 4.15.2).

## Summary

- **MapLibre GL JS is at 6.13.0** (BSD-3-Clause). v6.0.0 (about 2026-07-22) removed WebGL1 ("WebGL2 is now required") and ships ESM-only. Since 6.7.0 the `Map` constructor throws `GPUInitializationError` when no WebGL2 context can be created, so the map module must catch it and fall back to the list view. [changelog][gljs-changelog], [releases][gljs-releases], [package.json][gljs-pkg]
- **Style documents are spec version 8** with root keys including `sources`, `layers`, `glyphs`, `sprite` (string or array of `{id,url}`), `projection`, `light`, `terrain`, `sky`, `font-faces`, `transition`, and `state`. `state` holds defaults for the `global-state` expression, which is useful for per-viewer toggles without rebuilding the style. [root][spec-root]
- **There is no blend-mode property** (no multiply). v6.0.0 added `fill-layer-opacity` and `line-layer-opacity`, which composite a whole layer once so that overlaps don't darken. These are the closest tool to "ink on paper" layering. [layers][spec-layers]
- **Protomaps basemap (schema v4) is the best fit.** It is ODbL data with a CC0 map design, BSD-3 code, and a Noto Sans OFL font set. It has `name:it`/`name:en` (41 languages), buildings from z11 (merged below z15, individual at z15), and address points (`kind=address`, `addr_housenumber`) at z15. Max zoom is 15 and MapLibre overzooms beyond that. [layers doc][pm-layers], [Buildings.java][pm-buildings], [repo][pm-repo]
- **Measured:** a dry-run `pmtiles extract` of the 20261009 planet build (138.7 GB) with Rome bbox `12.23,41.65,12.86,42.08` produced **47 MB at z0–15** (4,081 tiles, 59 HTTP requests). This fits easily on the VPS and is cheap to refresh.
- **`@protomaps/basemaps` 5.7.2** exports `layers(source, flavor, {lang?, labelsOnly?})` and `namedFlavor('light'|'dark'|'white'|'grayscale'|'black')`. A Flavor is a flat object of 74 color keys plus optional `regular`/`bold`/`italic` font names, `landcover`, and `pois`. With `lang:'it'` it generates **71 layers** (1 background, 15 fill, 41 line, 14 symbol), and labels use `coalesce(name:it, …, name)`. [index.ts][pm-index], [typedoc][pm-flavor], measured locally.
- **OpenMapTiles** requires a visible "© OpenMapTiles" credit (CC-BY 4.0 design/schema). **Shortbread** (CC0) has max zoom 14, buildings from z14, and in 1.0 only `name`, `name_en`, `name_de` (no Italian; 1.1 adds `name_xx`). Both are weaker fits than Protomaps for TART. [OMT licence][omt-license], [Shortbread 1.0][shortbread]
- **Glyphs** are SDF PBFs in 256-codepoint ranges, generated with `maplibre/font-maker` (BSD-3). `text-font` names must equal the fontstack folder names. **`font-faces`** (TTF/OTF/WOFF via the CSS Font Loading API) is implemented in GL JS since 6.7.0, but the spec's SDK table still marks GL JS unsupported. Treat this as a conflict to verify. [changelog][gljs-changelog], [spec font-faces][spec-fontfaces], [map.ts source][gljs-mapts]
- **Sprites** are a JSON + PNG pair with `@2x`, built by `spreet` (MIT; supports `--sdf`, `--retina`). SDF icons can be recolored with `icon-color`. Patterns (`fill-pattern`, `line-pattern`, `background-pattern`) come from the sprite. These carry the hatching, paper texture, and ADR 0015's hatched approximate area. [sprite][spec-sprite], [spreet][spreet]
- **Accessibility:** the canvas gets `role="region"` and `aria-label` from the UI-string table (localizable via the `locale` option), and it has keyboard handlers. The `reduceMotion` option follows the OS setting by default. Basemap labels should meet 4.5:1 and essential markers 3:1 (WCAG 1.4.3 / 1.4.11). Pan and zoom need non-drag alternatives (2.5.7). [map.ts][gljs-mapts], [MapOptions][gljs-mapoptions], [1.4.11][wcag-1411]

## 1. Style document anatomy

The root properties are defined in the spec [root page][spec-root] and the machine-readable [v8.json][spec-v8].

| Key | Notes for TART |
|---|---|
| `version` | Must be `8`. |
| `name`, `metadata` | `metadata` is free-form and ignored by the renderer. Use it for the theme id and the generator version. |
| `center`, `zoom`, `bearing`, `pitch`, `roll`, `centerAltitude` | Defaults only. TART takes its default view from Instance config (ADR 0009), so the map module should set the camera explicitly. |
| `sources` | Required. Vector source keys include `url` (TileJSON or `pmtiles://…`), `tiles`, `bounds`, `minzoom`, `maxzoom` (default 22), `attribution`, `promoteId`, and `encoding` (`mvt` default; `mlt` since GL JS 5.12.0). [sources][spec-sources] |
| `layers` | Required, drawn in order (first = bottom). |
| `glyphs` | URL template with `{fontstack}` and `{range}`. The spec says it "must be absolute". [glyphs][spec-glyphs] |
| `sprite` | Either a string base URL (the renderer appends `.json`/`.png` and `@2x`) or an array `[{id, url}]`. Images in a non-`default` sprite are referenced as `id:image`. [sprite][spec-sprite] |
| `font-faces` | Font files per `text-font` name with an optional `unicode-range`. Characters not covered fall back to `glyphs`. See §6. |
| `projection` | `{type: …}`. The default is `mercator`. It accepts a zoom-interpolated expression, for example vertical-perspective/globe at low zoom. TART needs `mercator` only. [root][spec-root] |
| `light`, `sky`, `terrain` | 3D extrusion lighting, sky (experimental), and DEM terrain. These are not useful for a flat archival map. |
| `transition` | Global `{duration, delay}` for paint transitions. Set it to 0 under reduced motion if desired. |
| `state` | Default values for `["global-state", "key"]`. The value is set at runtime with `map.setGlobalStateProperty(key, value)`; `null` resets it to the default. Supported in GL JS ≥ 5.6.0. [expressions][spec-expr], [Map API][gljs-map] |

Layer types in the current spec: `background`, `fill`, `line`, `symbol`, `circle`, `heatmap`, `fill-extrusion`, `raster`, `hillshade`, and **`color-relief`** (DEM-driven color ramp; GL JS 5.6.0). [spec-v8], [layers][spec-layers]

Layer-level keys:
- `id` and `type`.
- `source`, required except for `background`.
- `source-layer`, required for vector sources and prohibited for GeoJSON.
- `filter`, an expression. Its zoom-dependent parts are evaluated at integer zooms only, and `feature-state` is not allowed in it.
- `minzoom`/`maxzoom` in the range 0–24.
- `layout`, which is evaluated at tile build time on worker threads. Camera expressions in `layout` are evaluated "only at integer zoom levels".
- `paint`, which is evaluated per frame and is the only place `feature-state` works.
- `layout.visibility` (`visible`|`none`). [layers][spec-layers], [expressions][spec-expr]

Rule of thumb for the style agent: anything you want to change at runtime cheaply (colors, opacities, highlight) belongs in `paint`. Text content, fonts, placement, and sizes that affect collision belong in `layout`, and changing them re-lays out tiles.

## 2. Expressions

Operators are listed on the [expressions page][spec-expr].

- **Zoom-driven:** `["interpolate", ["exponential", 1.6], ["zoom"], 11, 0.5, 15, 2, 18, 11]` or `["step", ["zoom"], a, 14, b]`. `["zoom"]` may appear only as the input to a top-level `interpolate`/`step`. Paint expressions re-evaluate at fractional zoom; layout expressions do not. Protomaps uses exponential base 1.6 for road widths, for example `roads_minor` `line-width` stops `11→0, 12.5→0.5, 15→2, 18→11`. [measured from @protomaps/basemaps 5.7.2]
- **Data-driven:** `["get","kind"]`, `["match", ["get","kind"], ["park","cemetery"], c1, c2]`, `["case", cond, a, …, fallback]`, `["coalesce", a, b, …]` (first non-null), `["has", "k"]`, and `["in", …]`. `match` labels must be literals.
- **Color interpolation:** `interpolate-hcl` and `interpolate-lab` exist in GL JS (not native). `to-color`, `rgb`, and `rgba` are also available.
- **Feature state:** `["feature-state","selected"]` works in data-driven **paint** properties only. It needs feature ids (`promoteId` on the source, or `generateId` for GeoJSON). Use it for the selected and focused artwork marker state.
- **Global state:** `["global-state","showDisappeared"]` works in filters, paint, and layout, and since 6.1 also in `sky.*`, `light.*`, and `projection.type`. It is a cleaner way to toggle "show disappeared artworks" than swapping filters in code. [changelog][gljs-changelog]
- **Text:** `format` (mixed fonts/scales in one label), `concat`, `upcase`, `number-format`, `is-supported-script`, `resolved-locale`, and `collator`.
- **Label language fallback (recommended minimal form for Latin-script cities):**
  ```json
  "text-field": ["coalesce", ["get", "name:it"], ["get", "name"]]
  ```
  For an English UI: `["coalesce", ["get","name:en"], ["get","name"]]`. Protomaps' own generator emits a large `case` that also handles `script`, `name2`/`name3`, and `pgf:name` (Devanagari), falling back to `name:en` only when the local script is not renderable. [localization][pm-l10n], [language.ts][pm-language]. For Rome (Latin script) the simple `coalesce` is equivalent in practice. Note that OSM `name` in Rome is Italian, so `name:it` adds little for an `it` UI but matters for `en` (`Rome`, `Colosseum`). This is unverified per feature and depends on OSM tagging.
- **Font fallback stacks:** `"text-font": ["Noto Sans Regular"]`. An array is a fontstack, and with `glyphs` the names are comma-joined into one `{fontstack}` request (for example `Font A,Font B/0-255.pbf`). The server or the static directory must hold exactly that combined name. Static hosting therefore needs single-name stacks, or pre-combined folders. [glyphs][spec-glyphs]
- **Dash arrays:** `line-dasharray` must be a literal array (`["literal",[2,1]]`) and cannot come from feature properties. Its lengths are multiples of line width, and zoom expressions on it are evaluated at integer zooms. [layers][spec-layers]
- **Legacy filter syntax** (`["in","kind","building","building_part"]`, `["!has","is_tunnel"]`) is still accepted, and Protomaps 5.7.2 still emits it for some layers (measured). New code should use expression syntax.

## 3. Wiring PMTiles

- **JS:** `pmtiles` 4.5.0 (BSD-3-Clause, single dependency `fflate`). [pkg][pmtiles-pkg]
  ```ts
  import maplibregl from "maplibre-gl";
  import { Protocol } from "pmtiles";
  const protocol = new Protocol(); // options: { metadata?: boolean; errorOnMissingTile?: boolean }
  maplibregl.addProtocol("pmtiles", protocol.tile); // once per app lifetime
  // source: { type: "vector", url: "pmtiles://https://<host>/tiles/rome.pmtiles", attribution: "…" }
  ```
  Register the protocol only once. [Protomaps MapLibre guide][pm-maplibre-pmtiles]. `Protocol.add(PMTiles)` shares an instance. `metadata: true` loads the metadata section, which "inspect" tooling needs. With `errorOnMissingTile`, a missing tile raises an error instead of returning an empty tile. [adapters.ts][pmtiles-adapters]. The protocol derives `minzoom`/`maxzoom` from the archive header.
- **Single file.** An archive is one file with a header, directories, and gzip-compressed tiles. The archive header of the planet build shows `tile compression: gzip`, `clustered: true`, `max zoom: 15` (measured with `pmtiles show`). The JS library decompresses tiles itself, so **the file must be served byte-for-byte**: no `Content-Encoding`, and no on-the-fly `encode` in Caddy for the `.pmtiles` path. Caddy's `encode` "may compress the response on-the-fly" [Caddy file_server][caddy-fs]. Whether its default MIME matcher skips `application/octet-stream` is unverified, so exclude the path explicitly.
- **Caddy range requests.** Caddy's `file_server` delegates to Go's `http.ServeContent` and documents support for `Range`, `If-Range`, and the conditional headers, plus Etag and Last-Modified. [staticfiles.go][caddy-src]. Same-origin serving needs no CORS. If tiles are ever cross-origin, allow headers `range,if-match`, expose `ETag`, and answer `OPTIONS` preflights. [cloud storage][pm-cloud]. The `pmtiles_proxy` Caddy plugin exists (it serves `/z/x/y` + TileJSON from buckets), but a plain `file_server` is enough for the `pmtiles://` client protocol. [deploy/server][pm-server]
- **Extracting Rome.** Install go-pmtiles CLI v1.31.2 (released 2026-07-22), then:
  ```sh
  pmtiles extract https://build.protomaps.com/20261009.pmtiles rome.pmtiles \
    --bbox=12.23,41.65,12.86,42.08   # or --region=boundary.geojson (the Instance boundary, ADR 0009)
  ```
  Flags: `--maxzoom`, `--minzoom` (expensive), `--download-threads=4`, `--overfetch=0.05`, `--dry-run`. [CLI docs][pm-cli], CLI `--help`. **Measured dry-run (2026-10-10):** 4,081 tiles, 59 requests, 49 MB transferred, **47 MB archive**, 5 s. The bbox is approximate (Roma Capitale municipality) and was not checked against the official boundary. Using `--region` with the Instance's GeoJSON boundary is the natural per-Instance choice.
- **Builds and updates.** The planet file is about 120 GB per the docs and 138,736,840,194 bytes for the 20261009 build (HTTP `content-length`). Zooms are 0–15. Daily builds are kept for a week, plus the latest per patch version. The v4 channel works with `@protomaps/basemaps` ≥ 4.0.0. [downloads][pm-downloads]. The 20261009 build carries `version 4.15.2` and an OSM replication time of 2026-10-09T04:00Z. Updating means re-running `extract`, writing to a new filename (or atomically replacing the file), and restarting nothing. Cached clients compare ETag via `If-Match`, so swap atomically. The exact client behavior on an ETag mismatch is unverified.
- **Alternatives for building your own tiles:** planetiler (Apache-2.0; OpenMapTiles, Shortbread, and Protomaps profiles; `--output=*.pmtiles`) [planetiler][planetiler], and tippecanoe (BSD-2-Clause; `-o file.pmtiles`) for TART's *own* overlay data if ever needed [tippecanoe][tippecanoe]. TART's artwork points should come from the API as GeoJSON/clustered data, not baked into PMTiles. That follows from moderation: only approved data is public, and it changes continuously.

## 4. Tile schemas compared

| | Protomaps basemap v4 | OpenMapTiles | Shortbread 1.0 |
|---|---|---|---|
| Data licence | ODbL, attribute OSM [pm-repo] | ODbL (OSM) | ODbL (OSM) |
| Schema/design licence | Design CC0, code BSD-3 [pm-repo] | Design/schema **CC-BY 4.0**: must show "© OpenMapTiles" in map corner; code BSD-3 [omt-license] | Schema CC0 [shortbread-search] |
| Max zoom | 15 [pm-downloads] | 14 (housenumber "adds significant size to z14") [omt-schema] | 14 [shortbread] |
| Buildings | z11–15; merged with `mergeNearbyPolygons` below z15, heights quantized; individual at z15; `building_part` from z14 [pm-buildings] | `building` layer; start zoom not stated on schema page (commonly z13, **unverified**) [omt-schema] | 14+ [shortbread] |
| House numbers | `buildings` layer `kind=address`, `addr_housenumber`, z15 [pm-buildings] | `housenumber` layer, z14 [omt-schema] | `addresses` 14+ [shortbread] |
| Names | `name`, `name:<41 langs>` incl. `it`, `en`; `script`, `name2/3`, `pgf:name:*` [pm-l10n] | `name`, `name:xx`, `name_en`, `name_de`, `name_int`, `name:latin` [omt-schema] | `name`, `name_en`, `name_de` only (1.1 adds `name_xx`) [shortbread], [shortbread-1.1] |
| Hosted daily builds | yes (build.protomaps.com) | no free planet build in scope | OSMF serves Shortbread tiles on osm.org (not a downloadable PMTiles) [shortbread-1.1] |

Protomaps v4 layers [pm-layers]:

| Layer | Contents |
|---|---|
| `boundaries` | `kind`: country/region/county/locality, plus `kind_detail` = admin_level |
| `buildings` | `kind`: building/building_part/address, plus `height`, `min_height`, `layer` |
| `earth` | Natural Earth at low zoom, OSMCoastline z6+ |
| `landcover` | `kind`: barren/farmland/forest/glacier/grassland/scrub/urban_area; **z0–7 only** |
| `landuse` | `kind`: park, cemetery, residential, … |
| `places` | `kind`: country/region/locality/macrohood/neighbourhood, plus `kind_detail`, `population_rank` |
| `pois` | Ranked by Wikidata QRank |
| `roads` | `kind`: highway/major_road/minor_road/path/aerialway/ferry/pier/rail/aeroway, plus `kind_detail`, `is_tunnel`, `is_bridge`, `oneway`, `shield_text` |
| `transit` | Currently empty |
| `water` | `kind`: water/lake/playa/ocean/other, plus `kind_detail` (river, canal) |

Common fields on all layers: `sort_rank` and a suggested `min_zoom`.

Implication for a "historic map with building blocks" look: Protomaps gives merged block-like building masses from z11–14 (good for a figure-ground plan in the style of Nolli at city scale) and individual footprints at z15+. Overzoom past 15 keeps footprints sharp enough for street level, because vector geometry is simplified at z15 tile resolution (4096 units per tile; unverified for Protomaps specifically).

## 5. `@protomaps/basemaps` (style as code)

- Package `@protomaps/basemaps` 5.7.2 is BSD-3-Clause with no runtime dependencies. [pkg][pm-pkg]
- Exports: `layers`, `namedFlavor`, `get_multiline_name`, `get_country_name`, `language_script_pairs`, the constants `LIGHT`, `DARK`, `WHITE`, `GRAYSCALE`, `BLACK`, and the types `Flavor` and `Pois`. [index.ts][pm-index]
- Signatures: `layers(source: string, flavor: Flavor, options?: { labelsOnly?: boolean; lang?: string }): LayerSpecification[]`. Labels are appended only when `lang` is set. [index.ts][pm-index]
- `Flavor` [typedoc][pm-flavor] has 74 required string color keys:
  - background and land: `background`, `earth`
  - landuse: `park_a/b`, `wood_a/b`, `scrub_a/b`, `hospital`, `industrial`, `school`, `zoo`, `military`, `aerodrome`, `beach`, `sand`, `glacier`, `pedestrian`, `pier`, `runway`
  - water: `water`
  - buildings: `buildings`
  - roads: `highway`, `major`, `minor_a/b`, `minor_service`, `link`, `other`, `railway`, each with `*_casing` variants; `bridges_*` and `tunnels_*` variants
  - labels: `boundaries`, `city_label`, `state_label`, `subplace_label`, `country_label`, `ocean_label`, `roads_label_major/minor`, `address_label`, each with `*_halo` where applicable
  - optional: `regular`, `bold`, `italic` (font names), `landcover` (per-kind colors), `pois` (per-color-group).
- Custom flavor: `{...namedFlavor("light"), buildings: "#…", earth: "#…"}`. [flavors][pm-flavors]
- What the generator does **not** expose: line widths, dash patterns, patterns, letter-spacing, text-transform, and layer omission. For an engraved look you would post-process the returned `LayerSpecification[]` (map over layers by `id`, adjust `paint`/`layout`, insert pattern layers), or hand-write the layers. The IDs are stable strings such as `roads_minor`, `buildings`, and `places_locality`. Measured on 5.7.2, with no stability guarantee found.
- Sprites: each named flavor has a matching sprite (townspots, shields, POIs for light/dark). Custom-colored sprites are made with the repo's `spritegen` tool, or icons can be replaced by name, or `spreet` can be used. [flavors][pm-flavors]. basemaps-assets currently has `sprites/v3` and `sprites/v4` (`black`, `dark`, `grayscale`, `light`, `white`, each 1x/2x) (checked via GitHub API). The README says the sprites derive from MIT-licensed tangrams/icons. [assets][pm-assets]
- Measured output (`light`, `lang:'it'`): 71 layers. POI layer colors come from `flavor.pois` (blue, green, lapis, pink, red, slategray, tangerine, turquoise), which is too much color for TART. Drop or mute `pois`.
- **Hand-written JSON vs generator:** the generator gives correct schema coverage (filters for tunnels, bridges, and casings) for free, and upgrades follow the tileset version. A hand-written style gives full control but must track schema v4 changes. A hybrid works well: generate the base with `layers()`, then apply a TART transform (`(layers, theme) => layers`) and serialize to static JSON per Instance.

## 6. Fonts and glyphs

- **Format:** signed-distance-field glyph sets in PBF, one file per 256-codepoint range (`0-255.pbf`, `256-511.pbf`, …), at `{glyphs}/{fontstack}/{range}.pbf`. [glyphs][spec-glyphs]
- **Generation:**
  - `maplibre/font-maker` (BSD-3) has a web UI and a CLI (`./font-maker --name "Noto Sans" output File1.ttf File2.ttf`). Several files can be merged under one name, which is how basemaps-assets covers much of Unicode. [font-maker][font-maker], [CONTRIBUTING][font-maker-contrib]
  - Alternative: `stadiamaps/sdf_font_tools` `build_pbf_glyphs` (BSD-3), which "crunch[es] a directory [of] fonts into PBF files". [sdf_font_tools][sdf-tools]
- **Naming:** the `text-font` names must equal the fontstack directory names exactly (`"Noto Sans Regular"`). With static hosting, a multi-font `text-font` array requests a comma-joined directory that must exist. [glyphs][spec-glyphs]
- **Protomaps assets:** fonts `Noto Sans Regular`, `Noto Sans Medium`, `Noto Sans Italic`, `Noto Sans Devanagari Regular v1`, with `OFL.txt` (SIL OFL). [assets][pm-assets], GitHub API. The Protomaps generator uses `Noto Sans Regular`/`Medium` by default (`flavor.regular` is undefined in `light`; measured). Self-host by copying the ZIP into the Caddy static path, so no third-party requests are made. [maplibre guide][pm-maplibre]
- **CJK:** the map option `localIdeographFontFamily` (default `'sans-serif'`) renders CJK locally instead of downloading glyph PBFs. [MapOptions][gljs-mapoptions]. font-maker notes that its demo enables local ideographs. Not relevant to Rome labels, but foreign-script names (for example on embassies) may appear.
- **Complex scripts:**
  - RTL (Arabic, Hebrew) renders without the plugin since GL JS 6.9.0, and `setRTLTextPlugin` is deprecated. [changelog][gljs-changelog]
  - Devanagari needs `pgf:name:*` with the PGF font. [l10n][pm-l10n]
  - `font-faces` (GL JS 6.7.0+, `map.setFontFaces`) hands TTF/OTF/WOFF files to the browser's CSS Font Loading API and draws "a grapheme cluster at a time", falling back to `glyphs`. [map.ts][gljs-mapts], [changelog][gljs-changelog]. **Conflict:** the spec's SDK table says GL JS is not supported (issue #6637). [spec font-faces][spec-fontfaces]. Verify against the pinned version before relying on it.
- **Variable fonts:** **unverified.** No primary source states support or non-support for glyph PBFs. SDF generators rasterize outlines of one instance, so the expectation is that only the default instance is used. Safe practice: generate PBFs from **static instances** (one file per weight/style). With `font-faces`, the browser's font engine might handle a variable WOFF2, but the weight axis cannot be selected from the style. This is also unverified.
- **Licensing:** choose OFL-1.1 fonts (Noto, Source Serif/Sans, IBM Plex, EB Garamond, Cormorant, and similar). The OFL allows embedding/serving and conversion. The derived PBFs keep the OFL and a Reserved Font Name may require renaming modified versions. Check the font's RFN clause; this is general OFL knowledge, so flag it for the licence allow-list check. An "engraved/historic" look suggests a serif or small-caps italic for water and place names (a cartographic convention). This is a design suggestion, not sourced.

## 7. Sprites and patterns

- **Format:** `sprite.png` + `sprite.json`, plus `sprite@2x.png`/`.json` on high-DPI displays. Each entry has `width`, `height`, `x`, `y`, `pixelRatio`, and optionally `sdf`, `content`, `stretchX/Y`, and `textFitWidth/Height`. [sprite][spec-sprite]
- **SDF:** with `"sdf": true`, an image can be recolored with `icon-color`/`icon-halo-color`. `icon-color` works "only with SDF icons". [sprite][spec-sprite], [layers][spec-layers]. SDF colorization of **patterns** is not supported: `fill-color` as the SDF pattern foreground is "not supported in GL JS or native". [layers][spec-layers]. **Pattern sprites must therefore be pre-colored**, with one image per theme color, which is a reason to generate the sprite per Instance theme.
- **Multiple sprites:** `"sprite": [{"id":"default","url":"…/basemap"},{"id":"tart","url":"…/tart"}]`, referenced as `tart:hatch-45`. This keeps TART marker/pattern assets separate from basemap icons. [sprite][spec-sprite]. At runtime, `map.addSprite(id, url)` and `map.addImage()` also exist. [Map API][gljs-map]
- **Tooling:** `spreet` v0.13.1 (MIT): `spreet icons/ out/tart`, `spreet --retina icons/ out/tart@2x`, plus `--sdf`, `--unique`, `--minify-index-file`, `--spacing`, and `--recursive`. [spreet][spreet]
- **Patterns:**
  - `fill-pattern`, `line-pattern`, `background-pattern`, and `fill-extrusion-pattern` take sprite image names.
  - `fill-pattern`/`line-pattern` are data-driven (GL JS ≥ 0.49), so you can `match` on `kind` to pick a hatch.
  - Zoom expressions on patterns are evaluated at integer zooms.
  - `fill-pattern` disables `fill-outline-color`. Draw outlines as a separate `line` layer.
  - `background-pattern` is not data-driven and disables `background-color`.
  - `line-pattern` disables `line-dasharray`. [layers][spec-layers]
  - Pattern tiles are repeated in screen pixels and are not scaled with zoom (**unverified** wording; consistent with sprite pixel semantics). Hatch density therefore stays constant on screen, which suits engraving.

## 8. Cartographic techniques for an engraved / historic look

| Effect | MapLibre mechanism | Notes |
|---|---|---|
| Paper texture | `background-pattern` with a tileable low-contrast sprite, or plain `background-color` | Not data-driven. Keep it subtle: texture under labels lowers effective contrast. |
| Hatched parks, water, blocks | `fill-pattern` (data-driven by `kind`) + separate `line` outline | Pre-colored pattern images. ADR 0015's hatched approximate-location area can use the same mechanism on a GeoJSON source. |
| Building blocks as solid poché | `fill` with `fill-color`, plus `fill-layer-opacity` for uniform tone where merged polygons overlap | `fill-layer-opacity` is GL JS 6.0.0+ only, not native. [layers][spec-layers] |
| Engraved street casings | Two `line` layers (casing below with a wider `line-width`, fill above), or a single layer with `line-gap-width` (draws two parallel lines with a gap: a "double-line street") | `line-gap-width` and `line-offset` are data-driven. |
| Dashed or dotted lines (demolished, boundaries, paths) | `line-dasharray` as a literal; `line-cap: round` with short dashes gives dots | Lengths are in line-width units. They can't come from feature properties, so use `case` on literals or separate layers. |
| Soft ink | `line-blur`, `text-halo-blur` | Use sparingly. |
| Antique lettering | `text-transform: uppercase`, `text-letter-spacing` (em, data-driven), italic fonts for water, `text-max-angle` for curved labels | |
| Curved street and river names | `symbol-placement: line` / `line-center`, `symbol-spacing` | |
| Label priority | `symbol-sort-key`, `text-padding`, `text-optional`, `text-allow-overlap` | |
| Halos | `text-halo-color` set to the paper color, `text-halo-width` ≤ ¼ of font size | Halos are the main tool for keeping labels at 4.5:1 over texture and hatching. [layers][spec-layers] |
| Relief | `hillshade` (`hillshade-method`: standard, basic, combined, igor, multidirectional; GL JS 5.5.0) or `color-relief` on a `raster-dem` source (`terrarium`/`mapbox`/`custom` encodings) | Needs a DEM tileset, which is out of budget unless self-generated. Rome's hills are subtle. Optional. [layers][spec-layers], [sources][spec-sources] |
| Historic raster overlay (old map scans) | `raster` layer with `raster-opacity`, `raster-saturation`, `raster-contrast` | Licensing of scans is a separate rights concern (CLAUDE.md). |
| Blending | **No blend modes.** Only per-feature opacity and per-layer `*-layer-opacity` exist. The spec says layer opacity "cannot be used to composite multiple layers together or control how this layer blends with layers above or below it." [layers][spec-layers] | A multiply look must be faked with pre-mixed colors. |
| Antialias | `fill-antialias: false` removes hairline seams on hatched fills, but gives jagged edges | |

Restraint for markers: the basemap should be low-chroma and mid-to-light value, with labels below the marker layers. Markers go in TART-owned layers inserted *above* basemap labels (or between basemap geometry and labels, with marker collision via `symbol` layers). ADR 0015's solid, dashed, and dotted squares can be `symbol` layers using SDF icons (recolorable, haloed), or `line` + `fill` on generated square polygons. SDF icons are simpler and scale-independent.

## 9. Workflow and tooling

- **Maputnik** (MIT, v3.1.0, 2026-07-06) is a visual editor: hosted at maplibre.org/maputnik or in Docker `ghcr.io/maplibre/maputnik:main`, with file-watch options. [maputnik][maputnik]. It supports `pmtiles://` vector sources natively: it registers the `Protocol` and has a "pmtiles_vector" source type (seen in its source code). Useful for exploring, but a generated style should not be hand-edited in Maputnik. Use Maputnik to prototype values, then port them to the theme.
- **Validation:** `@maplibre/maplibre-gl-style-spec` 26.4.4 (ISC) ships `gl-style-validate` (`--json` output), `gl-style-migrate`, and `gl-style-format`, and exposes `validateStyleMin`/`validate` as a library (library API names unverified beyond the CLI). [pkg][spec-pkg], [README][spec-readme]. The map also validates on load unless `validateStyle: false` is set. [MapOptions][gljs-mapoptions]. Run `gl-style-validate` in CI on every Instance style, as ADR 0009 requires fail-fast config.
- **Style as code vs static JSON:** ADR 0009 says an Instance config contains "a MapLibre style file". A TS generator (theme object → style JSON) can still be the authoring path if its output is the committed style file. Alternatively, the config holds a small theme file and the platform generates the style at build time, but that changes ADR 0009's contract and would need an ADR amendment.
- **URLs in the style:** the spec requires absolute `glyphs` and source URLs. Per-Instance hostnames differ, so either template the host at build or deploy time, or rewrite at load. `setStyle(style, {transformStyle})` and `transformRequest` exist on the Map. [Map API][gljs-map], [MapOptions][gljs-mapoptions]. Whether GL JS accepts relative `glyphs` URLs in practice is unverified.
- **Per-viewer runtime theming:** dark mode can be done by `setStyle(newStyle, {diff:true})` (minimal diff), or by `global-state` (`["global-state","theme"]` inside `match` on color properties) without reloading. [Map API][gljs-map]
- **Testing:** use render snapshots with Playwright screenshots of fixed camera positions over the Rome extract (needs WebGL2 in headless Chromium; SwiftShader availability is unverified for CI). Also validate the style JSON and check label contrast programmatically from the theme tokens (APCA/WCAG ratio of text color vs halo and background). Protomaps keeps `render-tests/` in its repo as a reference. [pm-repo]
- **Performance:**
  - Fewer layers mean fewer draw calls. 71 Protomaps layers is fine, but drop unused ones (POIs, shields, aeroways).
  - Symbol collision is the main CPU cost. Use `symbol-sort-key`, generous `text-padding`, and min zooms.
  - `fadeDuration` (default 300 ms) controls the label fade.
  - Layout properties that depend on zoom re-evaluate per integer zoom.
  - `cancelPendingTileRequestsWhileZooming` defaults to true. [MapOptions][gljs-mapoptions]
- **Self-hosted asset set per Instance:**
  - `rome.pmtiles` in the data volume
  - `fonts/<stack>/<range>.pbf`
  - `sprites/basemap(.json|.png|@2x…)`
  - `sprites/tart(...)`
  - `style.json`

  All are same-origin through Caddy, so there are no third-party requests, which is also a privacy gain.

## 10. Accessibility of the map

- **Canvas semantics:** GL JS sets `role="region"` and `aria-label` from the UI-string key `Map.Title`. Every control string is localizable through the `locale` map option (for example `NavigationControl.ZoomIn`, `AttributionControl.ToggleAttribution`). These must come from Paraglide messages, not the defaults. [map.ts][gljs-mapts], [default_locale.ts][gljs-locale]
- **Keyboard:** the `keyboard` option is on by default.
  - `+`/`=` zooms in by 1 and `-` zooms out by 1 (2 with Shift).
  - The arrow keys pan by 100 px.
  - Shift+←/→ rotates by 15°, and Shift+↑/↓ changes pitch by 10°. [keyboard.ts][gljs-keyboard]

  Canvas markers are not focusable. Artwork selection must also be possible from the synchronized list, which ADR 0004 already requires for no-WebGL2.
- **Reduced motion:** the `reduceMotion` option disables gesture inertia and, when unset, follows the OS setting (`prefers-reduced-motion`). [MapOptions][gljs-mapoptions], [map.ts][gljs-mapts]. Also set `transition.duration` to 0 and avoid `flyTo` animations under reduced motion. (The flyTo behavior under `prefersReducedMotion` is unverified.)
- **Contrast:**
  - Text in graphics must meet 1.4.3 (4.5:1, or 3:1 for large text).
  - Graphical objects "required to understand the content" need 3:1 against adjacent colors (1.4.11), but a graphic is exempt when text conveys the same information. [1.4.11][wcag-1411]

  Practical reading: artwork markers and their Condition signs are essential, so they need 3:1 against the basemap. Basemap streets and buildings are context and arguably not essential. Whether basemap labels count as "incidental" text is a judgment; target 4.5:1 with halos anyway. Note that the marker-to-basemap contrast must hold over every basemap fill (paper, buildings, parks, water). That favors a narrow value range in the basemap.
- **Not by color alone (1.4.1):** ADR 0015 already uses shape (solid, dashed, dotted) plus words. Hatching vs solid fill is likewise a non-color cue for approximate areas. [1.4.1][wcag-141]
- **Dragging (2.5.7, new in WCAG 2.2, AA):** pan and zoom by drag need a single-pointer alternative. Use the NavigationControl zoom buttons, plus pan buttons or the list or search, which MapLibre does not provide out of the box. [2.5.7][wcag-257]
- **Colour-vision deficiency:** no MapLibre-specific guidance was found. Simulate the palette (deuteranopia, protanopia, tritanopia) as part of the theme check. The design keeps color redundant, so this is about legibility, not meaning.
- **Attribution:** OSM requires the credit "OpenStreetMap" plus clarity that the data is ODbL, or "© OpenStreetMap contributors". It goes in a corner or adjacent to the map, and may collapse after interaction or after 5 s if it stays reachable via an "(i)" button. [OSMF guidelines][osm-attrib]. MapLibre's `AttributionControl` (compact by default) fits this. ADR 0009's non-empty attribution text should include OSM (and "© OpenMapTiles" if OMT is ever used). The planet build's own attribution string is `© OpenStreetMap` linking to /copyright (measured).

## 11. Recommendations for TART's style agent (recommendation, not decision)

1. **Tiles:** a Protomaps v4 basemap extract per Instance, made with `pmtiles extract <daily build> <instance>.pmtiles --region=<instance boundary>.geojson` (Rome ≈ 47 MB at z0–15). Refresh monthly or quarterly with a script, swapping the file atomically. Serve it with Caddy `file_server` under `/tiles/`, without `encode`.
2. **Style authoring:** a TS generator in the platform (`deploy/` or a `map-style` tool package), `theme → style.json`:
   - start from `layers("basemap", flavorFromTheme(theme), {lang})`;
   - apply a TART transform that drops POIs, shields, and aeroways, mutes colors, swaps fonts, sets letter-spacing and uppercase for district names, and adds hatch-pattern layers for parks, water, and (optionally) building blocks at z11–14;
   - append TART overlay layers (artwork clusters and markers, approximate-location hatch) on separate GeoJSON sources.

   Emit **one `style.json` per UI language** (`style.it.json`, `style.en.json`), or one style with a `global-state` `lang` key, since `text-field` is layout. Output goes into the Instance config directory per ADR 0009, validated with `gl-style-validate` in CI and at `tart config check`.
3. **Theme object** (per Instance, small): `paper`, `ink`, `inkMuted`, `water`, `waterHatch`, `park`, `parkHatch`, `building`, `roadFill`, `roadCasing`, `labelText`, `labelHalo`, `accent` (from instance.toml, already contrast-checked per ADR 0009), `fontRegular`, `fontItalic`, `fontCaps`, and a `dark` variant of each. Derive the full 74-key Flavor from these about 13 tokens, so that Instances can't produce an incoherent palette.
4. **Assets:** self-hosted Noto Sans (from basemaps-assets, OFL) plus at most one OFL display/serif face converted with font-maker. Use static instances only. Build two sprites with spreet: `default` (basemap icons, if kept) and `tart` (SDF marker squares, pre-colored hatch patterns at 1x/2x per theme).
5. **Labels:** `["coalesce", ["get","name:<lang>"], ["get","name"]]` for Latin-script Instances. Keep Protomaps' `get_multiline_name` if a future Instance is in a non-Latin-script city.
6. **Restraint:**
   - Basemap in 2–3 near-neutral values, with zero saturated colors.
   - Roads differentiated by width, not color.
   - No POIs by default, with labels only for districts, major streets, water, and landmarks.
   - Markers and the accent color are the only strong ink on the page.
   - Check the 3:1 marker-vs-every-basemap-fill rule in the theme test.
7. **Fallback:** catch `GPUInitializationError` and show the list and search path (ADR 0004).

## Open questions

- Is a historic/engraved look compatible with 4.5:1 label contrast over textures? Test with halos and decide whether the paper texture is z-limited or omitted.
- Does `font-faces` in the pinned GL JS version render as the changelog says (6.7.0), given the spec table says "not supported"? If yes, is serving WOFF2 simpler than PBF glyph generation?
- Is a per-language style file or a `global-state`-driven `text-field` the better fit with Paraglide routing (`/it/…`, `/en/…`)? Does a `global-state` change in a layout property re-layout tiles acceptably fast?
- Does ADR 0009's "style file in config" stay as generated output, or does the config carry a theme and the platform generate the style? The latter needs an ADR amendment.
- Absolute-URL requirement: template the host per deployment, or rewrite in `transformStyle`?
- Are disappeared artworks shown on the map by default? This is still open per ADR 0015 and affects the overlay layer filters (`global-state` toggle).
- Is the update cadence and pinning of the Protomaps tileset version tied to `@protomaps/basemaps` (v4 tiles need style ≥ 4.0.0)?
- Licence allow-list: BSD-3 (maplibre-gl, pmtiles, @protomaps/basemaps, font-maker), ISC (style-spec), MIT (spreet, Maputnik, tangrams icons), Apache-2.0 (planetiler), OFL-1.1 (fonts), CC0 (Protomaps design), and ODbL (data, attribution and share-alike for Derivative Databases). These need confirming against ADR 0011's tiers. ODbL share-alike is unlikely to be triggered by rendering (Produced Work [pm-downloads]), but this needs legal review if TART ever redistributes modified tiles.
- Is a DEM or hillshade worth it for Rome? It is not in the budget unless generated once from an open DEM, and that DEM's licence must be checked.

## Sources

- [gljs-changelog]: https://raw.githubusercontent.com/maplibre/maplibre-gl-js/main/CHANGELOG.md
- [gljs-releases]: https://github.com/maplibre/maplibre-gl-js/releases
- [gljs-pkg]: https://raw.githubusercontent.com/maplibre/maplibre-gl-js/main/package.json
- [gljs-mapts]: https://github.com/maplibre/maplibre-gl-js/blob/main/src/ui/map.ts
- [gljs-locale]: https://github.com/maplibre/maplibre-gl-js/blob/main/src/ui/default_locale.ts
- [gljs-keyboard]: https://github.com/maplibre/maplibre-gl-js/blob/main/src/ui/handler/keyboard.ts
- [gljs-map]: https://maplibre.org/maplibre-gl-js/docs/API/classes/Map/
- [gljs-mapoptions]: https://maplibre.org/maplibre-gl-js/docs/API/type-aliases/MapOptions/
- v6.0.0 date and WebGL2: https://newreleases.io/project/github/maplibre/maplibre-gl-js/release/v6.0.0 (mirror of GitHub release), https://maplibre.org/news/2026-08-02-maplibre-newsletter-jul-2026/
- [spec-root]: https://maplibre.org/maplibre-style-spec/root/
- [spec-v8]: https://github.com/maplibre/maplibre-style-spec/blob/main/src/reference/v8.json
- [spec-layers]: https://maplibre.org/maplibre-style-spec/layers/
- [spec-expr]: https://maplibre.org/maplibre-style-spec/expressions/
- [spec-sources]: https://maplibre.org/maplibre-style-spec/sources/
- [spec-glyphs]: https://maplibre.org/maplibre-style-spec/glyphs/
- [spec-sprite]: https://maplibre.org/maplibre-style-spec/sprite/
- [spec-fontfaces]: https://maplibre.org/maplibre-style-spec/font-faces/
- [spec-pkg]: https://raw.githubusercontent.com/maplibre/maplibre-style-spec/main/package.json
- [spec-readme]: https://github.com/maplibre/maplibre-style-spec
- [pm-layers]: https://docs.protomaps.com/basemaps/layers
- [pm-buildings]: https://github.com/protomaps/basemaps/blob/main/tiles/src/main/java/com/protomaps/basemap/layers/Buildings.java
- [pm-repo]: https://github.com/protomaps/basemaps
- [pm-pkg]: https://raw.githubusercontent.com/protomaps/basemaps/main/styles/package.json
- [pm-index]: https://github.com/protomaps/basemaps/blob/main/styles/src/index.ts
- [pm-language]: https://github.com/protomaps/basemaps/blob/main/styles/src/language.ts
- [pm-flavor]: https://maps.protomaps.com/typedoc/interfaces/Flavor.html
- [pm-flavors]: https://docs.protomaps.com/basemaps/flavors
- [pm-l10n]: https://docs.protomaps.com/basemaps/localization
- [pm-maplibre]: https://docs.protomaps.com/basemaps/maplibre
- [pm-downloads]: https://docs.protomaps.com/basemaps/downloads
- [pm-assets]: https://github.com/protomaps/basemaps-assets
- [pm-maplibre-pmtiles]: https://docs.protomaps.com/pmtiles/maplibre
- [pm-cli]: https://docs.protomaps.com/pmtiles/cli
- [pm-cloud]: https://docs.protomaps.com/pmtiles/cloud-storage
- [pm-server]: https://docs.protomaps.com/deploy/server
- Getting started (daily build URL pattern, extract): https://docs.protomaps.com/guide/getting-started
- [pmtiles-pkg]: https://raw.githubusercontent.com/protomaps/PMTiles/main/js/package.json
- [pmtiles-adapters]: https://github.com/protomaps/PMTiles/blob/main/js/src/adapters.ts
- go-pmtiles CLI v1.31.2: https://github.com/protomaps/go-pmtiles/releases
- Planet build header (measured with `pmtiles show` / `curl -I`): https://build.protomaps.com/20261009.pmtiles
- [caddy-fs]: https://caddyserver.com/docs/caddyfile/directives/file_server
- [caddy-src]: https://github.com/caddyserver/caddy/blob/master/modules/caddyhttp/fileserver/staticfiles.go
- [omt-schema]: https://openmaptiles.org/schema/
- [omt-license]: https://github.com/openmaptiles/openmaptiles/blob/master/LICENSE.md
- [shortbread]: https://shortbread-tiles.org/schema/1.0/
- [shortbread-search]: https://shortbread.geofabrik.de (schema CC0, via search summary)
- [shortbread-1.1]: https://community.openstreetmap.org/t/now-serving-shortbread-1-1-tiles/146864
- [planetiler]: https://github.com/onthegomap/planetiler
- [tippecanoe]: https://github.com/felt/tippecanoe
- [maputnik]: https://github.com/maplibre/maputnik
- [font-maker]: https://github.com/maplibre/font-maker
- [font-maker-contrib]: https://github.com/maplibre/font-maker/blob/main/CONTRIBUTING.md
- [sdf-tools]: https://github.com/stadiamaps/sdf_font_tools
- [spreet]: https://github.com/flother/spreet
- [osm-attrib]: https://osmfoundation.org/wiki/Licence/Attribution_Guidelines
- [wcag-1411]: https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html
- [wcag-141]: https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html
- [wcag-257]: https://www.w3.org/WAI/WCAG22/Understanding/dragging-movements.html

<!-- Link reference definitions for the citations above. -->

[gljs-changelog]: https://raw.githubusercontent.com/maplibre/maplibre-gl-js/main/CHANGELOG.md
[gljs-releases]: https://github.com/maplibre/maplibre-gl-js/releases
[gljs-pkg]: https://raw.githubusercontent.com/maplibre/maplibre-gl-js/main/package.json
[gljs-mapts]: https://github.com/maplibre/maplibre-gl-js/blob/main/src/ui/map.ts
[gljs-locale]: https://github.com/maplibre/maplibre-gl-js/blob/main/src/ui/default_locale.ts
[gljs-keyboard]: https://github.com/maplibre/maplibre-gl-js/blob/main/src/ui/handler/keyboard.ts
[gljs-map]: https://maplibre.org/maplibre-gl-js/docs/API/classes/Map/
[gljs-mapoptions]: https://maplibre.org/maplibre-gl-js/docs/API/type-aliases/MapOptions/
[spec-root]: https://maplibre.org/maplibre-style-spec/root/
[spec-v8]: https://github.com/maplibre/maplibre-style-spec/blob/main/src/reference/v8.json
[spec-layers]: https://maplibre.org/maplibre-style-spec/layers/
[spec-expr]: https://maplibre.org/maplibre-style-spec/expressions/
[spec-sources]: https://maplibre.org/maplibre-style-spec/sources/
[spec-glyphs]: https://maplibre.org/maplibre-style-spec/glyphs/
[spec-sprite]: https://maplibre.org/maplibre-style-spec/sprite/
[spec-fontfaces]: https://maplibre.org/maplibre-style-spec/font-faces/
[spec-pkg]: https://raw.githubusercontent.com/maplibre/maplibre-style-spec/main/package.json
[spec-readme]: https://github.com/maplibre/maplibre-style-spec
[pm-layers]: https://docs.protomaps.com/basemaps/layers
[pm-buildings]: https://github.com/protomaps/basemaps/blob/main/tiles/src/main/java/com/protomaps/basemap/layers/Buildings.java
[pm-repo]: https://github.com/protomaps/basemaps
[pm-pkg]: https://raw.githubusercontent.com/protomaps/basemaps/main/styles/package.json
[pm-index]: https://github.com/protomaps/basemaps/blob/main/styles/src/index.ts
[pm-language]: https://github.com/protomaps/basemaps/blob/main/styles/src/language.ts
[pm-flavor]: https://maps.protomaps.com/typedoc/interfaces/Flavor.html
[pm-flavors]: https://docs.protomaps.com/basemaps/flavors
[pm-l10n]: https://docs.protomaps.com/basemaps/localization
[pm-maplibre]: https://docs.protomaps.com/basemaps/maplibre
[pm-downloads]: https://docs.protomaps.com/basemaps/downloads
[pm-assets]: https://github.com/protomaps/basemaps-assets
[pm-maplibre-pmtiles]: https://docs.protomaps.com/pmtiles/maplibre
[pm-cli]: https://docs.protomaps.com/pmtiles/cli
[pm-cloud]: https://docs.protomaps.com/pmtiles/cloud-storage
[pm-server]: https://docs.protomaps.com/deploy/server
[pmtiles-pkg]: https://raw.githubusercontent.com/protomaps/PMTiles/main/js/package.json
[pmtiles-adapters]: https://github.com/protomaps/PMTiles/blob/main/js/src/adapters.ts
[caddy-fs]: https://caddyserver.com/docs/caddyfile/directives/file_server
[caddy-src]: https://github.com/caddyserver/caddy/blob/master/modules/caddyhttp/fileserver/staticfiles.go
[omt-schema]: https://openmaptiles.org/schema/
[omt-license]: https://github.com/openmaptiles/openmaptiles/blob/master/LICENSE.md
[shortbread]: https://shortbread-tiles.org/schema/1.0/
[shortbread-search]: https://shortbread.geofabrik.de
[shortbread-1.1]: https://community.openstreetmap.org/t/now-serving-shortbread-1-1-tiles/146864
[planetiler]: https://github.com/onthegomap/planetiler
[tippecanoe]: https://github.com/felt/tippecanoe
[maputnik]: https://github.com/maplibre/maputnik
[font-maker]: https://github.com/maplibre/font-maker
[font-maker-contrib]: https://github.com/maplibre/font-maker/blob/main/CONTRIBUTING.md
[sdf-tools]: https://github.com/stadiamaps/sdf_font_tools
[spreet]: https://github.com/flother/spreet
[osm-attrib]: https://osmfoundation.org/wiki/Licence/Attribution_Guidelines
[wcag-1411]: https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html
[wcag-141]: https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html
[wcag-257]: https://www.w3.org/WAI/WCAG22/Understanding/dragging-movements.html
