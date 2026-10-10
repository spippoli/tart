# Public URLs use a stable id with a cosmetic slug; Merge redirects and Withdrawal answers 410

Every public Archive record (Artwork, Artist, Location, Site, Area, Series, Source, Documentation item) has its own page at `/<ui-language>/<translated-kind>/<id>[-<slug>]`, for example `/it/opere/4821-lupa-capitolina-stencil` and `/en/artworks/4821-lupa-capitolina-stencil`. Only the id identifies the record. The slug is derived from the record's current name, ignored when the URL is resolved, and a wrong, missing, or outdated slug answers a 301 to the canonical URL. We chose this because these URLs are cited from outside the archive (articles, Sources, DSA notices), so they must survive Revisions. Many Artworks have no known title and titles change, which rules out slug-only URLs, while a bare id tells a reader nothing.

## Considered Options

- **Id only** (`/it/opere/4821`): stable, but unreadable in links and search results.
- **Slug only**: readable, but breaks or needs a redirect history whenever a title changes, and collides for the many untitled Artworks.

## Consequences

- After a Merge, the duplicate's id answers a 301 to the surviving record (ADR 0002), with redirects flattened so none chains. Its `/revisions` subpage still answers 200 and shows its own Revisions read-only (ADR 0018). A retired Documentation item redirects the same way.
- A withdrawn record or Documentation item answers 410 with a page that states it was removed for legal, rights, or privacy reasons and shows none of its content. Its Revisions subpage answers 410 too.
- Each record's Revisions (audit trail) live on a `/revisions` subpage (translated per UI language), never on the Timeline.
- Path segments are translated per UI language (ADR 0004, ADR 0008), so they are UI strings and may change before launch; ids never change.
