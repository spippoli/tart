# Location is a shared physical surface, not an attribute of an Artwork

A Location is its own Archive record representing the physical surface (wall, façade, pole, pavement) an Artwork occupies, with point, line, or polygon geometry. Many Artworks can share one Location, side by side or in succession. We chose this over storing coordinates on each Artwork because urban art is layered: the same wall hosts successive overpaintings, and the archive must show that stratigraphy and keep the surface after every Artwork on it is gone.

## Considered Options

- **Coordinates on the Artwork**: simpler, but overpainting and demolition become ad-hoc links, and the record of a surface disappears with its last Artwork.
- **Location as the identity of the Artwork**: rejected because a Location can host several Artworks at once, and a wrongly entered Location must be correctable without changing the Artwork's identity.

## Consequences

- An Artwork's Location never changes for physical reasons; the Location field changes only to correct wrong data. A detached or moved piece gets a `removed` History event on its original Location, whose note and citations say where it went; if it reappears in another urban place, that is a new Artwork documented there (amended by [History event types and Uncertain-date ordering](https://github.com/spippoli/tart/issues/89); previously "Relocation is a History event that moves an Artwork between Locations").
- Locations have no Condition and are never deleted. Physical history belongs to Artworks only.
- Image Documentation items show a single Location; nearby Locations are grouped by Sites (by proximity) and Areas (by region), never by the Location itself.
