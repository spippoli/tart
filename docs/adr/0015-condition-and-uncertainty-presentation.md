# Condition, uncertainty, and review status are shown in words and three historical-map signs

The archive presents physical Condition, uncertainty, and pending Submissions with an editorial, text-first language and a historical-map symbology: three signs, one per Condition group, on every surface (map markers, cards, detail page, Timeline). A **solid square** marks a *present* Artwork, a **dashed square** a *disappeared* one, and a **dotted square** an *unknown* Condition, always next to the word for the exact Condition. An approximate Location is drawn as a hatched area with a smaller sign and no precise point. We chose this because it borrows a convention readers already know (on historical maps, demolished buildings are dashed), it keeps the interface restrained and archival, it never relies on color, and nine distinct Condition symbols would have to be learned from a legend. The decision came from a throwaway prototype (#17, branch `prototype/17-status-presentation`).

## Rules

- **Words carry the meaning, shape carries the group, color is redundant.** One accent color for *disappeared* and one for pending Submissions; both stay readable in grayscale.
- **Uncertainty is language, not alarm.** Uncertain dates read as `c. 2016`, `before 2012`, `2014–2015`. A probable Attribution reads as `[MRLN] — probable attribution`, a disputed one as `Disputed attribution: A or B`, and an Artwork without Attributions as `Unknown artist`. An approximate Location reads as `approximate location, within 40 m`. No warning icons and no red for uncertainty.
- **A Condition always has a date.** It is shown with the Observed date of its History event and the latest Documentation item (`Intact · last documented 12 Apr 2026`), never as a bare "current" state, together with its Evidence level (`documented · 2 sources` or `reported · no sources cited`).
- **Disappeared Artworks keep a full record**, showing their last Documentation item and its date.
- **Pending Submissions are never public.** Their Submitter and Moderators see the pending content inline in the list and Timeline, in a dashed, hatched box labelled as under review. It never changes the Condition shown until it is approved.
- **The Timeline shows the three dates** of each History event (observed, submitted, approved); cards show only the Condition and the latest documentation date.
- **Avoid**: traffic-light colors, colored badges, gradients, counters or popularity cues, and placeholders that assume colorful murals.

## Considered Options

- **Layouts**: photography-first (a contact-sheet grid where disappeared Artworks are shown in black and white with a ribbon) and a ledger (a table with explicit certainty and evidence columns and a to-scale Timeline). Both were rejected in favour of the editorial label, which keeps uncertainty readable without making the archive look unreliable.
- **Abstract geometry**: three group shapes on the map and nine abstract glyphs in text. It was compact, but the glyphs had to be learned.
- **Descriptive pictograms** for all nine Conditions, also inside map pins. They were readable without a legend, but needed larger pins that crowd a dense map, and a pictogram set must be professionally designed.

## Consequences

- The map does not tell covered from destroyed; the word, the detail page, and Condition filters do.
- At marker size and in grayscale, the dotted *unknown* sign is too close to the dashed *disappeared* sign; it needs a stronger differentiator (for example a "?" inside) when the design system is drawn.
- Still open: whether disappeared Artworks are shown on the map by default, and whether the public sees that a record has Submissions under review without seeing their content.
