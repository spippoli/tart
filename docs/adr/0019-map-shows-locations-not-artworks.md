# The map shows Locations, not Artworks, and disappeared Artworks are shown by default

The Explore map draws one sign per Location (ADR 0003), never one per Artwork. Filters apply to Artworks: a Location appears when at least one of its Artworks matches, and its sign reflects only those. When the matching Artworks fall in different Condition groups, the sign follows the priority *present* > *unknown* > *disappeared*, so it answers "is there still something to see here?" and a surface whose works are all gone stays dashed, like a demolished building on a historical plan. A Location with more than one matching Artwork gets a second, offset outline behind its square (a stack), which announces the stratigraphy before it is opened. Disappeared Artworks are shown by default; a Condition group filter in the shared query string hides them. We chose this because the Location is the domain's spatial unit: overlapping markers disappear by construction instead of being managed, a façade with three works stays one geometry, and the map tells the layering the way the Location page does. Showing disappeared Artworks by default follows from "disappearance is never deletion": the map is an archive, not a guide to what can be seen today. The decision came from [Map behaviour: clustering, geometries, overlays, stratigraphy](https://github.com/spippoli/tart/issues/39).

## Considered Options

- **One sign per Artwork**: Condition reads directly, but five works on one wall need five offset or spiderfied markers, the stratigraphy is split, and a polygon is drawn once per Artwork.
- **Sign of the most recent Artwork**: ambiguous under uncertain dates, and a recent work of *unknown* Condition would hide an older one still intact.
- **A mixed sign** (half solid, half dashed): a fourth sign to learn, against ADR 0015.
- **Disappeared Artworks hidden by default**, or hidden below a zoom level: more useful to someone walking the city today, but it presents a "present-only" archive by default, and zoom-dependent hiding changes cluster counts as the user zooms.

## Consequences

- Clusters group Locations but count Artworks; a cluster is a neutral circle, never a Condition sign.
- The sign of a Location changes with the active filters; its accessible name states the counts per group (e.g. "Location, 3 artworks: 1 present, 2 disappeared").
- Selecting a sign opens the Location's stratigraphy, not an Artwork page, even when only one Artwork matches.
