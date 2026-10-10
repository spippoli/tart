---
status: accepted
---

# The basemap is a tinted early-1900s city plan in continuous lines, leaving dashes and hatching to TART's signs

TART's basemap borrows the chromolithographed tourist plan of c. 1900 (Baedeker): flat warm blocks with key-plate outlines, ruled water, letter-spaced district capitals, and a Goudy serif. Every basemap line is continuous: dashes, dots, and line hatching are reserved for the ADR 0015 signs (dashed and dotted Condition squares, the hatched approximate area), so the base can never be mistaken for archive meaning. We chose the tinted plan over a monochrome line plan, a Nolli figure-ground, and a street-only plan after comparing all four over the real Rome tiles at z14 and z17, at 1x pixel density, in greyscale, and with a deuteranopia simulation. The decision came from a throwaway prototype (branch `prototype/36-map-cartography`; decision ticket [Map cartography style](https://github.com/spippoli/tart/issues/36); research input [Research: map cartography style inputs](https://github.com/spippoli/tart/issues/34)).

## Rules

- **Reserved semantics.** The basemap uses no dashed, dotted, chequered, or hatched lines or fills: rail, boundaries, paths, and tunnels are continuous or hidden. Rail is a thin continuous ink line; service and yard tracks are hidden below z15, because parallel tracks read as hatching at city scale.
- **No public-building tint.** All buildings share one block tint, so there is no carmine to compete with the accent.
- **Rome walls and archaeology are in the MVP**, as an Instance overlay from OpenStreetMap (ODbL, ADR 0016): walls as a heavy ink line, ruins and archaeological sites as outlines, with italic names from z15.5.
- **District labels come from the archive's Areas**, not from OpenStreetMap neighbourhoods, in letter-spaced capitals from z12 to z16.
- **Approximate area**: 45° ink hatching, 10 px spacing, no outline, from z15. Below z15 an approximate Location shows only its smaller sign. Layer order from the bottom: base geometry and overlays, the approximate-area hatch, basemap labels (with a paper halo), then clusters and Condition signs.
- **Typography**: Sorts Mill Goudy (OFL, no Reserved Font Name) in Regular for streets and districts and Italic for water and ruins, served as font files through the style's `font-faces`. Noto Sans is kept for cluster counts and as the glyph fallback. The city's name is not on the map.
- **Contrast**: Condition signs and the accent stay at ≥ 3:1 against every basemap fill (paper, block, park, water, road), and labels at ≥ 4.5:1 against their halo. An Instance accent (ADR 0009) is validated against the map fills as well as the UI backgrounds.
- **Pan and zoom without dragging** (WCAG 2.5.7): one map control with zoom in/out, four pan buttons (a third of the view each), and a button back to the Instance's default view, replacing MapLibre's `NavigationControl`. Rotation and pitch are disabled; reduced motion makes moves instant.
- **Dark theme**: an ink negative of the same tokens, chosen with the UI theme.

## Draft tokens

| Token | Light | Dark |
|---|---|---|
| `map.paper` | `#F3EEE2` | `#1E1B18` |
| `map.block` | `#EBCBBE` | `#3A2A25` |
| `map.park` | `#DCE5CC` | `#222A20` |
| `map.water` | `#C5D7DE` | `#18252B` |
| `map.waterline` | `#8EA9B3` | `#36505A` |
| `map.ink` | `#2A2521` | `#EAE2D5` |
| `map.casing` | `#6F6359` | `#857669` |
| `map.ruin.line` | `#6E5E52` | `#A69482` |
| `map.label.street` | `#3A332E` | `#DCD2C5` |
| `map.label.district` | `#5E4636` | `#C9AE9A` |
| `map.label.water` | `#2F5562` | `#A0C0CA` |
| `marker.ink` | `#1F1B18` | `#F6F0E6` |
| `marker.accent` (Instance accent) | e.g. `#2E3F8F` | e.g. `#A3B4FF` |

Measured: marker ink ≥ 11:1 and accent ≥ 6:1 on every fill; labels ≥ 5.4:1; ruin lines 4.1:1 on blocks (light). Re-run the checks whenever a token changes.

## Considered Options

- **Monochrome line plan with one warm tint** (EB1911 strand, the research's recommendation): restrained, but at z14 the building outlines turn the centre into noise.
- **Figure-ground** (Nolli poché): strong character, but the 45° hatch is illegible over mid-tone building masses.
- **Street network without blocks**: the most headroom for markers, but it loses the archival look the brief asks for.
- **Other OFL serifs** (Spectral, Old Standard TT, EB Garamond, IM Fell DW Pica, Linden Hill, Cinzel for capitals): at 11–13 px they are nearly indistinguishable; Goudy was preferred on a specimen at map and enlarged sizes.

## Consequences

- The Rome archive starts empty, so the map shows no district labels until Areas are recorded.
- The `font-faces` path works in MapLibre GL JS 6.13 in the prototype, although the style specification's support table still marks GL JS as unsupported; pin and test the version.
- Who owns the style (Instance theme vs style file), the tile pipeline, and overlay behaviour stay with their own decisions ([Map style ownership: Instance theme vs style file](https://github.com/spippoli/tart/issues/37), [Basemap tile pipeline per Instance](https://github.com/spippoli/tart/issues/38), [Map behaviour: clustering, geometries, overlays, stratigraphy](https://github.com/spippoli/tart/issues/39)).
