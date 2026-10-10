---
status: accepted (provisional, pending professional legal review)
---

# Non-code assets and map data have their own licence policy, separate from the dependency tiers

The map brings in licences that ADR 0011's three dependency tiers don't cover: SIL OFL 1.1 fonts, the CC0 Protomaps map design, and ODbL OpenStreetMap data. The tiers measure how tightly *code* is bound to TART (linked, bundled, separate program), which is meaningless for a font or a database. So non-code assets and data get a separate policy, organised by asset type, which amends ADR 0011 §8. It also separates what the **platform** distributes (fonts, sprites, the style generator) from what an **Instance** obtains and serves (its basemap tile extract and any overlays), which is the Operator's responsibility, not a software dependency. Research input: [Research: map cartography style inputs](https://github.com/spippoli/tart/issues/34) (PR #32); decision ticket: [Licence policy for map assets and basemap data](https://github.com/spippoli/tart/issues/35).

## 1. Assets the platform distributes

| Asset type | Allowed licences | Main obligation |
|---|---|---|
| Fonts | OFL-1.1 | ship the licence text with the font and its derived glyphs; respect any Reserved Font Name |
| Map style design, icons, images | CC0-1.0, CC-BY-4.0, and the permissive code licences of ADR 0011 (MIT, BSD, Apache-2.0, ISC) | CC BY: credit |

- **Excluded**: share-alike (CC BY-SA), because it would extend to whatever incorporates the asset, such as a composite sprite or a derived style; non-commercial (NC), because it would layer a second, different definition of "non-commercial" on top of PolyForm's; no-derivatives (ND), because converting a font to glyph PBFs or recolouring an icon is a modification.
- **CC BY credits** appear on the About TART page and in the third-party notices, never on the map. The only mandatory credit on the map is the data attribution (section 4).
- **Reserved Font Name**: converting a font to SDF glyph PBFs, or subsetting it, is treated as producing a Modified Version. A font with an RFN is allowed only if its derived fontstack name (the folder name `text-font` refers to) doesn't use the reserved name. Noto Sans, the Protomaps default, has no RFN.
- TART's own cartographic assets (sprites, hatch patterns, the style generator) are part of the repository and stay under PolyForm Noncommercial 1.0.0 (ADR 0011 §1). The style file in an Instance's configuration directory belongs to its Operator.

## 2. OpenStreetMap data and the ODbL boundary

- **The rendered basemap is a Produced Work.** Showing OSM-derived tiles as a map needs attribution only, not share-alike. The PMTiles extract is a Derivative Database, served unchanged under the ODbL as Instance data.
- **OSM-derived overlays** (for example Rome's walls and archaeological areas, if the tile pipeline builds them) are Derivative Databases used publicly. They stay under the ODbL, and the Operator must be able to offer the derived database or the method to recreate it (the extraction script). They never flow into archive data.
- **Archive data is never derived from OSM.** No import or snapping of OSM geometries, and no stored geocoding results, in Locations or any other Archive record. Otherwise ODbL share-alike could reach the archive database and clash with the Instance's Data licence (CC0, CC BY, or CC BY-SA; Rome uses CC BY-SA, ADR 0012). Drawing a Location by clicking on the basemap is not systematic extraction. Any future address search or snapping feature needs a new decision.

## 3. CI licence allow-list

- **Asset packages** (for example `@fontsource/*` or `@protomaps/basemaps-assets`): OFL-1.1, CC0-1.0, and CC-BY-4.0 are allowed only for packages listed by name in an asset list in the CI configuration, so a code package with an asset licence cannot slip through.
- **Assets vendored into the repository** (generated glyph PBFs, third-party sprite sources): each has an entry in a third-party asset manifest recording its SPDX licence, source, credit, and Reserved Font Name. CI checks that every file in a third-party asset directory has an entry and that its licence is allowed by section 1. The manifest also generates the third-party notices and the credits on the About TART page.
- **Tile data and overlays** are not in the repository and are not checked by CI. The Operator documentation covers them (sections 2 and 4).

## 4. Map attribution

- **Configuration**: ADR 0009's attribution is a list of `{text, url}` entries rather than free HTML; the platform renders the links. Validation requires at least one entry. It doesn't require OpenStreetMap, because an Instance may use non-OSM tiles.
- **OSM minimum**: the Operator documentation and Rome's configuration require `© OpenStreetMap` linking to `https://www.openstreetmap.org/copyright`. This matches the OSMF attribution guidelines and the Protomaps build's own attribution string.
- **Language**: the attribution is configuration content and is not translated (`© OpenStreetMap` is language-neutral). Only the label of the attribution toggle button is a UI string.
- **Display**: a MapLibre AttributionControl in a map corner. It may collapse after interaction, as the OSMF guidelines allow, but its toggle stays keyboard-reachable and labelled. Without WebGL2 only the list is shown, with no basemap and so no attribution.
- **Courtesy credits** (Protomaps, MapLibre, fonts) are not shown on the map; they appear on the About TART page from the manifest.

## 5. Professional legal review

To add to ADR 0011 §9:

1. Whether converting or subsetting a font into glyph PBFs makes a Modified Version for Reserved Font Name purposes.
2. Whether shipping the OFL text alongside the glyphs meets the OFL's distribution terms when glyphs are served to browsers.
3. Whether Locations drawn by looking at an OSM basemap stay outside the ODbL's notion of a Derivative Database.
4. The practical offer obligations for OSM-derived overlays published by a small Instance.
5. Whether using ODbL data next to an Instance's Data licence (for example CC BY-SA) raises any compatibility issue.

## Considered Options

- **A fourth tier in ADR 0011's table**: simpler, but the tiers' criterion (how code is bound to TART) doesn't apply to fonts or data, and the obligations (licence text and RFN for fonts, share-alike for databases) differ in kind.
- **Only fonts without a Reserved Font Name**: easier to check, but it would rule out typefaces such as Source Serif or IBM Plex before the cartography style is chosen.
- **The platform validator requiring an OSM credit**: it would break Instances that use non-OSM tiles.
