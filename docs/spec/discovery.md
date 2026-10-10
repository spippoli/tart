# Discovery

Feature spec 3 of 7 in the [delivery order](index.md#delivery-order). It covers how people find things in an **Instance**'s archive: the Explore map and the Archive list, which share one filter state; search and filters; the map's cartography style and how an Instance owns it; the basemap tile pipeline and Instance overlays; the mini-map on record pages; and everything that keeps discovery usable without the map. It depends on [Foundations](foundations.md) (Instance configuration and its validation, page shell, i18n shell, Operator CLI, Caddy) and [Archive records](archive-records.md) (the records, Condition and Condition group, Uncertain dates, visibility rules, record pages that embed the mini-map). Compile ticket: [Compile Discovery spec](https://github.com/spippoli/tart/issues/52).

Every section except Further Notes is normative. The invariants, language rules, and implementation principles in [`CLAUDE.md`](../../CLAUDE.md) apply and override any reading of this spec that contradicts them. Terms in **bold** are [glossary](../../GLOSSARY.md) terms and carry exactly that meaning ([spec index, Sources of truth](index.md#sources-of-truth)).

## References

**ADRs applied**

| ADR | What this spec takes from it |
|---|---|
| [0003](../adr/0003-location-as-shared-physical-surface.md) | The Location is the shared surface and the map's spatial unit; Sites group Locations by proximity, Areas by region |
| [0004](../adr/0004-mvp-tech-stack.md) | Plain MapLibre GL JS and the `pmtiles` protocol inside one app-level map module that no other code imports; Caddy serves PMTiles with byte ranges; MapLibre v6 needs WebGL2, so the list must work fully without the map |
| [0008](../adr/0008-single-content-language-and-prefixed-ui-languages.md) | Content in one Content language with its own `lang`; UI strings, path segments, and vocabulary labels per UI language; dates and numbers through `Intl` |
| [0009](../adr/0009-instance-configuration-as-validated-files.md) | Boundary polygon and default map view; two finished style files at fixed paths, archive layers inserted by the platform, asset rewriting, the symbolic basemap URL, external `https` sources, map style validation, accent with a light and a dark value, the non-empty attribution list (as amended by [#37](https://github.com/spippoli/tart/issues/37) and [#38](https://github.com/spippoli/tart/issues/38)) |
| [0010](../adr/0010-public-url-scheme.md) | Record URLs and translated path segments; Explore and Archive share the query string; 301 for merged duplicates and 410 for withdrawn records |
| [0015](../adr/0015-condition-and-uncertainty-presentation.md) | Three signs by Condition group (solid, dashed, dotted square) next to the Condition word; hatched area with a smaller sign for an approximate Location; uncertainty in words; colour always redundant; pending content never public |
| [0016](../adr/0016-licence-policy-for-map-assets-and-data.md) | Licences of fonts, sprites, and style design; the ODbL boundary (rendered basemap is a Produced Work, extract and overlays stay ODbL, archive data never derived from OSM); map attribution display; asset manifest |
| [0017](../adr/0017-map-cartography-style.md) | The tinted-plan reference style, reserved line semantics, approximate-area hatch, layer order, typography, draft tokens and contrast rules, non-drag pan/zoom control, dark theme |
| [0019](../adr/0019-map-shows-locations-not-artworks.md) | One sign per Location; filters apply to Artworks; sign priority *present* > *unknown* > *disappeared*; the stack; disappeared Artworks shown by default; clusters count Artworks |

**Glossary terms applied**: Instance, Operator, Instance configuration, UI language, Content language, Artwork, Expression type, Location, Surface type, Site, Area, Series, Documentation item, Condition, Condition group, History event, Creation event, Uncertain date, Observed date, Source, Artist, Alias, Attribution, Archive record, Revision, Merge, Withdrawal, Redaction, Submission.

**Decision tickets incorporated**: [Map behaviour: clustering, geometries, overlays, stratigraphy](https://github.com/spippoli/tart/issues/39), [List alternative and map/list sync](https://github.com/spippoli/tart/issues/40), [Search and filters](https://github.com/spippoli/tart/issues/41), [Map cartography style](https://github.com/spippoli/tart/issues/36), [Map style ownership: Instance theme vs style file](https://github.com/spippoli/tart/issues/37), [Basemap tile pipeline per Instance](https://github.com/spippoli/tart/issues/38), [Licence policy for map assets and basemap data](https://github.com/spippoli/tart/issues/35) (map attribution and assets), and, for the parts that shape discovery, [Information architecture and page inventory](https://github.com/spippoli/tart/issues/15) (Explore and Archive views, header search, empty archive), [Status, uncertainty and condition presentation rules](https://github.com/spippoli/tart/issues/17) (signs), [Submission form flow](https://github.com/spippoli/tart/issues/27) (Location drawing modes that the map module serves), and [Research: map cartography style inputs](https://github.com/spippoli/tart/issues/34) (background), and [History event types and Uncertain-date ordering](https://github.com/spippoli/tart/issues/89) (stratigraphy order, Uncertain date range and sort key).

**Prototype and research assets** (throwaway, linked rather than copied): the cartography prototype on branch [`prototype/36-map-cartography`](https://github.com/spippoli/tart/tree/prototype/36-map-cartography/frontend/prototypes/map-cartography), with screenshots at [Campo Marzio z17](https://github.com/spippoli/tart/blob/prototype/36-map-cartography/frontend/prototypes/map-cartography/screenshots/campo-marzio-z17-ABCD.jpg), [z14](https://github.com/spippoli/tart/blob/prototype/36-map-cartography/frontend/prototypes/map-cartography/screenshots/campo-marzio-z14-ABCD.jpg), and [dark, greyscale, and deuteranopia checks](https://github.com/spippoli/tart/blob/prototype/36-map-cartography/frontend/prototypes/map-cartography/screenshots/checks-dark-grey-deut.jpg) (variant C is the chosen strand); the research notes on branch [`research/map-cartography-style`](https://github.com/spippoli/tart/tree/research/map-cartography-style/docs/research) (`maplibre-pmtiles-style.md`, `early-1900s-urban-map-graphics.md`); the presentation prototype on branch `prototype/17-status-presentation`. Their markers and Area records are fictional.

## Problem Statement

A visitor to an urban art archive (Journey A) wants to look at a city and see what has been painted, pasted, or installed on its walls, including what is gone. A map is the natural entry point, but a naive map fails this archive in several ways. Pins per artwork pile up on a façade that has hosted five successive pieces and split its layered history; a pin vanishes when the work is painted over, presenting a "what is visible today" guide instead of an archive; colourful status markers and popularity rankings turn documentation into engagement; an approximate position drawn as an exact point misleads; a cartographic style full of dashes and hatches collides with the signs the archive uses for disappearance and approximation. Beyond the map, a researcher needs precise lookup: search by name, tag, or Artist alias across an archive written in one Content language, filters by condition, type, area, attribution, and date that respect uncertain dates, and a stable, non-popularity ordering. All of this must work without WebGL2, without JavaScript, by keyboard and screen reader, on a phone in the street, in every UI language, and for any Instance's territory, map style, and tile source, on a server budget of a few euros a month.

## Solution

Discovery is one surface with two views sharing one filter state in the query string: **Explore** (`/it/`, the homepage) shows a map with a synchronized, paginated list of the matching Artworks in the viewport; **Archive** (`/it/archivio`) shows the same filtered set as a paginated list that ignores the viewport. The map draws one sign per Location: the sign's shape follows the Condition group of the matching Artworks on that surface, a second offset outline marks a surface with several, and selecting a sign opens a side panel (a bottom sheet on mobile) with the surface's stratigraphy. Locations cluster into neutral numbered circles up to z16; from z17 lines and polygons draw their geometry. Search runs in PostgreSQL only: trigram matching on names and stemmed full-text search in the Content language on descriptions, returning Artworks plus an "Also matching" box of related records. Filters (Condition group and Condition, Expression type, Area, Attribution, Artist and Series by link, two date ranges by overlap) combine OR within and AND across, and ordering never uses popularity.

The basemap is the Instance's own pair of finished MapLibre styles (light and dark), with the platform's tinted early-1900s plan as the reference; the platform inserts its archive layers into them and validates TART's rules at startup. Each Instance extracts its basemap tiles from Protomaps with `tart tiles update` into a versioned PMTiles file served by Caddy, and keeps OSM-derived overlays as committed GeoJSON. Without WebGL2 the Explore URL renders the Archive view in place under a notice, record pages replace the mini-map with text, and every view is server-rendered so it works without JavaScript.

## User Stories

**Visitor on the map**

1. As a visitor, I want the homepage to be a map of the archive with a short introduction, so that I can start exploring immediately.
2. As a visitor, I want one sign per surface, not per artwork, so that a wall with several works stays one readable place.
3. As a visitor, I want a sign's shape to tell me whether something can still be seen there (solid), is gone (dashed), or is of unknown condition (dotted), so that I can read the map without relying on colour.
4. As a visitor, I want a surface with several matching works to look stacked, so that I know there is a layered history before opening it.
5. As a visitor, I want disappeared artworks shown by default, so that the map is an archive and not only a guide to what is visible today.
6. As a visitor, I want dense areas grouped into numbered clusters that zoom in when I activate them, so that the centre of Rome stays legible.
7. As a visitor, I want to select a sign and see a panel with the surface and its artworks from most recent to oldest, so that I can read the stratigraphy of one wall.
8. As a visitor, I want the panel to tell me how many works on this surface don't match my filters, so that I know the panel is filtered.
9. As a visitor, I want an approximate location drawn as a hatched area with a smaller sign and stated in words, so that I am not misled about precision.
10. As a visitor, I want lines and polygons drawn when I zoom in close, so that I see the real extent of a long wall or a hall of fame.
11. As a visitor, I want Site names and district names (from the archive's Areas) on the map, so that I can orient myself in the archive's own geography.
12. As a visitor, I want a legend I can open, so that I learn the signs without guessing.
13. As a visitor, I want the selected surface and the current view in the URL, so that I can share a link that reopens exactly what I see.
14. As a visitor, I want the map to follow my light or dark theme, so that it fits the rest of the interface.
15. As a visitor, I want a basemap that never uses dashes or hatching for streets or rail, so that I never mistake the city for archive signs.

**Visitor in the list**

16. As a visitor, I want a list of the matching artworks in the current map view, beside the map on desktop and behind a Map/List switch on mobile, so that I can browse without reading the map.
17. As a visitor, I want each list entry to show a thumbnail, title, Condition word and sign with the latest documentation date, attribution summary, and where it is, so that I can choose what to open.
18. As a visitor, I want a "Show on map" button on each entry that selects its surface, so that I can move from the list to the map.
19. As a visitor, I want entries of the surface I selected on the map marked "Selected", so that I see the link between map and list without the list jumping.
20. As a visitor, I want numbered pages of 24 rather than infinite scroll, so that I keep my place and can reach the footer.
21. As a visitor, I want to hear how many artworks are in the area when I stop moving the map, so that I know the list changed.
22. As a visitor, I want the Archive view to list the whole filtered archive regardless of the map, so that I can browse everything.

**Searching and filtering**

23. As a researcher, I want to search by title, description, an Artist's name or Alias, or the name of a Series, Site, or Area, so that I find artworks from whatever I know.
24. As a researcher, I want searches to tolerate typos and accents, so that "acca" or a misspelt tag still finds the work.
25. As a researcher, I want an "Also matching" box linking to Artists, Sites, Areas, and Series whose names match, so that I can jump to those records.
26. As a visitor reading in English, I want my search to find Italian content exactly as an Italian reader would, so that the UI language never hides results.
27. As a researcher, I want to filter by Condition group and drill down to the exact Condition, by Expression type, by Area, by attribution (unknown, attributed, disputed), and by documented or created years, so that I can narrow the archive precisely.
28. As a researcher, I want date filters to match uncertain dates by overlap and to tell me how many artworks without a creation date were left out, so that uncertainty never silently excludes or includes works.
29. As a visitor, I want "Show on the map" on an Artist or Series page to open the map filtered to its artworks, so that I can see where an artist worked.
30. As a researcher, I want results ordered by most recently documented, oldest documented, recently added, title, or relevance, and never by popularity, so that the order reflects the archive, not engagement.
31. As a visitor, I want active filters as removable chips and a "Clear all filters" action, so that I can always see and undo what narrows the results.
32. As a visitor with no results, I want to be told so and offered ways out (clear filters, search the whole archive, widen the view), so that I am never stuck.
33. As a visitor, I want the filters to work as a plain form without JavaScript, so that I can use the archive on any browser.
34. As a visitor on a phone, I want the filters in a full-screen dialog applied with "Show results", so that the results don't change under my thumb.
35. As a visitor, I want to filter the Artists, Sites, Areas, and Series indexes by name, so that I can find a record in a long list.

**Accessibility and fallbacks**

36. As a keyboard user, I want to pan and zoom with buttons and keys, never only by dragging, so that I can use the map without a pointer.
37. As a keyboard user, I want a skip link past the map to the list and a link back, so that I don't have to tab through every sign.
38. As a screen-reader user, I want each sign and cluster to have a name that states the counts per Condition group, so that I get the same information as sighted users.
39. As a visitor without WebGL2, I want Explore to show the full archive list with a notice explaining why the map is missing, so that I can still browse everything from the same URL.
40. As a visitor without WebGL2, I want record pages to state the location in text with a link to open it in a maps app, so that I still know where a work is.
41. As a visitor who opens a shared map link without WebGL2, I want a notice linking to the selected surface's page, so that the link is still useful.
42. As a visitor with reduced-motion settings, I want map moves to be instant, so that the map doesn't animate.

**Contributor (Location entry)**

43. As a contributor without the map, I want to choose an existing Location from a text list, type or paste coordinates, or use my device position, so that I can still document an artwork.
44. As a contributor, I want a coordinates field that accepts decimal, degrees-minutes-seconds, a `geo:` URI, or a pasted map link, and confirms the parsed point in words, so that I can enter a position precisely even with the map available.

**Operator**

45. As an Operator, I want to ship my own light and dark map styles and have the platform add the archive layers, so that my archive has its own cartography without forking the platform.
46. As an Operator, I want startup and `tart config check` to reject a style that uses dashes or hatches, misses its metadata, references missing files, or fails contrast, so that I can't ship a misleading or inaccessible map.
47. As an Operator, I want one command that extracts my basemap tiles from my boundary and swaps them in atomically, so that refreshing the map is safe and cheap.
48. As an Operator, I want a startup warning when my tiles are missing or out of date with my boundary or style, so that I notice without the service going down.
49. As an Operator, I want to use an external tile source instead, with the platform handling the Content-Security-Policy, so that I am not forced to host tiles.
50. As an Operator, I want the OSM attribution configured once and shown in an accessible control, so that I meet the ODbL attribution duty.

## Implementation Decisions

### Scope and dependencies

- This spec owns the Explore and Archive views, search and filters, index name filtering, the map module and everything it draws (Explore map, record-page maps, mini-map), the map style rules and serving, the basemap tile pipeline, overlays, and the map's behaviour without WebGL2.
- The records and what is public are [Archive records](archive-records.md): this spec shows only approved, public content and never decides visibility. The record pages (including where they embed a map) are Archive records; this spec specifies the map they embed.
- Loading and validating the configuration directory, the Operator CLI framework, the page shell (header search field, theme, landmarks), and the i18n shell are [Foundations](foundations.md). This spec adds the map style rules the loader enforces, the `tart tiles update` command, and when the header search field is omitted.
- The Submission editor's Location step is Contribution and moderation; this spec specifies the map module it embeds (drawing by clicks and the crosshair mode of [#27](https://github.com/spippoli/tart/issues/27)) and the Location entry without the map ([Location entry without the map](#location-entry-without-the-map)), which amends that step.
- The licence of platform map assets and the CI asset manifest are fixed by [ADR 0016](../adr/0016-licence-policy-for-map-assets-and-data.md); keeping tiles out of backups and the external tile provider's compliance item belong to Operations and portability and Rights and legal actions.

### Modules

| Module | Interface (what callers see) | Lives in |
|---|---|---|
| Map module | Render a map into a container from a served style and a data source: Explore (Locations GeoJSON, selection, viewport, events for selection and movement end), area/site/series map (fit to an extent, only given Locations), mini-map (one highlighted Location, muted neighbours), drawing (point, line, simple polygon; click and crosshair modes) for the editor. Reports "map unavailable" on missing WebGL2 or a style that fails to load. The only code that imports MapLibre ([ADR 0004](../adr/0004-mvp-tech-stack.md)) | frontend |
| Filter state | Parse and serialise the shared query-string state (search, filters, order, selection `luogo`, viewport `mappa`) with localized keys and stable values; remap keys on a UI-language switch | frontend |
| Discovery query | Given a filter state, return (a) the matching Artworks as one page of list entries with the total, (b) all matching Locations as one lightweight GeoJSON (id, geometry, representative point, prevailing Condition group, matching count, per-group counts), (c) the "Also matching" records, (d) the count of Artworks left out by "Created between" | backend (`api`) |
| Location panel | Given a Location id and a filter state, return the Location header and its stratigraphy of matching Artworks plus the count of non-matching ones | backend (`api`) |
| Index name filter | Filter an index (Artists with Aliases, Sites, Areas, Series) by name, alphabetical in the Content language, 24 per page | backend (`api`) |
| Map style service | Validate the two style files (startup and `tart config check`, invoked by the Foundations loader); serve a style at a fixed endpoint with asset paths and the symbolic basemap URL rewritten to absolute URLs; supply the archive-layer insertion point and tokens to the map module | backend (`api`) |
| Tile pipeline | `tart tiles update [--build YYYYMMDD] [--source URL]`: extract, check, and atomically swap the basemap; startup checks of the manifest | backend (`api` image, Operator CLI) |
| List entry | One card component for the side-panel stratigraphy, the Explore list, and `/archivio` | frontend |
| Coordinates parser | Parse decimal, degrees-minutes-seconds, `geo:` URI, and OpenStreetMap or Google Maps links into a point, or an error code | frontend (editor) |

Search and filtering are queries over PostgreSQL behind the Discovery query interface; no search port or external engine is introduced. Callers of the map module never touch MapLibre objects.

### Explore and Archive views

- **Explore** (`/it/`, `/en/`) is the homepage: a compact intro band (archive name, short description, link to About), the filter bar, the map, and the synchronized list ([#15](https://github.com/spippoli/tart/issues/15)). On desktop the list sits beside the map; on mobile a "Map / List" switch shows one at a time, and the Map view becomes the initial view after hydration when the map is available.
- **Archive** (`/it/archivio`, `/en/archive`): the filter bar, the "Also matching" box, and the paginated list of all matching Artworks. It ignores the viewport.
- Both views share one filter state in the query string. Switching views keeps the filters and drops the viewport (`?mappa=`).
- **Header search**: on every page other than Explore and Archive, the header search field submits to the Archive view with `?q=`. On Explore and Archive the header field is omitted, leaving only the filter bar's field, which is bound to the shared state (and to the viewport on Explore). There is no autocomplete.
- **Empty archive at launch**: the band "the archive has just started: document the first artwork" ([#15](https://github.com/spippoli/tart/issues/15)) replaces the results; the filter bar and search are hidden, not disabled.

### The map: signs, stack, clusters, geometries

From [ADR 0019](../adr/0019-map-shows-locations-not-artworks.md) and [#39](https://github.com/spippoli/tart/issues/39):

- **Map unit.** One sign per **Location**, never per Artwork. Filters apply to Artworks. A Location appears when at least one of its Artworks matches, and its sign reflects only those.
- **Sign.** Over the matching Artworks, the Condition group priority is *present* > *unknown* > *disappeared*: a solid square if any is present, otherwise a dotted square if any is unknown, otherwise a dashed square ([ADR 0015](../adr/0015-condition-and-uncertainty-presentation.md)). Colour is redundant to shape; the accent of ADR 0015 for *disappeared* never carries meaning alone.
- **Stack.** A Location with more than one matching Artwork gets a second outline offset behind its square, a difference of shape, not colour.
- **Accessible name of a sign** gives the counts per group, e.g. "Location, 3 artworks: 1 present, 2 disappeared".
- **Disappeared Artworks are shown by default.** The Condition group filter (present, disappeared, unknown; all on by default) hides them.
- **Clustering.** MapLibre client-side clustering of Locations by their representative point, radius about 50 px, active up to z16 and off from z17. A cluster is a **neutral circle** (ink on paper, never a Condition sign) showing the number of matching Artworks in Noto Sans, with no per-group breakdown. Clusters are focusable; accessible name "Cluster of 24 artworks in 9 Locations; activate to zoom in". Click, Enter, or Space zooms to the cluster's expansion zoom.
- **Data.** All filtered Locations in one lightweight GeoJSON response (id, geometry, representative point, prevailing group, count), with no viewport paging.
- **Lines and polygons.** Up to z16 every Location is only its square sign at its representative point. From z17, lines and polygons also draw their geometry in `marker.ink` at about 3 px, styled by the prevailing group: continuous for *present*, dashed for *disappeared*, dotted for *unknown*. Polygons get an outline only, no fill.
- **Hit targets.** Selection targets the square sign, at least 24×24 px (WCAG 2.5.8). A click on a drawn geometry also selects it, with a slightly widened hit area. Keyboard and screen readers reach Locations only through their signs, so each Location has exactly one focusable element.
- **Approximate Locations.** An approximate point shows a smaller sign and, from z15 and only when unclustered, the hatched approximate area of [ADR 0017](../adr/0017-map-cartography-style.md) (45° ink hatching, 10 px spacing, no outline). Below z15 only the smaller sign shows. An approximate line or polygon is drawn normally and its approximation is stated in words.
- **Sites and Areas on Explore.** Areas show only as district labels (from the archive's Areas, [ADR 0017](../adr/0017-map-cartography-style.md)), with no outlines. A Site shows its name as a focusable, linked label from z16 at the centroid of its Locations, in Goudy small caps distinct from district labels, with no hull drawn. There are no layer toggles.
- **Area, Site, and Series pages** ([Archive records](archive-records.md)): on Area and Site pages the map fits the record's extent and shows only its Locations; an Area page also draws the Area as a thin continuous `map.ink` outline with no fill.

### Selection and the side panel

- Selecting a sign (click, Enter, Space) opens a **side panel** on desktop and a **bottom sheet** on mobile, never a popup anchored to the marker. Focus moves to the panel title. Esc or "Close" returns focus to the sign (or to the control that opened it).
- **Contents**: the Location header (Surface type, approximate notice with radius, Site, Areas) and a link to the Location page; then the **stratigraphy**: the matching Artworks in the stratigraphy order of [Archive records](archive-records.md) (chronological key of the Creation event, else of first documentation, most recent first), each as a [list entry](#list-entries) card. An Artwork that has left this Location through a correction of its Location field no longer appears.
- A line states filtered-out works: "2 more artworks on this surface don't match the filters".
- A Location with a single matching Artwork uses the same panel; selection never jumps straight to an Artwork page.
- The selection goes into the query string (`?luogo=<id>`), so a link reopens it and browser Back closes it.

### Map/list sync

From [#39](https://github.com/spippoli/tart/issues/39) point 8 and [#40](https://github.com/spippoli/tart/issues/40):

- The Explore list shows the matching Artworks of Locations **in the viewport**. It updates when map movement ends, resets to page 1, and a polite live region announces the total and page ("32 artworks in this area · page 1 of 2").
- The viewport goes into the URL as `?mappa=<z>/<lat>/<lon>` via `replaceState` when movement ends. Without it, the view is set by [Filters and the viewport](#filters-and-the-explore-viewport).
- **List to map.** Each entry's "Show on map" button selects the Location, centres it if needed, and opens the panel with focus on its title, exactly as selecting the sign does; Esc or "Close" returns focus to that button. On mobile it first switches from List to Map. In `/archivio` it is a link to Explore with `?luogo=…&mappa=…`. Without WebGL2 it is not rendered.
- **Map to list.** Visible entries of the selected Location get a "Selected" text label and a thick outline, so colour never carries the state alone. The list does not reorder, change page, scroll, or take focus; focus stays in the panel, whose stratigraphy is the complete set. Entries on other pages are not flagged. Closing the panel clears the label.
- Nothing happens on hover, anywhere.

### List entries

- One component serves the panel stratigraphy, the Explore list, and `/archivio`: thumbnail of the latest Documentation item; title or "Untitled"; Condition word and sign with the latest documentation date ([ADR 0015](../adr/0015-condition-and-uncertainty-presentation.md)); Attribution summary; and, in the two lists, a **"where" line**: the Site name if there is one, else the Area, plus an approximate-location notice when it applies.
- Entries are flat, one per Artwork. Several Artworks on one Location are separate entries with the same "where" line.
- Two distinct controls: the **title links to the Artwork page**; the **"Show on map" button** (accessible name "Show on map: <title>") behaves as in [Map/list sync](#maplist-sync).
- **Pagination**: numbered, 24 entries per page, previous/next links and page numbers, the same in Explore and `/archivio`. On Explore, every viewport change resets to page 1, and the page number is not in the URL. No infinite scroll, no "load more", no cap.

### Focus order and landmarks (desktop)

- DOM order: filter bar → map (control, legend, signs) → list.
- A skip link before the map, visible on focus, reads "Skip the map: go to the list (32 artworks)"; a matching "Back to the map" link sits before the list.
- Map and list are two named `region` landmarks ("Map", "Artwork list").
- Signs stay individually focusable; no roving-tabindex map widget.

### Map controls, legend, attribution

- **Pan and zoom without dragging** (WCAG 2.5.7, [ADR 0017](../adr/0017-map-cartography-style.md)): one control with zoom in/out, four pan buttons (a third of the view each), and a button back to the Instance's default view, replacing MapLibre's `NavigationControl`. Keyboard navigation of the map remains. Rotation and pitch are disabled. Under `prefers-reduced-motion` every move is instant.
- **Legend**: a "Legend" disclosure button in the map control (never on hover) shows the three Condition signs, the stack, the cluster circle, and the approximate hatch, each drawn from the Instance style with one translated line of text. The Condition signs link to the Condition group filter. It is open on the first visit and closed afterwards, remembered in `localStorage` as a convenience only (it renders correctly when storage is unavailable).
- **Attribution** ([ADR 0016](../adr/0016-licence-policy-for-map-assets-and-data.md)): a MapLibre AttributionControl in a map corner renders the configured `{text, url}` entries as links. It may collapse after interaction, but its toggle stays keyboard-reachable and labelled. The attribution text is configuration content and is not translated; only the toggle label is. Courtesy credits (Protomaps, MapLibre, fonts) are not on the map; they appear on About TART from the asset manifest ([Foundations](foundations.md)).
- **Theme**: the map uses `map/style.light.json` or `map/style.dark.json` with the UI theme, switched with `setStyle` when the theme changes.

### Mini-map

On Artwork and Location pages ([Archive records](archive-records.md), answering its open item 20):

- Framed on the Location at z17, or on the geometry's extent if larger. The record's Location is highlighted, nearby Locations are muted; no clustering and no panel.
- Static by default: no wheel or drag pan/zoom, only the zoom buttons of the map control, plus an "Open on the map" link to Explore with `?luogo=…&mappa=…`.
- **Without WebGL2** there is no server-rendered image. A text box takes its place: Location, Areas, Site, approximate notice ([Archive records](archive-records.md) acceptance criterion 30), coordinates, and an "Open in a maps app" link with a `geo:` URI.

### Explore without WebGL2 or JavaScript

- SSR always renders the list, so every view works without JavaScript. Detection runs on the client: a `getContext('webgl2')` probe plus MapLibre's error event. A style that fails to load is treated the same way ([ADR 0009](../adr/0009-instance-configuration-as-validated-files.md)).
- Without WebGL2, `/it/` renders the **Archive view in place**: filters only, paginated, no viewport, no redirect, so shared URLs keep working.
- A persistent, non-dismissible text notice (not an alert) sits above it: "The map isn't available on this browser or device because it needs WebGL2. You can browse the whole archive from the list." Its "Why?" link leads to a short help entry (enable hardware acceleration, update the browser).
- The Map/List switch omits "Map" rather than showing it disabled. `?mappa=` is ignored. `?luogo=<id>` shows a notice ("You opened a link to a location on the map") linking to the Location page.
- With JavaScript and WebGL2, desktop keeps the list beside the map; on mobile the Map view becomes the initial view after hydration.

### Search

From [#41](https://github.com/spippoli/tart/issues/41):

- **Only public, approved content** is searchable or filterable. Excluded: pending content, withdrawn records and Documentation items, Attributions hidden by a withdrawn Artist ([ADR 0014](../adr/0014-artist-records-hold-only-a-public-identity.md)), redacted Revision values, and merged duplicates.
- **Results are Artworks only**, reached through related records. An Artwork matches `q` on its title, its description, the name or an Alias of an attributed Artist, or the name of its Series, its Site, or one of its Areas. Sources, Documentation items, and History event notes are not searched.
- **"Also matching"**: above the results, in both views, a compact box links directly to Artists, Sites, Areas, and Series whose name or Alias matches `q`.
- **Engine**: PostgreSQL only.
  - Names (titles, Artist names, Aliases, Site, Area, and Series names): `unaccent` plus trigram similarity (`pg_trgm`), tolerant of typos and prefixes, no stemming.
  - Free text (descriptions): `tsvector` with the stemming configuration of the **Content language**, derived from its code (`it` → `italian`), falling back to `simple`. No configuration key.
  - The UI language never affects search: `/en/archive?q=muro` returns exactly what `/it/archivio?q=muro` returns.

### Filters

All filters live in the shared query-string state and apply to Artworks ([ADR 0019](../adr/0019-map-shows-locations-not-artworks.md)).

| Filter | Values | Notes |
|---|---|---|
| Condition group | present, disappeared, unknown; all on by default | Drill-down to the single **Condition** (filters are where covered differs from destroyed, [ADR 0015](../adr/0015-condition-and-uncertainty-presentation.md)) |
| Expression type | Multi-select from the vocabulary | `retired` entries stay filterable |
| Area | Multi-select from the Areas index | Membership by geometry; Areas may overlap |
| Attribution | "Unknown artist" / "Attributed" (`confirmed` or `probable`) / "Disputed" | |
| Artist | Link-driven only | From "Show on the map" on an Artist page (`/it/?artista=<id>`); shown as a removable chip; no picker |
| Series | Link-driven only | As Artist, from a Series page |
| Documented between | Year from/to, either end open | Any Observed date of a public Documentation item |
| Created between | Year from/to, either end open | The Creation event; Artworks without one are excluded and a notice says "N artworks without a creation date are not included" |

- **Date matching** is by overlap of the Uncertain date's stored earliest–latest range with the filter range: `c. 2016` (2015–2017) matches "from 2017"; `before 2012` matches any range reaching back to 2012 or earlier. There is no "disappeared between" filter.
- **Combination**: OR within a filter, AND across filters. Map and list show the same set; the Explore list further restricts it to the viewport.
- **No per-option counts**; only the total, announced by the live region.
- **Not filterable**: Evidence level, approximate Location, Surface type, Site (a Site has its own page with a map).

### Ordering

- No view counts, clicks, or any engagement signal, ever.
- **Without `q`**: default "Most recently documented". Also selectable: "First documented" (oldest first), "Recently added to the archive" (approval date of the Artwork's first Revision), and "Title A–Z" ("Untitled" last).
- **With `q`**: default textual relevance (full-text rank plus name similarity). The other orders stay selectable.
- **Uncertain-date sort key**: the chronological key of [Archive records](archive-records.md) (midpoint of the entered values, ignoring `circa` widening), then id; it is never the stored range. "Most recently documented" sorts by the key of last documentation descending, "First documented" by the key of first documentation ascending. Artworks whose only Observed dates are `unknown` sort last in both directions. The final id tie-break keeps pages stable ([History event types and Uncertain-date ordering](https://github.com/spippoli/tart/issues/89)).
- The Explore list uses the same ordering as the Archive view, never distance from the map centre.
- The order lives in the query string (`?ordine=`).

### Applying filters

- The filters are a GET form with a "Show results" button, so they work without JavaScript.
- **Desktop, with JavaScript**: each change applies immediately; the text field updates after a 300 ms pause. The URL updates with `replaceState` and the live region announces the total. A result update is not a change of context (WCAG 3.2.2).
- **Mobile**: a "Filters (3 active)" button opens a full-screen dialog. Changes apply on "Show results", and focus returns to the button.
- Active filters always appear above the results as removable chips, with accessible names like "Remove filter: Area Ostiense", and a "Clear all filters" action.

### Filters and the Explore viewport

- A URL with filters but no `?mappa=` (for example from an Artist page) opens fitted to the results' extent, clamped to the Instance boundary. With no filters and no `?mappa=`, the Instance's default view applies ([ADR 0009](../adr/0009-instance-configuration-as-validated-files.md)).
- Changing a filter on the map does not move it. If the viewport empties, the empty state below applies.
- **Exception: Area.** Selecting Areas fits the map to their extent, because the intent is geographic.

### Empty states

- **No results**: "No artworks match these filters", followed by the active filters as removable chips and "Clear all filters". With a `q`, "Search the whole archive" keeps `q` and drops the other filters.
- **Explore, nothing in the viewport but matches elsewhere**: "No artworks in this part of the map. N in the whole archive", with "Widen the view" (fits the map to the results) and a link to the Archive view.
- **Empty archive**: see [Explore and Archive views](#explore-and-archive-views).

### Index name filter

The Artists, Sites, Areas, and Series indexes each have a "Filter by name" field (name plus Aliases for Artists) using the name matching of [Search](#search), alphabetical order in the Content language, and pagination by 24. This answers [Archive records](archive-records.md#open-items) open item 18 for the indexes.

### Query-string keys

- Keys are localized like path segments ([ADR 0010](../adr/0010-public-url-scheme.md)): `?ordine=`/`?sort=`, `?artista=`/`?artist=`, and so on, including `luogo` and `mappa`. The language switcher remaps them.
- **Values are always stable**: vocabulary keys, ids, enum values, never translated labels.
- Key names are UI strings and may change before launch.

### Location entry without the map

From [#40](https://github.com/spippoli/tart/issues/40) point 6, amending [#27](https://github.com/spippoli/tart/issues/27) decision 6. The Location step of the editor (Contribution and moderation) offers:

- **Choose an existing Location** from a text list, searched by Site, Area, or text, or among Locations near entered coordinates.
- **Coordinates field**, accepting decimal (`41.8986, 12.4769`), degrees-minutes-seconds, a `geo:` URI, or a pasted OpenStreetMap or Google Maps link, and confirming the parsed point in text ("41.8986 N, 12.4769 E, <Area>"). It is **always available**, also with the map, as a third mode beside click drawing and the crosshair. Points outside the Instance boundary are rejected with a text message.
- **"Use my current position"** (Geolocation API), with an explicit reminder that the Location is the artwork's position, not the Submitter's. Nothing about the Submitter's position is stored.
- **No geocoding or address search.** Parsing coordinates out of a pasted link is not geocoding, and nothing derived from OSM is stored ([ADR 0016](../adr/0016-licence-policy-for-map-assets-and-data.md)).
- Without the map, only a **Point** can be entered, with the optional uncertainty radius. For a line or polygon the form explains that drawing needs the map, suggests a representative point with the extent described in the note to Moderators, and notes that the geometry can later be refined by a separate Submission on that Location.
- The duplicate warning works unchanged, computed server-side from the coordinates and shown as a text list with the "add documentation" exit.

### Cartography

The platform ships the reference style of [ADR 0017](../adr/0017-map-cartography-style.md); its rules, typography, layer order, and draft tokens are normative there and are not restated. In short: the tinted early-1900s plan; no dashed, dotted, chequered, or hatched basemap lines or fills; rail as a thin continuous ink line with service and yard tracks hidden below z15; one block tint for all buildings; Rome walls and archaeology from an OSM overlay (walls as a heavy ink line, ruins and archaeological sites as outlines with italic names from z15.5); district labels from Areas in letter-spaced capitals at z12–16; Sorts Mill Goudy (Regular, Italic) through `font-faces`, Noto Sans for cluster counts and as glyph fallback; the city's name not on the map; the dark theme as an ink negative of the same tokens. Contrast: signs and the accent ≥ 3:1 against every map fill, labels ≥ 4.5:1 against their halo; re-run the checks whenever a token changes. MapLibre GL JS is pinned and the `font-faces` path tested with that version.

### Map style ownership and serving

From [#37](https://github.com/spippoli/tart/issues/37), recorded in [ADR 0009](../adr/0009-instance-configuration-as-validated-files.md):

- **Files**: `map/style.light.json` and `map/style.dark.json` at fixed paths in the configuration directory, both required. One style serves every UI language: basemap labels use local OSM names (`name`); no per-language style and no language state.
- **Archive layers** (Condition signs, stack, clusters, the approximate-area hatch, geometries from z17, Site labels, district labels from Areas, Area outlines on Area pages) belong to the platform. The map module inserts them below the layer named by `metadata.tart:insert-archive-below` and styles them from `metadata.tart:tokens`.
- **Assets**: fonts, glyphs, sprites, and overlay GeoJSON live under `map/` in the configuration directory; the PMTiles file lives in the data volume. The style uses root-relative paths; the API serves the style from a fixed endpoint, rewriting those paths to absolute URLs from the public base URL, and the symbolic basemap URL to the current extract ([Basemap tiles](#basemap-tiles)).
- **Validation** (Python, at startup and in `tart config check`; any failure stops startup like any configuration error):
  - light/dark parity of sources and layer ids;
  - `metadata.tart:insert-archive-below` and `metadata.tart:tokens` present, and the insertion layer exists; `metadata.tart:basemap-schema` present when the style uses the local basemap;
  - `line-dasharray`, `fill-pattern`, and `line-pattern` banned;
  - every asset path root-relative under a known prefix and pointing to an existing file; each overlay GeoJSON at most 1 MB;
  - every other source URL either the symbolic basemap URL or absolute `https`;
  - every colour literal in `background-color` and `fill-color`, including inside expressions, at ≥ 3:1 against the theme's accent and `marker.ink`; non-literal fill colours rejected;
  - `text-color` at ≥ 4.5:1 against `text-halo-color` in every symbol layer.
- **Spec conformance**: `gl-style-validate` runs in CI (the platform's CI for the reference style, and a template workflow for an Instance configuration repository). The `api` image gets no Node. A style that still fails to load in the browser sends it to the list view.
- **Accent**: a light and a dark value in `instance.toml`, each checked against its own theme's UI backgrounds and map fills ([Foundations](foundations.md)).

### Basemap tiles

From [#38](https://github.com/spippoli/tart/issues/38), recorded in [ADR 0009](../adr/0009-instance-configuration-as-validated-files.md):

- **Command**: `tart tiles update` in the Operator CLI, in the `api` image, which bundles the go-pmtiles binary (BSD-3, a separate program under [ADR 0011](../adr/0011-provisional-software-license.md)'s tiers). It reads the boundary from the configuration directory, extracts, checks the header, and swaps the file in.
- **Area**: the Instance boundary buffered by **2 km** (platform constant), passed as `--region`.
- **Source and build**: the latest Protomaps daily build by default, or `--build YYYYMMDD`; `--source` points to a mirror.
- **Schema pinning**: the style declares `metadata.tart:basemap-schema` (the Protomaps major, `4` today). The command refuses an extract whose header major differs. Moving to a new major is deliberate: regenerate the style, bump the key, extract.
- **Atomic swap**: versioned files `basemap-YYYYMMDD.pmtiles` in the data volume, plus a small manifest written atomically (current file, build date, schema version, boundary hash). The command keeps the previous file for open pages and deletes older ones. A failed extraction leaves the current file in place.
- **Serving**: the style refers to the local basemap as `pmtiles:///tiles/basemap.pmtiles`; the API rewrites it to the current file when serving the style. Caddy serves `/tiles/` with byte ranges, no `encode`, and `Cache-Control: immutable`.
- **Cadence**: manual only, at installation and whenever the Operator chooses; the Operator documentation suggests every six months and after any boundary change.
- **Startup checks** (warnings, never blocking): the extract is missing; the boundary hash differs from the one in the manifest; the manifest's schema major differs from the style's. Without tiles the map does not appear, and list and search work.
- **External tiles**: a style source may be an absolute `https` URL (vector, raster, or `pmtiles://https://…`). The platform adds its origin to the Content-Security-Policy; manifest and schema checks do not apply. Rome uses the local file.

### Overlays

- The Instance configuration repository holds each overlay GeoJSON under `map/`, together with the Overpass QL query that produces it and a README with the command (Overpass API plus `osmtogeojson`, MIT). The Operator regenerates and commits it by hand, which meets the ODbL "method to recreate" duty ([ADR 0016](../adr/0016-licence-policy-for-map-assets-and-data.md)). There is no platform command.
- Rome's overlay: `historic=city_walls`, `archaeological_site`, and `ruins` within the boundary.
- Overlays are drawn by the Instance style, below the archive layers. They never flow into archive data.

## Testing Decisions

A good test drives a module through its external interface and asserts observable behaviour (the returned set, the rendered page, the URL, what assistive technology is told), never internal calls. Prior art: the Foundations configuration loader's fixtures (one valid directory, one directory per failure) and its CLI tests. The throwaway prototype on `prototype/36-map-cartography` shows the intended style; it is not a fixture.

- **Discovery query (integration, pytest against PostgreSQL with PostGIS, `unaccent`, `pg_trgm`)**: sign priority and per-group counts per Location under filters; the stack count; clusters' inputs; public-only exclusions (pending, withdrawn, hidden Attributions, redacted values, merged duplicates); OR within / AND across; date overlap cases (`c. 2016` vs "from 2017", `before 2012`), the "without a creation date" count; Area membership by geometry with overlapping Areas; retired Expression types; each ordering, including `unknown` last and stable pages; viewport restriction. Fixtures are fictional records marked as fictional, with no claims about real artworks or artists.
- **Search (integration)**: name matching with accents and typos; Italian stemming of descriptions; `/en/` and `/it/` returning identical results; "Also matching" contents; Sources and Documentation items not searched.
- **Map style validation (unit, pytest)**: the reference style passes in both themes; one failing style per rule (parity, missing metadata, missing insertion layer, `line-dasharray`, missing asset, overlay over 1 MB, non-`https` source, low-contrast fill, non-literal fill, low label contrast); style serving rewrites assets and the symbolic URL.
- **Tile pipeline (integration)**: with a stubbed go-pmtiles and fixture extracts: a successful swap writes the manifest and keeps one previous file; a schema-major mismatch is refused; a failed extraction keeps the current file; startup warnings for a missing extract, a changed boundary, and a schema mismatch.
- **Filter state and coordinates parser (unit, vitest)**: round-trip of every key in each UI language, remapping on language switch, stable values; each coordinate format, out-of-boundary rejection.
- **Pages (end to end, Playwright with axe)**, in both UI languages, desktop and mobile viewports: Explore and Archive with filters, chips, pagination, and empty states; keyboard-only selection of signs and clusters, panel focus and return, skip links; the "Show on map" flow both ways; the URL reopening a selection and viewport; Explore and record pages with WebGL2 disabled; JavaScript disabled; reduced motion. The map canvas is not pixel-tested; contrast is tested on the style.
- **i18n**: the missing-key check covers every string of this spec, including accessible names, live-region announcements, and query-string keys.

## Acceptance criteria

**Map**
1. Explore draws exactly one sign per Location that has at least one matching public Artwork, and none for a Location without.
2. A Location's sign is solid if any matching Artwork is *present*, else dotted if any is *unknown*, else dashed; its accessible name states the counts per Condition group.
3. A Location with more than one matching Artwork shows the stack outline; with one, it does not.
4. Disappeared Artworks appear by default; turning off the *disappeared* Condition group hides them from map and list alike.
5. Up to z16 Locations cluster (radius about 50 px) into neutral circles showing the number of matching Artworks; from z17 there are no clusters. Clusters are focusable, named as specified, and Enter, Space, or click zooms to the expansion zoom.
6. From z17 lines and polygons draw their geometry in `marker.ink`, continuous, dashed, or dotted by prevailing group, polygons without fill; below z17 only signs are drawn.
7. Every sign's target is at least 24×24 px, and each Location has exactly one focusable element.
8. An approximate point shows a smaller sign and, from z15 when unclustered, the hatched area; an approximate line or polygon states its approximation in words.
9. Selecting a sign opens the side panel (bottom sheet on mobile) with focus on its title, the Location header, the stratigraphy of matching Artworks, the count of non-matching ones, and a link to the Location page; Esc or "Close" returns focus to the opener.
10. `?luogo=<id>` reopens the panel; browser Back closes it. `?mappa=<z>/<lat>/<lon>` is written with `replaceState` when movement ends and restores the view.
11. Site names appear as focusable linked labels from z16; Areas appear only as district labels on Explore and as a continuous outline on their own page; there are no layer toggles.
12. The map control offers zoom ±, four pan buttons, and a reset to the default view; rotation and pitch are disabled; with reduced motion, moves are instant.
13. The legend is a disclosure button that is open on the first visit, shows the three signs, stack, cluster, and hatch with translated text, and works when `localStorage` is unavailable.
14. The configured attribution entries are shown as links in a keyboard-reachable AttributionControl, untranslated; only the toggle label is translated.
15. The map follows the UI theme, switching style without reload.

**List and sync**
16. The Explore list shows the matching Artworks of Locations in the viewport, 24 per page, reset to page 1 and announced ("N artworks in this area · page X of Y") when movement ends; the page number is not in the URL.
17. The Archive view ignores the viewport, is paginated by 24, and shares the filter state; switching views keeps filters and drops the viewport.
18. Each entry has a title link to the Artwork page and a separate "Show on map: <title>" button that selects and centres the Location and opens the panel; in `/archivio` it links to Explore with `?luogo=…&mappa=…`.
19. Entries of the selected Location show a "Selected" text label and a thick outline; the list does not reorder, change page, scroll, or take focus.
20. Hover triggers nothing on the map or the list.
21. A skip link before the map leads to the list and a "Back to the map" link returns; map and list are named `region` landmarks; DOM order is filter bar, map, list.

**Search and filters**
22. Search and filters return only public, approved content and exclude everything listed in [Search](#search).
23. `q` matches an Artwork on its title, description, attributed Artist names and Aliases, and its Series, Site, and Area names, tolerating accents and typos; Sources, Documentation items, and History event notes are not searched.
24. The same `q` returns the same results in every UI language.
25. The "Also matching" box links to Artists, Sites, Areas, and Series whose name or Alias matches.
26. Filters combine OR within and AND across; there are no per-option counts.
27. Date filters match by overlap of stored ranges, and "Created between" states how many Artworks without a creation date were left out.
28. Retired Expression types remain filterable; Artist and Series filters arrive only by link and show as removable chips.
29. The default order is "Most recently documented" without `q` and relevance with `q`; no ordering uses views, clicks, or any engagement signal; `unknown` precision sorts last and ties break by id.
30. The filter form works without JavaScript; with JavaScript, desktop applies changes immediately (text after 300 ms) without moving focus and announces the total; mobile applies on "Show results" and returns focus to the "Filters" button.
31. Every active filter appears as a removable chip with an accessible name; "Clear all filters" is always offered with active filters.
32. A filtered URL without `?mappa=` opens fitted to the results, clamped to the boundary; changing a filter other than Area does not move the map; selecting Areas fits to their extent.
33. The no-results, empty-viewport, and empty-archive states show the texts and exits specified; in the empty archive the filter bar and search are hidden.
34. On Explore and Archive the header search field is absent; elsewhere it submits to the Archive view with `?q=`. There is no autocomplete.
35. Query-string keys are localized per UI language and remapped by the language switcher; values are never translated labels.
36. Each index offers a "Filter by name" field, alphabetical in the Content language, 24 per page.

**Without WebGL2, JavaScript, or tiles**
37. Without WebGL2, `/it/` renders the Archive view in place, with the persistent notice and its "Why?" link, no "Map" option in the switch, `?mappa=` ignored, and a notice linking to the Location page when `?luogo=` is present.
38. Without JavaScript, Explore renders the list and every filter works through the form.
39. Without WebGL2, record pages replace the mini-map with the text box (Location, Areas, Site, approximate notice, coordinates, `geo:` link).
40. A style that fails to load, or a missing tile extract, leaves list and search fully working.

**Mini-map**
41. The mini-map frames the Location at z17 (or its larger extent), highlights it, mutes neighbours, has no clustering, panel, wheel, or drag zoom, and links to Explore with `?luogo=…&mappa=…`.

**Location entry**
42. The editor's coordinates field accepts all four input forms, confirms the point in words, and rejects points outside the boundary with a text message; it is available with and without the map.
43. Without the map, a contributor can choose an existing Location, enter coordinates, or use the device position (with the reminder), and can enter only a Point; the duplicate warning appears as a text list.

**Style and tiles**
44. Startup and `tart config check` reject a style violating any rule of [Map style ownership and serving](#map-style-ownership-and-serving), reporting every error.
45. The served style has absolute asset URLs and the symbolic basemap URL replaced by the current extract.
46. `tart tiles update` extracts the boundary plus 2 km, refuses a schema-major mismatch, swaps atomically with a manifest, keeps the previous file, and leaves the current file in place on failure.
47. Startup warns, without stopping, on a missing extract, a changed boundary, or a schema mismatch.
48. An external `https` tile origin is added to the Content-Security-Policy.

**Accessibility and i18n**
49. Explore, Archive, the indexes, and record-page maps pass axe with no WCAG 2.2 AA violations in every enabled UI language, by keyboard alone; status (Condition, selection, active filters) is never conveyed by colour alone.
50. Every user-facing string of this spec (labels, accessible names, live-region texts, notices, empty states, legend lines, query keys) comes from the i18n catalogue; dates and counts are formatted with `Intl` in the UI language; content keeps its Content-language `lang`.

## Instance configuration

Exact key names in `instance.toml` belong to [Foundations](foundations.md), which owns it; the map files have fixed paths.

| Setting | Use here | Rome |
|---|---|---|
| Boundary polygon (GeoJSON) | Bounds the map; tile extract area (+2 km); rejects coordinates outside it; clamps "fit to results" | Not decided |
| Default map view | Explore with no filters and no `?mappa=`; the reset-view button | Not decided |
| Content language | Full-text stemming configuration; alphabetical order of indexes | `it` (`italian`) |
| Enabled UI languages | Localized path segments and query-string keys; labels | `it` (default), `en` |
| Accent (light and dark) | Marker accent; validated against map fills and UI backgrounds | Not decided |
| `map/style.light.json`, `map/style.dark.json` | The two finished styles | The [ADR 0017](../adr/0017-map-cartography-style.md) reference style |
| `metadata.tart:insert-archive-below` | Insertion point of archive layers | From the reference style |
| `metadata.tart:tokens` | Colours of archive layers (e.g. `marker.ink`, `map.ink`) | [ADR 0017](../adr/0017-map-cartography-style.md) draft tokens |
| `metadata.tart:basemap-schema` | Protomaps major for the local basemap | `4` |
| Fonts, glyphs, sprites under `map/` | Style assets | Sorts Mill Goudy (Regular, Italic), Noto Sans |
| Overlay GeoJSON, Overpass query, README under `map/` | Instance overlays (≤ 1 MB each) | City walls, archaeological sites, ruins |
| Map attribution (`{text, url}` list, non-empty) | AttributionControl | `© OpenStreetMap` → `https://www.openstreetmap.org/copyright` |
| Expression type vocabulary | Filter options and labels | Starting from the brief's §9 list |
| Tile source | Local extract or external `https` | Local extract |

Environment: the public base URL (style rewriting) and the PMTiles volume path ([ADR 0009](../adr/0009-instance-configuration-as-validated-files.md)).

**Platform constants, not configuration**: the 2 km extract buffer; cluster radius (about 50 px) and maximum zoom (z16); geometries from z17; hatch from z15; Site labels from z16; district labels z12–16; mini-map zoom z17; minimum target 24×24 px; page size 24; filter text pause 300 ms; overlay limit 1 MB.

## Out of Scope

- Geocoding and address search, for discovery and for Location entry, and any snapping to OSM geometries ([ADR 0016](../adr/0016-licence-policy-for-map-assets-and-data.md), [#40](https://github.com/spippoli/tart/issues/40)).
- Layer toggles, map rotation and pitch, and per-language basemap styles.
- Autocomplete in search fields; per-option filter counts; infinite scroll or "load more".
- Any popularity or engagement signal in ordering, maps, or lists.
- Filters on Evidence level, approximate Location, Surface type, Site, and "disappeared between".
- Searching Sources, Documentation items, and History event notes.
- Server-rendered static map images.
- A platform command for overlays, and automatic tile refresh.
- A theme-to-style generator: the Instance ships finished style files ([ADR 0009](../adr/0009-instance-configuration-as-validated-files.md)).
- UI design tokens beyond the map's cartography ([spec index](index.md#out-of-scope-for-the-mvp)).
- Showing pending Submissions on the map or in lists.

## Further Notes

Not normative.

### Open items

The inputs leave these questions unsettled. Implementers must not fill them by assumption; each needs a decision (a resolution comment or an ADR) before the affected ticket is built.

**Rome values**
1. **Boundary polygon and default map view** for Rome are not decided ([Foundations open item 2](foundations.md#open-items)); the tile extract and every "fit" depend on them.
2. **Rome's accent colour** (light and dark) is not decided; ADR 0017 gives only examples.

**Map**
3. **Representative point.** Clusters, signs of lines and polygons, and Site labels use a Location's "representative point"; how it is computed (centroid, point on surface) and whether it is stored is not decided.
4. **Approximate point without a radius.** The uncertainty radius is optional; the size of the hatched area when an approximate point has none is not decided. The size of the "smaller sign" is not fixed either.
5. **Archive-layer tokens and fonts.** `metadata.tart:tokens` is required, but the exact token list the platform reads (beyond `marker.ink`, `map.ink`, and the accent) is not decided, nor whether the accent comes from `instance.toml` or the tokens when they disagree. Platform layers use Goudy (district and Site labels, small caps) and Noto Sans (cluster counts), which an Instance style supplies under `map/`; what happens when an Instance style lacks them is not decided.
6. **The "?" in the *unknown* sign.** The dotted sign needs a stronger differentiator ([ADR 0015](../adr/0015-condition-and-uncertainty-presentation.md)); it stays a drawing task.
7. **Stratigraphy order under uncertain dates.** Answered by [History event types and Uncertain-date ordering](https://github.com/spippoli/tart/issues/89): chronological key of the Creation event, else first documentation, most recent first; see Selection and the side panel.
8. **`?luogo=` edge cases.** A link to a Location that has no matching Artwork under the current filters, that is withdrawn, or that does not exist: what the map shows is not decided.
9. **Map bounds.** "The boundary also bounds the map" ([ADR 0009](../adr/0009-instance-configuration-as-validated-files.md)); whether panning is limited to the boundary, the extract (+2 km), or a bounding box, and the minimum and maximum zoom, are not decided.
10. **Series page map.** [#39](https://github.com/spippoli/tart/issues/39) fixes the map of Area and Site pages; the Series page map (fit to its Artworks' Locations, presumably) is not stated.
11. **Mini-map neighbours.** How far "nearby Locations" reach on the mini-map, and whether they respect any filter, is not decided.
12. **"Near me" on Explore.** The brief asks for discovering nearby works; the device-position button is decided only for the editor. Whether Explore offers "centre on my position" is not decided.
13. **Loading and failure states.** The brief (§21) lists loading and network failure; no decision fixes what the map and list show while loading or when the Discovery query fails.
14. **Scale of the single GeoJSON response.** All filtered Locations come in one response with no viewport paging; there is no decided size threshold or caching policy if the archive grows large.

**Search and filters**
15. **Full key table.** Only `ordine`/`sort`, `artista`/`artist`, `luogo`, `mappa`, and `q` are named; the English keys for `luogo` and `mappa`, the Series key, the keys of the other filters, and whether `q` is localized are not decided.
16. **Relevance formula and thresholds.** How full-text rank and name similarity are combined, and the trigram similarity threshold, are not decided.
17. **"First documented" sort key.** Answered by [History event types and Uncertain-date ordering](https://github.com/spippoli/tart/issues/89): one chronological key in both directions; see Ordering.
18. **Artworks with no public Documentation item** (for example after a Withdrawal): their place in "documented" orderings, their thumbnail, and "Documented between" are not decided. The brief's "missing images" state for list entries whose latest Documentation item is not an image (PDF, text, link) is also not decided.
19. **Condition drill-down semantics.** How a group and individual Conditions coexist in the state (e.g. group *disappeared* with only *covered* selected) is not detailed.
20. **"Also matching" size.** How many records the box shows, and in which order, is not decided.
21. **Availability of documentation.** The brief (§18) lists it as a search criterion; the decisions neither include nor exclude it.
22. **Range derivation.** Answered by [History event types and Uncertain-date ordering](https://github.com/spippoli/tart/issues/89): see [Archive records](archive-records.md), Uncertain date; an open bound overlaps everything on its side.

**Style and tiles**
23. **Style endpoint path** and its caching are not decided.
24. **How the frontend learns that tiles are missing.** Startup only warns; whether the style endpoint signals it, or the browser falls back on a tile error, is not decided.
25. **Theme selection.** The map follows the UI theme; whether that theme is `prefers-color-scheme` only or a toggle is [Foundations open item 23](foundations.md#open-items).

### Notes

- This spec answers [Archive records open item 20](archive-records.md#open-items) (mini-map fallback) and, for the indexes, open item 18 (index ordering). [Location entry without the map](#location-entry-without-the-map) answers [Contribution and moderation open item 18](contribution-and-moderation.md#open-items). Those specs mark the items as answered ([Apply decided answers across feature specs](https://github.com/spippoli/tart/issues/83)).
- Tiles are reproducible and stay out of backups; the manifest may be included ([#45](https://github.com/spippoli/tart/issues/45), Operations and portability). The compliance item for an external tile provider and the processing-inventory entry belong to Rights and legal actions and Operations and portability.
- Legal review items from [ADR 0016](../adr/0016-licence-policy-for-map-assets-and-data.md) §5 (font conversion and Reserved Font Names, OFL text with served glyphs, Locations drawn over an OSM basemap, overlay offer obligations, ODbL next to the Data licence) do not change behaviour here.
- The research measured a Rome Protomaps extract at about 47 MB for z0–15 ([#34](https://github.com/spippoli/tart/issues/34)); the Protomaps basemap has no city walls, archaeological sites, or ruins, hence the overlay.
- Sample data in tests and fixtures must be fictional and marked as such, with no claims about real artworks or artists; the prototype's markers and Areas are fictional.
