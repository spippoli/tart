# Archive records

Feature spec 2 of the [TART MVP specification](index.md). It defines the authoritative archive: the **Archive record** kinds (**Artwork**, **Artist**, **Location**, **Site**, **Area**, **Series**, **Source**, **Documentation item**), the physical history of Artworks, the audit trail of **Revisions**, and the public pages that show them. Compile ticket: [Compile Archive records spec](https://github.com/spippoli/tart/issues/51).

Every section except Further Notes is normative. The invariants, language rules, and implementation principles in [`CLAUDE.md`](../../CLAUDE.md) apply and override any reading of this spec that contradicts them. Terms in **bold** are [glossary](../../GLOSSARY.md) terms and carry exactly that meaning.

## References

**ADRs applied**

| ADR | What this spec takes from it |
|---|---|
| [0001](../adr/0001-one-instance-per-deployment.md) | Records are local to one Instance; no cross-Instance Artist |
| [0002](../adr/0002-every-change-is-a-submission.md) | Records change only through approved Submissions; one Revision per touched record; Withdrawal produces no Revision |
| [0003](../adr/0003-location-as-shared-physical-surface.md) | Location as a shared surface; an Artwork's Location changes only by correction, a detached piece is `removed` (amended by #89); Locations have no Condition and are never deleted |
| [0006](../adr/0006-derived-evidence-level.md) | Evidence level derived from citations on Claims; record-level citations are background |
| [0007](../adr/0007-edit-submissions-as-field-changesets.md) | The field and item structure that edit changesets address |
| [0008](../adr/0008-single-content-language-and-prefixed-ui-languages.md) | Content rendered in the Content language with its own `lang`; dates through `Intl`; one message per Uncertain date precision × qualifier |
| [0009](../adr/0009-instance-configuration-as-validated-files.md) | Open vocabularies (Expression type, Surface type) with `retired`; closed vocabularies in the platform; Areas are archive data |
| [0010](../adr/0010-public-url-scheme.md) | Record URLs, slug redirects, 301 after Merge, 410 after Withdrawal, `/revisions` subpages |
| [0012](../adr/0012-per-file-licence-with-rights-basis.md) | Per-file licence, Creator credit, Rights basis; "covers the file only"; capped public renditions; no EXIF in public renditions |
| [0013](../adr/0013-hide-not-delete-for-legal-removals.md) | Withdrawal and Redaction hide content; Notices can be sent from every public record and Documentation item page |
| [0014](../adr/0014-artist-records-hold-only-a-public-identity.md) | Artist content rules; no User–Artist link; no legality data; withdrawn Artist hides its Attributions and Crew memberships |
| [0015](../adr/0015-condition-and-uncertainty-presentation.md) | Words plus three signs for Condition groups; uncertainty as language; dated Condition; three dates per History event; pending content never public |
| [0018](../adr/0018-merge-as-reconciling-multi-record-submission.md) | Merged duplicate keeps a readable `/revisions` subpage; Duplicate retirement redirects |

**Glossary terms applied**: Instance, Content language, UI language, Instance configuration, Data licence, Artwork, Expression type, Location, Surface type, Site, Area, Series, Documentation item, Creator credit, Rights basis, Condition, Missing, Condition group, History event, Condition record, Creation event, Timeline, Uncertain date, Observed date, Claim, Source, Evidence level, Artist, Alias, Crew membership, Attribution, User, Moderator, Submitter, Submission, Archive record, Revision, Merge, Withdrawal, Redaction, Reinstatement, Notice.

**Decision tickets incorporated**: [Core domain model and glossary](https://github.com/spippoli/tart/issues/3), [Uncertainty and provenance model](https://github.com/spippoli/tart/issues/4), [Information architecture and page inventory](https://github.com/spippoli/tart/issues/15) (record pages and routes), [Status, uncertainty and condition presentation rules](https://github.com/spippoli/tart/issues/17), [Artist records, personal data, and artist claims](https://github.com/spippoli/tart/issues/20), and, for the parts that shape records, [Submission and moderation lifecycle](https://github.com/spippoli/tart/issues/5) (what approval writes), [Content rights and GDPR product rules](https://github.com/spippoli/tart/issues/14) (names on Revisions pages, file rights fields), [Submission form flow](https://github.com/spippoli/tart/issues/27) (required initial Condition record, Location geometry kinds), and [History event types and Uncertain-date ordering](https://github.com/spippoli/tart/issues/89) (History event types, Condition mapping, Uncertain date ranges and ordering, stratigraphy), [Redaction, current-value removal and Purge](https://github.com/spippoli/tart/issues/95) (redacted current values, purged ids), [Record descriptive fields, text alternatives and slugs](https://github.com/spippoli/tart/issues/90) (descriptive fields, Source citations, periods, Series and Crew cardinality, Place description, alt text, slugs, default Surface types).

**Depends on**: [Foundations](foundations.md) (Instance configuration, storage and media pipeline, i18n shell, page shell).

## Problem Statement

Urban art in Rome appears, changes, and disappears faster than anyone records it. What survives is scattered across personal photo rolls, social media, and articles, with no shared place that says what was on a given wall, who is believed to have made it, what happened to it, and how sure anyone is. Existing catalogues tend to treat a work as a pin with a photo: when the work is painted over, the pin is deleted and its history goes with it; when the author is uncertain, the uncertainty is either hidden or not recorded; and a contributor's guess looks the same as a documented fact.

A visitor (Journey A) needs to open any artwork, including one that no longer exists, and understand what it is, where it is or was, what documentation exists and from when, who made it if known, what happened to it over time, and how much of that is evidenced. A researcher needs stable, citable pages and an inspectable record of how each entry changed. A community needs these records to survive overpainting, removal, and demolition, and to tell the physical life of a work apart from the edits made to its database entry.

## Solution

The archive stores eight kinds of **Archive record**. An **Artwork** sits on a **Location**, the physical surface that persists after every Artwork on it is gone, so the archive keeps the stratigraphy of a wall. Locations group into **Sites** by proximity and fall into **Areas** by geometry; **Series** group Artworks by intent. **Artists** are public creative identities, linked to Artworks through **Attributions** that carry an explicit certainty. **Documentation items** (images, PDFs, texts, links) and **Sources** are the evidence.

Each Artwork has a physical history: dated **History events** that, together with its Documentation items, make up its **Timeline**. Its **Condition** is never typed in: it is derived from its most recent condition-changing History event. Disappearance is recorded as a History event and never deletes anything. Dates are **Uncertain dates**, and **Claims** (Attributions and History events) show a derived **Evidence level** that a reader can inspect.

Records change only through approved **Submissions** (specified in Contribution and moderation). Each approval writes one **Revision** per touched record, and each record's Revisions are public on a separate `/revisions` subpage, never on the Timeline.

Every record kind has a public page at a stable URL. The Artwork page is the most important screen: an editorial, text-first catalogue label in which Condition and uncertainty are stated in words, with one of three historical-map signs per Condition group, and nothing is conveyed by colour alone.

## User Stories

**Discovering and reading an Artwork**

1. As a visitor, I want to open an Artwork page from a stable link, so that I can read about a work I saw on the street or found cited elsewhere.
2. As a visitor, I want the Artwork header to state its title or an explicit "Untitled", so that I never confuse a missing title with a forgotten one.
3. As a visitor, I want to see the Artwork's Expression types, so that I know whether it is a stencil, a paste-up, a mural, or something else.
4. As a visitor, I want to see the Artwork's Condition as a word with a sign and a date ("Intact · last documented 12 Apr 2026"), so that I know what state it was last known to be in and since when.
5. As a visitor, I want to see the Evidence level of the Condition ("documented · 2 sources" or "reported · no sources cited"), so that I can judge how well-founded it is.
6. As a visitor, I want a disappeared Artwork (covered, removed, destroyed, missing) to keep a full page with its last documentation and date, so that the archive remains useful after the work is gone.
7. As a visitor, I want to see who the Artwork is attributed to, with the certainty in words ("probable attribution", "Disputed attribution: A or B", "Unknown artist"), so that uncertain authorship is never presented as fact.
8. As a visitor, I want to see an Alias when the Artwork was signed with one, so that I can match the signature on the wall with the Artist.
9. As a visitor, I want a gallery of the Artwork's Documentation items, each with its Observed date, so that I can see how the work looked at different times.
10. As a visitor, I want each image to show its Creator credit and licence with a notice that the licence covers the file only, so that I know how I may reuse the file and that the depicted work is not covered.
11. As a visitor, I want to see where the Artwork is or was (mini-map, Location, Areas, Site), so that I can find it or understand its context.
12. As a visitor, I want an approximate Location to be stated in words ("approximate location, within 40 m") and drawn as a hatched area without a precise point, so that I am not misled about the precision.
13. As a visitor, I want to read the Artwork's description and the detail of each Attribution with its citations, so that I understand the context and the basis for each attribution.
14. As a visitor, I want a chronological Timeline of History events and Documentation items, so that I can follow how the work changed over time.
15. As a visitor, I want each History event on the Timeline to show when it was observed, when it was submitted, and when it was approved, so that I can tell the event's date from the date the archive learnt about it.
16. As a visitor, I want an Artwork without a Creation event to read as having an unknown creation date, distinct from its first documentation, so that I do not mistake the first photo for the date it was made.
17. As a visitor, I want uncertain dates written as `c. 2016`, `before 2012`, or `2014–2015` in my UI language, so that uncertainty reads as language, not as an error.
18. As a visitor, I want an overpainting event to link to the Artwork that covered this one, so that I can follow the layers on a wall.
19. As a visitor, I want a detached or moved piece to stay on the wall it came from as a `removed` event saying where it went, so that the wall keeps the memory of what was there.
20. As a visitor, I want the Sources cited by the Artwork, so that I can check the references myself.
21. As a visitor, I want links to related Artworks (same Location, same Artist, same Series), so that I can continue exploring.
22. As a visitor, I want each Artwork page to link to its Revisions, so that I can see how the record itself was edited, separately from the work's physical history.
23. As a visitor, I want archive content shown in the Content language even when I read the UI in English, so that nothing is machine-translated or silently altered.

**Artists**

24. As a visitor, I want an Artists index, so that I can browse the creative identities in the archive.
25. As a visitor, I want an Artist page showing the Artist's public name, Aliases, whether it is an individual or a collective, a biography, and a period of activity, so that I can learn about the identity behind a set of works.
26. As a visitor, I want to see the Artist's Areas of activity and Crew memberships, so that I understand where and with whom they worked.
27. As a visitor, I want the Artist page to list the Artworks attributed to it with their certainty, so that probable and disputed attributions are not shown as confirmed.
28. As a visitor, I want the Artist's own public channels listed as Sources, so that I can find the artist's own statements.
29. As an artist, I want my Artist page to show only my public artist identity, never my legal name (unless it is my artist name), age, residence, appearance, or any allegation of an offence, and never a photo of me, so that the archive does not expose me.
30. As an artist, I want no field or filter anywhere that says whether a work was authorised, so that my page is never a list of alleged offences.
31. As an artist with a registered account, I want my account never to be linked to my Artist record, so that the Operator never holds the link between my pseudonym and my email.

**Locations, Sites, Areas, Series**

32. As a visitor, I want a Location page showing the stratigraphy of the surface, the Artworks on it in succession and the documentation of their disappearance, so that I can see the layered history of one wall.
33. As a visitor, I want a Location to remain after every Artwork on it is gone, so that the history of the surface survives.
34. As a visitor, I want Site, Area, and Series pages with a header, a map, and a list of their Artworks, so that I can explore a hall of fame, a rione, or a project as a whole.
35. As a visitor, I want indexes of Sites, Areas, and Series reachable from the Archive and from record pages, so that I can browse them without crowding the main navigation.

**Sources and Documentation items**

36. As a visitor, I want every Source to have its own permalink, so that I can cite it and see what it is cited by.
37. As a visitor, I want every Documentation item to have its own permalink with its Observed date, Creator credit, licence, and the Artworks it documents, so that I can cite a specific photo or document.
38. As a visitor, I want a PDF Documentation item to show a preview of its first page, so that I can tell what it is before opening it.
39. As a visitor, I want a text or link Documentation item to be shown with its own language when that differs from the Content language, so that assistive technology reads it correctly.

**Audit trail and visibility**

40. As a researcher, I want a `/revisions` subpage on every record listing each Revision with its Submitter's display name and its submitted and approved dates, so that I can see who changed the record and when.
41. As a researcher, I want a merged duplicate's URL to redirect permanently to the surviving record, so that my citations keep working.
42. As a researcher, I want a withdrawn record's URL to answer that it was removed for legal, rights, or privacy reasons, without its content, so that I know the link is not broken but deliberately hidden.
43. As a Submitter, I want to see a notice on a record that my pending Submissions touch, with the pending content shown inline and marked as under review, so that I can follow my contribution without anyone mistaking it for accepted fact.
44. As a Moderator, I want to see how many pending Submissions touch a record, so that I can spot busy records.
45. As a visitor, I want to never see pending content, so that proposed data is never presented as accepted.
46. As a visitor, I want a "Report" action on every record and Documentation item page, so that I can send a Notice about unlawful content without an account.

**Contributing from a record**

47. As a signed-in User, I want actions on the Artwork page to propose an edit, add documentation, and report a condition change, so that I can contribute from where I noticed something.
48. As an anonymous visitor, I want those actions to send me to sign-in and back, so that I can contribute without losing my place.

**Accessibility and languages**

49. As a keyboard or screen-reader user, I want every record page, including its gallery and Timeline, to work without a mouse and without hover, so that I can read the archive.
50. As a user with low colour vision, I want Condition and uncertainty conveyed by words and shapes, never colour alone, so that I read them correctly.
51. As a visitor without WebGL2, I want record pages to be fully usable without the mini-map, so that I can still read where a work is.
52. As an Italian or English speaker, I want every label, status, error, and empty state in my UI language, with dates formatted for my language in the Instance's time zone, so that the page reads naturally.

## Implementation Decisions

### Scope and dependencies

- This spec owns the record model, the derivations (Condition, Evidence level, first documentation, Area membership), the Revision store and its read side, and the public read pages. It does not own how records are written: the only writer is the approval of a Submission, specified in Contribution and moderation (ADR 0002). Until that spec is built, records are created in tests and development through the same domain write operation that approval will call.
- Withdrawal, Redaction, Reinstatement, Purge, and Notices are specified in Rights and legal actions. This spec owns only how pages behave for content in those states.
- Merge mechanics are specified in Contribution and moderation (open ticket [Duplicate detection and Merge](https://github.com/spippoli/tart/issues/42)). This spec owns only the redirect.
- Map rendering (markers, clustering, overlays, the mini-map's style) is specified in Discovery. Record pages embed the map module only through its public interface (ADR 0004).

### Modules

- **Archive domain** (ports and adapters, per `CLAUDE.md`): the record kinds and their invariants, the Uncertain date value, the physical history (History events, Condition derivation, Timeline assembly), Attributions and Evidence level. No framework or persistence imports. It exposes:
  - a read interface per record kind returning the public view of a record (with derived Condition, Evidence levels, Timeline);
  - one write operation that applies a validated changeset to one or more records and returns the new Revisions (used by approval);
  - pure functions for Condition derivation, Evidence level derivation, and Uncertain date formatting inputs.
- **Archive persistence**: PostgreSQL/PostGIS repositories behind the domain's ports (ADR 0004). Location and Area geometries are PostGIS geometries; Area membership is a spatial query, never stored by hand.
- **Archive API**: read endpoints for each record kind, its Revisions, and its indexes, returning stable error codes (ADR 0008). Pending Submission content is included only for the Submitter and Moderators, and the API never sends Moderation notes to non-Moderators.
- **Record pages** (frontend): one page per record kind plus the `/revisions` subpage and the indexes, server-rendered, with all UI strings through the i18n shell.

### Common record rules

- Every Archive record has a stable id that never changes (ADR 0010). It is local to the Instance (ADR 0001).
- A record becomes public only through an approved Submission; a record that exists only in a pending Submission is not an Archive record and is never shown to the public.
- Records are never deleted. They leave public view only by Merge (redirect) or Withdrawal (410), and leave the database only by Purge (Rights and legal actions).
- All free text in records (titles, names, descriptions, biographies, notes) is in the Content language and is rendered with that language's `lang` and `dir`, whatever the UI language (ADR 0008). Nothing is translated.
- Values from open vocabularies (Expression type, Surface type) are stored by their immutable `key` and shown with the label for the current UI language. A `retired` entry is still displayed on existing records (ADR 0009).
- Values from closed vocabularies (Condition, History event type, Attribution certainty, Uncertain date precision and qualifier) are platform enums with one UI message per value.
- Fields not listed for a record kind below do not exist: configurability stops at vocabularies, and custom metadata fields are out of scope (ADR 0009).
- No record kind has a field for whether an Artwork was authorised, and none may be added (ADR 0014).
- No record stores the Submitter's position. EXIF GPS is only ever a suggestion in the form and is stripped from stored originals (ADR 0012).

### Uncertain date

- An Uncertain date is entered as a precision (`day`, `month`, `year`, `decade`, `unknown`), a qualifier (`exact`, `circa`, `before`, `after`), and one or two values at that precision. A second value is allowed only with `exact` and gives the "from–to" form (`2014–2015`, `March–May 2016`). `unknown` is a precision only: it has no value and no qualifier. The form's "Unknown date" choice stores precision `unknown` ([History event types and Uncertain-date ordering](https://github.com/spippoli/tart/issues/89)).
- It stores the entered values together with a derived earliest–latest range (day-precise bounds, either of which may be open):
  - the **base range** of a value is the first to the last day it covers (`2016` → 1 Jan–31 Dec 2016; `March 2016` → 1–31 Mar; `1990s` → 1 Jan 1990–31 Dec 1999);
  - `exact`: the base range, or from the start of the first value to the end of the second;
  - `circa`: the base range widened by one unit of the precision on each side (`c. 2016` → 2015–2017; `c. March 2016` → Feb–Apr 2016; `c. 1990s` → 1980–2009);
  - `before X`: earliest open, latest the day before X starts;
  - `after X`: earliest the day after X ends, latest the date of the Submission;
  - `unknown`: both bounds open;
  - no latest bound is ever later than the date of the Submission; this also truncates `circa`.
- The range is used only for filtering by overlap ([Discovery](discovery.md)). Ordering uses the chronological key below.
- **Chronological key**: the midpoint of the base range of the entered values, ignoring the widening of `circa`: `2016` and `c. 2016` → mid-2016; `2014–2015` → end of 2014; `before X` → the start of X; `after X` → the end of X. Ties are broken by the later approval (the Revision timestamp), then by id, so information approved later wins. An `unknown` date has no key. The same key orders the Condition derivation, the Timeline, the stratigraphy, and first and last documentation, in both directions.
- It is used for: the Observed date of Documentation items and History events, the date of a Creation event, the date of a Source, and the two ends of a period.
- A **period** (an Artist's period of activity, a Crew membership period) is a **start** and an **end**, each an optional Uncertain date with its own precision and qualifier. The start's chronological key must not be later than the end's. Without an end the period shows as "from …", without a start as "until …", and without both there is no period. No flag says that an activity or membership is ongoing ([Record descriptive fields, text alternatives and slugs](https://github.com/spippoli/tart/issues/90)).
- Display uses one platform message per precision × qualifier combination, formatted with `Intl` in the UI language and the Instance's time zone (ADR 0008), producing forms such as `c. 2016`, `before 2012`, `2014–2015` (ADR 0015).
- Uncertain dates are never "disputed". When Sources conflict, the History event carries the widest compatible range and a note.
- The submitted and approved dates of a Claim are not Uncertain dates: they are exact timestamps from the Submission and the Revision.

### Artwork

| Field | Rules |
|---|---|
| Title | Optional, Content language. Without one, every surface shows an explicit "Untitled" (a UI string) |
| Expression types | One or more, from the open vocabulary |
| Description | Optional free text, subject to the Artist content rules of ADR 0014 when it names people |
| Location | Exactly one Location. It changes only to correct wrong data, never for a physical move |
| Attributions | Zero or more (see Attribution) |
| History events | Zero or more; the Artwork's physical history |
| Documentation items | Linked many-to-many; a new Artwork has at least one (Contribution and moderation validates this) |
| Series | Zero or more Series |
| Sources | Record-level citations: background references that never change an Evidence level (ADR 0006) |

- Identity rules (from [#3](https://github.com/spippoli/tart/issues/3)): overpainting by someone else creates a new Artwork, and the old one gets an overpainting History event optionally linking to the covering Artwork; a refresh by the same artist is a `modified` event on the same Artwork; a detached or moved piece gets a `removed` event on its original Location, whose note and citations say where it went, and if it reappears in another urban place that is a new Artwork documented there (ADR 0003, amended by [History event types and Uncertain-date ordering](https://github.com/spippoli/tart/issues/89)).
- An edit Submission may change the Artwork's Location to correct wrong data; it produces a Revision and no History event. Editing a Location's geometry is a separate Submission on that Location ([#27](https://github.com/spippoli/tart/issues/27)).
- Derived values, never stored by hand:
  - **Condition**: see Physical history.
  - **First documentation**: the Observed date of the Artwork's public Documentation item that comes first by chronological key.
  - **Last documented**: the Observed date of the Artwork's public Documentation item that comes last by chronological key.
  - **Areas**: the Areas the Artwork's Location falls within by geometry.

### Location

| Field | Rules |
|---|---|
| Geometry | A point, a line, or a simple polygon (no self-intersection); must fall inside the Instance boundary (ADR 0009) |
| Approximate | Exact or approximate; applies to every geometry kind |
| Uncertainty radius | Optional, in metres, for approximate points only |
| Surface type | From the open vocabulary |
| Site | At most one |
| Place description | Optional, Content language, one line of at most 200 characters saying in words where the surface is ("Shutter at no. 12, left of the entrance", "North pier of the bridge, river side"). Not a structured address, and never geocoded |

- A Location has no Condition, no physical history of its own, and is never deleted (ADR 0003).
- Several Artworks can share a Location, side by side or in succession.
- **Title**: the Place description; without one, the Surface type label followed by the Site name, else the first Area by name ("Shutter · Pigneto"); without either, "Location {id}" (a UI string). The title is used for the page header, the browser title, the map panel, and every link to the Location ([Record descriptive fields, text alternatives and slugs](https://github.com/spippoli/tart/issues/90)).
- **Stratigraphy**: the Artworks on a Location, ordered by the chronological key of their Creation event, or of their first documentation when they have none, most recent first; ties as for the key. `covered` links never reorder it: a covered Artwork placed above the one covering it is inconsistent data, corrected by a Submission. Disappeared Artworks stay in it with their Condition word and sign. The Location page and the map side panel use the same order ([History event types and Uncertain-date ordering](https://github.com/spippoli/tart/issues/89)).
- Documentation items that document a disappearance link to the Location as well as to the Artworks (glossary: Documentation item).

### Site, Area, Series

- **Site**: a name, an optional description, and the Locations that belong to it (membership is the Location's Site field). Record-level Sources.
- **Area**: a name, an optional description, and a polygon geometry. Areas may overlap. Locations fall within Areas by geometry, computed. Areas are archive data entered through Submissions, never configuration; Rome starts with none (ADR 0009). Record-level Sources.
- **Series**: a name, an optional description, and its Artworks, regardless of where they are. An Artwork may belong to zero or more Series. Record-level Sources. A documented commission (a festival, a municipal project) may be told in a Series or a description, with a Source (ADR 0014).
- The description is free text in the Content language, subject to the Artist content rules of ADR 0014 when it names people ([Record descriptive fields, text alternatives and slugs](https://github.com/spippoli/tart/issues/90)).

### Artist, Alias, Crew membership

| Field | Rules |
|---|---|
| Name | The public name it uses as an artist. A legal name appears only when it is itself that name, and is never added as an Alias |
| Kind | Individual or collective |
| Aliases | Zero or more alternative public names |
| Biography | Optional free text |
| Period of activity | Optional period (see Uncertain date) |
| Areas of activity | Zero or more Areas |
| Crew memberships | This Artist, individual or collective, as a member of a collective Artist, each with an optional period |
| Sources | Record-level citations; the artist's own public channels are linked only as Sources |

- Content rules (ADR 0014), enforced by Moderators at review and repeated in the editorial guidelines: free text never states a legal identity, age or date of birth, residence, physical appearance, or any allegation of an offence. An Artist has no image of the person, and no field for one.
- There is no link of any kind between a User and an Artist, not even a verified or read-only claim (ADR 0014).
- Artists are local to the Instance (ADR 0001).
- Crew memberships may nest (a crew inside a larger collective) but never form a cycle: no collective is a member of itself, directly or through a chain. Pages show direct memberships only, never the transitive closure.
- When an Artist is withdrawn, its Attributions and Crew memberships are hidden with it, and its Artworks show no Attribution, exactly as Artworks without Attributions do; Reinstatement restores them (ADR 0014).

### Attribution

- An Attribution is a Claim linking one Artwork to one Artist, with:
  - a certainty: `confirmed`, `probable`, or `disputed`;
  - an optional Alias the Artwork was signed with (one of the Artist's Aliases);
  - an optional note;
  - citations (Sources and Documentation items) that determine its Evidence level.
- `confirmed` requires at least one citation; without evidence the strongest certainty is `probable` (ADR 0006). A User writing "I made this" in a Submission is not a citation (ADR 0014).
- Several non-disputed Attributions on one Artwork mean a collaboration. Competing alternatives are all `disputed`, with a note.
- An Artwork without Attributions has unknown authorship and reads "Unknown artist".
- Correcting an Attribution is a Revision. A real-world change (for example an artist publicly claiming a piece) is recorded additionally as an `attribution changed` History event with its own date and citations.

### Source

- A Source is a citable external reference (article, book, the artist's own publication). It can be cited by Artworks, Artists, Sites, Areas, Attributions, and History events.
- It may carry its own language tag, used as its `lang` when rendered (ADR 0008).
- Its fields ([Record descriptive fields, text alternatives and slugs](https://github.com/spippoli/tart/issues/90)):

  | Field | Rules |
  |---|---|
  | Title | Required; the text of the reference |
  | Author | Optional free text; may hold several names or a pseudonym |
  | Publication | Optional: periodical, publisher, website, or channel |
  | Date | Optional Uncertain date |
  | URL | Optional |
  | Note | Optional: pages, context, where an archived copy is |
  | Language | Optional language tag |

- It has no Source type: no rule or filter needs one. Its rendered citation is "Author, *Title*, Publication, Date", omitting absent parts, followed by the URL.
- Sources are Archive records, editable through Submissions, with their own Revisions ([#5](https://github.com/spippoli/tart/issues/5)).
- External testimony enters the archive as a Source ([#4](https://github.com/spippoli/tart/issues/4)).

### Documentation item

| Field | Rules |
|---|---|
| Medium | `image`, `pdf`, `text`, or `link`. Video and audio are out of scope |
| Observed date | Uncertain date; required |
| Artworks | One or more |
| Location | Set only for documentation of a disappearance |
| File | For `image` and `pdf`: an immutable stored file; replacing a file means a new Documentation item ([#5](https://github.com/spippoli/tart/issues/5)) |
| Licence | For uploaded files: one licence from the Instance allowlist (ADR 0012) |
| Creator credit | For uploaded files: required; may be a pseudonym; independent of the Submitter |
| Rights basis | For uploaded files: own work, or third-party work already under an allowlisted licence with its creator and origin URL |
| Alt text | For `image`: required, Content language, at most 250 characters. Describes what the image shows (the work, the surface, its state) without interpreting it, and follows the content rules of ADR 0014: no appearance or identity of people in the photo. Written by the Submitter in the Documentation step, checked by the Moderator at review like any other field, and corrected later by an edit Submission |
| Text | For `text`: the text itself |
| URL | For `link`: the linked address. Material whose rights do not allow upload is linked, never uploaded |
| Language | Optional language tag for `text` and `link` items |

- An image shows a single Location (ADR 0003): every Artwork linked to one image Documentation item is on the same Location.
- Documentation items are Archive records, editable through Submissions with their own Revisions; the file itself never changes.
- Public renditions of images are WebP, carry no EXIF, and are capped at a resolution set in the Instance configuration; the original is never public (ADR 0004, ADR 0012). PDFs show a first-page preview (ADR 0004). Producing renditions is part of the Foundations media pipeline.
- Every licence notice states that it covers the file only, never the depicted Artwork (ADR 0012).
- There is no separate caption field: the visible caption is composed from the Observed date, the Creator credit, and the licence. A PDF's first-page preview carries a platform alt text ("First page of the document") and links to the file ([Record descriptive fields, text alternatives and slugs](https://github.com/spippoli/tart/issues/90)).
- All stored objects are private and served through the app; a pending or withdrawn file is hidden by a database flag (ADR 0004).

### Physical history

- **History events** are Claims on one Artwork. Each has a type from the platform's closed vocabulary (ADR 0009), an Observed date (Uncertain date), an optional note, citations (Sources and Documentation items), and type-specific links:
  - a `covered` event may link the covering Artwork.
- The closed vocabulary has nine types ([History event types and Uncertain-date ordering](https://github.com/spippoli/tart/issues/89)):

| Type | Meaning | Sets Condition |
|---|---|---|
| `created` | The Creation event: the Artwork was made | No |
| `condition recorded` | The Condition record: the state observed, without asserting a change | The Condition it states (any of the nine) |
| `deteriorated` | Natural decay (fading, flaking, peeling) | `deteriorated` |
| `damaged` | Partial damage (vandalism, tags over it, breakage) | `damaged` |
| `modified` | Altered or refreshed by the same artist | `modified` |
| `covered` | Covered by overpainting, buffing, or posters; optionally links the covering Artwork | `covered` |
| `removed` | Taken away from its surface (detached, scraped off, removed); the note says where it went when known | `removed` |
| `destroyed` | Destroyed with its surface (demolition) | `destroyed` |
| `attribution changed` | A real-world change of attribution, such as an artist publicly claiming a piece | No |

- The seven types that set a Condition are the **condition-changing** types. `missing`, `unknown`, a restoration (`intact`), and a covered piece re-exposed are recorded with a `condition recorded` event. There is no `relocated`, `restored`, or `not found` type.
- History events have no certainty of their own; their Evidence level and the `missing` Condition are enough ([#4](https://github.com/spippoli/tart/issues/4)).
- **Condition** is one of `intact`, `deteriorated`, `damaged`, `modified`, `covered`, `removed`, `destroyed`, `missing`, `unknown`. It is always derived from the Artwork's most recent public condition-changing History event by chronological key, never stored or set by hand, and recomputed on every approval that touches the Artwork's History events ([#5](https://github.com/spippoli/tart/issues/5)).
- A `condition recorded` event states the Condition observed on its Observed date without asserting a change; it counts for the derivation. Every new Artwork gets one, required and asked explicitly, dated to the latest Observed date and citing that document; there is no implicit `intact` ([#27](https://github.com/spippoli/tart/issues/27)).
- Events with an `unknown` Observed date count for the derivation only when no dated condition-changing event is public; among them, the most recently approved wins.
- **Invariant**: an approved Artwork always has at least one condition-changing History event. A Submission that would remove the last one is rejected at submission with a stable error code (form: "At least one event must record the Artwork's state"); the Submitter replaces it instead, for example with a `condition recorded` `unknown` event.
- **Fallback**: when no condition-changing event is public (for example after a Redaction), the Condition shown is `unknown`, worded "state not documented", without a date. This is the only Condition shown without a date.
- **Condition group** is derived from Condition: *present* (`intact`, `deteriorated`, `damaged`, `modified`), *disappeared* (`covered`, `removed`, `destroyed`, `missing`), *unknown* (`unknown`). It describes whether the Artwork can still be seen where it is, never whether the record is public.
- A disappeared Artwork remains a full public Archive record. Disappearance is never deletion.
- **Creation**: the Creation event states when the Artwork was made. With no Creation event, the creation date is unknown and is shown as such; it is never inferred from the first documentation.
- **Timeline**: the chronological presentation of an Artwork's public History events and public Documentation items, ascending by chronological key; on equal keys a History event precedes a Documentation item. Items with an `unknown` Observed date follow in a final "Undated" group. It never includes Revisions, Submission log entries, Withdrawals, or Redactions.

### Evidence level

- Only Claims (Attributions and History events) carry an Evidence level. It is `documented` when the Claim cites at least one Source or Documentation item, otherwise `reported`. It is computed, never stored as an editable value, and nobody can override it (ADR 0006).
- Record-level citations on Artworks, Artists, Sites, Areas, and Series are background references and never change an Evidence level.
- A weak Source still makes a Claim `documented`; the page shows the citations so the reader can judge them.
- Other fields (title, description, Expression type, and so on) carry no Evidence level; their provenance is the Revision that introduced them.

### Revisions

- An approved Submission produces, in one atomic transaction, one Revision per record it creates or changes. Each Revision records the producing Submission, the Submitter, the approving Moderator, the first-submitted date, and the approved date ([#5](https://github.com/spippoli/tart/issues/5)). The structure of the changeset itself is ADR 0007's.
- Revisions are the record's audit trail. They are distinct from the Timeline (physical history) and from the Submission log (moderation history).
- A Claim's provenance is the Revision that introduced it plus its citations. The Timeline shows each History event's submitted and approved dates from that Revision.
- Undoing a change is a new Submission pre-filled from an earlier Revision, never a rollback (ADR 0002).
- Withdrawal and Redaction produce no Revision (ADR 0002, ADR 0013). A Redaction hides selected operations of one or more Revisions; each affected Revision stays listed on `/revisions` with its Submitter, dates, and touched field or item names, but the redacted content is hidden from the public ([#95](https://github.com/spippoli/tart/issues/95)).

### Visibility

| State | Public page | `/revisions` | Submitter of a pending Submission | Moderators |
|---|---|---|---|---|
| Approved | Shown | Shown | Shown | Shown |
| Pending change to an approved record | Approved data only, no indication | Unchanged | Notice linking to their pending Submissions, and pending content inline in a dashed, hatched box labelled as under review; it never changes the displayed Condition | "N pending submissions on this record", and pending content inline as for the Submitter |
| Merged duplicate or retired Documentation item | 301 to the surviving record | 200, read-only, with a "merged into" notice (ADR 0018) | — | — |
| Withdrawn record or Documentation item | 410 with a neutral page stating it was removed for legal, rights, or privacy reasons, and none of its content | 410 | — | — |
| Redacted operations of a Revision | Record shown; a redacted value that is still current shows a neutral "removed for legal reasons" placeholder (field) or is omitted (item) | Revision listed with touched field or item names, the redacted content hidden | — | — |
| Purged record or Documentation item | 410 with the same neutral page, forever; the id is never reused | 410 | — | — |

- A record that exists only in a pending Submission answers 404 to the public.
- Withdrawn Documentation items are absent from galleries and Timelines; a withdrawn Artist hides its Attributions and Crew memberships (ADR 0014).

### Public record pages

**Routes** (from [#15](https://github.com/spippoli/tart/issues/15); path segments are UI strings and may change before launch, ids never do):

| Page | `it` | `en` |
|---|---|---|
| Artwork | `/it/opere/{id}-{slug}` | `/en/artworks/{id}-{slug}` |
| Artists index, Artist | `/it/artisti`, `/it/artisti/{id}-{slug}` | `/en/artists`, `/en/artists/{id}-{slug}` |
| Location | `/it/superfici/{id}` | `/en/locations/{id}` |
| Sites index, Site | `/it/luoghi`, `/it/luoghi/{id}-{slug}` | `/en/sites`, `/en/sites/{id}-{slug}` |
| Areas index, Area | `/it/aree`, `/it/aree/{id}-{slug}` | `/en/areas`, `/en/areas/{id}-{slug}` |
| Series index, Series | `/it/serie`, `/it/serie/{id}-{slug}` | `/en/series`, `/en/series/{id}-{slug}` |
| Source | `/it/fonti/{id}` | `/en/sources/{id}` |
| Documentation item | `/it/documenti/{id}` | `/en/documents/{id}` |
| Revisions of any record | `…/revisioni` | `…/revisions` |

- Only the id resolves the record. The slug is derived from the record's current name. A wrong, missing, or outdated slug answers 301 to the canonical URL (ADR 0010). Kinds whose route has no slug (Location, Source, Documentation item) are canonical at the bare id.
- **Slug derivation** ([Record descriptive fields, text alternatives and slugs](https://github.com/spippoli/tart/issues/90)): lowercase the name, strip accents (`unaccent`), turn every run of non-alphanumeric characters into `-`, trim leading and trailing `-`, and cut at 60 characters on the last `-` that fits. A record with no name (an untitled Artwork), or whose name yields an empty slug, is canonical at the bare id (`/it/opere/4821`); when it later gets a name, the bare id answers 301 to `…/{id}-{slug}`.
- The browser title is `<Page> — <Archive name>`.
- Every record and Documentation item page has a "Report" action leading to `/it/segnala?oggetto=…` (`/en/report?object=…`); the form belongs to Rights and legal actions.
- Every record page links to its `/revisions` subpage.

**Artwork page**, in this order:

1. **Header**: title or explicit "Untitled"; Expression types; Condition as word plus Condition-group sign, with the Observed date of its History event ("since …"), the latest documentation date, and the Evidence level; Attribution summary with certainty.
2. **Gallery**: the public Documentation items with their Observed dates, Creator credits, and licences ("covers the file only").
3. **Where**: mini-map, Location (link), Areas, Site, and the approximate-location notice when applicable.
4. **Description and Attribution detail**: the description; each Attribution with certainty, Alias used, note, Evidence level, and citations.
5. **Timeline**: History events and Documentation items in chronological order; each History event shows its type, Observed date, submitted date, approved date, Evidence level, citations, note, and the covering Artwork link of a `covered` event.
6. **Sources**: the record-level Sources.
7. **Related**: Artworks on the same Location, by the same Artist, and in the same Series.
8. **Actions**: propose an edit, add documentation, report a condition change, report content. Contribution actions for an anonymous visitor go to sign-in with `?next=` and return.
9. **Revisions** link.

**Other record pages** follow a reduced version of the same pattern ([#15](https://github.com/spippoli/tart/issues/15)):

- **Artist**: header (name, kind, Aliases, period of activity), biography, Areas of activity, Crew memberships (in both directions: members of a collective, collectives a member belongs to), attributed Artworks each with its Attribution certainty in words, Sources, actions, Revisions link. No image of the person.
- **Location**: header (title, Place description, Surface type, exact or approximate with radius, Site, Areas), mini-map, the stratigraphy (the Artworks on that surface, most recent first as defined under Location, each with its Condition word and sign), the Documentation items that document disappearances there, actions, Revisions link.
- **Site, Area, Series**: header (name, and for Site and Area their place), description, map, list of Artworks with Condition word and sign, Sources, actions, Revisions link.
- **Source** and **Documentation item**: minimal permalinks, needed for citation, Notices, and Merge redirects. A Source shows its rendered citation, its Note, and what cites it. A Documentation item shows the file rendition or preview with its alt text (or text, or link), Observed date, Creator credit, licence with "covers the file only", the Artworks it documents, and, for a disappearance, its Location.

**Indexes** (Artists, Sites, Areas, Series) list records by name with links to their pages, alphabetically in the Content language, paginated by 24, with a "Filter by name" field (name plus Aliases for Artists) specified in [Discovery](discovery.md#index-name-filter). They never rank by popularity or activity.

**`/revisions` subpage**: lists the record's Revisions with the Submitter's display name (which may be a pseudonym, with no profile link), the first-submitted and approved dates, and the Revision's content unless redacted ([#14](https://github.com/spippoli/tart/issues/14)).

### Presentation rules (ADR 0015)

- Words carry the meaning, shape carries the group, colour is redundant. Three signs, one per Condition group, used identically on cards, record pages, and the Timeline: solid square for *present*, dashed square for *disappeared*, dotted square for *unknown*, always next to the word for the exact Condition. The *unknown* sign needs a stronger differentiator than dotting (for example a "?" inside) when drawn.
- An approximate Location is drawn as a hatched area with a smaller sign and no precise point, and stated in words with its radius when known.
- A Condition is never shown without a date: "Intact · last documented 12 Apr 2026". The only exception is the `unknown` fallback "state not documented" (see Physical history).
- Uncertainty is language, not alarm: no warning icons, no red. Fixed wordings: `[name] — probable attribution`, `Disputed attribution: A or B`, `Unknown artist`, `approximate location, within N m`, `documented · N sources`, `reported · no sources cited` (all UI strings, translated).
- Cards show only the Condition and the latest documentation date; the Timeline shows the three dates of each History event.
- One accent colour marks *disappeared*, one marks pending content; both stay readable in grayscale.
- Avoid traffic-light colours, coloured badges, gradients, counters or popularity cues, and placeholders that assume colourful murals.

**Example** (fictional record, invented for illustration; not a real artwork or artist): an Artwork with no title, Expression type *stencil*, attributed with certainty `probable` to a fictional Artist "Nebbia Finta", whose latest condition-changing event is an approved `condition recorded` event stating `missing`, would read in the `en` UI: "Untitled · stencil · [dashed square] Missing · since c. 2019 · last documented 3 Mar 2018 · reported · no sources cited · Nebbia Finta — probable attribution".

## Acceptance criteria

**Records and derivations**

1. An Artwork with no title shows "Untitled" (translated) in its header, card, browser title, and every list.
2. An Artwork's Condition equals the Condition given by its most recent condition-changing public History event; no API or page accepts a Condition value as input.
3. Approving a Submission that adds a `destroyed` (or any disappeared-group) History event changes the Artwork's Condition group to *disappeared* and leaves the Artwork, its Documentation items, its Location, and all its earlier History events public.
4. No operation in the archive domain deletes an Artwork or a Location.
5. A Claim citing at least one public Source or Documentation item reads `documented`; a Claim citing nothing reads `reported`; there is no field, endpoint, or role that can change this.
6. A record-level Source on an Artwork does not change the Evidence level of any of its Claims.
7. A `confirmed` Attribution with no citation cannot be written by the archive write operation.
8. An Artwork without Attributions reads "Unknown artist"; with several non-disputed Attributions it lists all of them; with disputed ones it reads "Disputed attribution: A or B".
9. An Artwork with no Creation event shows its creation date as unknown and separately shows its first documentation date.
10. A Location geometry outside the Instance boundary, or a self-intersecting polygon, is rejected with a stable error code.
11. An uncertainty radius is accepted only on an approximate point.
12. An image Documentation item linked to Artworks on two different Locations is rejected.
13. Every Uncertain date precision × qualifier combination renders through its own message in every enabled UI language, with dates formatted by `Intl` in the Instance's time zone.
14. A retired Expression type or Surface type still displays its label on existing records.
15. No record kind exposes a field for authorisation or legality, and no Artist exposes an image of the person or a link to a User.

**Pages and URLs**

16. Each record kind is served at the route in the table above in both `it` and `en`; a wrong, missing, or outdated slug answers 301 to the canonical URL.
17. A merged duplicate's or retired Documentation item's id answers 301 to the surviving record, without redirect chains; its `/revisions` subpage answers 200 with its own Revisions and a "merged into" notice (ADR 0018).
18. A withdrawn record or Documentation item answers 410 with a neutral page that shows none of its content; its `/revisions` subpage answers 410 too.
19. A record that exists only in a pending Submission answers 404 to anonymous visitors and to signed-in Users who are not its Submitter or a Moderator.
20. Pending content is never present in public HTML or in API responses to anyone other than the Submitter and Moderators; for them it is shown in a box labelled as under review and does not change the displayed Condition.
21. The Timeline never shows Revisions, Submission log entries, Withdrawals, or Redactions; the `/revisions` subpage never shows History events as such.
22. Each History event on the Timeline shows its Observed, submitted, and approved dates.
23. Every image shows its Creator credit and a licence notice stating that it covers the file only; public renditions carry no EXIF and never exceed the configured cap; originals are never served publicly.
24. A withdrawn Artist's Attributions and Crew memberships are absent from every Artwork, Artist, and list page.
25. Every record and Documentation item page has a "Report" action and a link to its `/revisions` subpage.
26. The `/revisions` subpage shows each Submitter's display name without a profile link, and hides the content of redacted Revisions.

**Accessibility (WCAG 2.2 AA) and i18n**

27. Condition, Condition group, Attribution certainty, Evidence level, approximate location, and pending state are each conveyed in text; the sign and any colour are redundant, and the page remains correct in grayscale.
28. Every page is fully operable by keyboard with visible focus; nothing essential depends on hover, including gallery navigation and Timeline details.
29. Every image has a meaningful text alternative: an image Documentation item's alt text, or a platform alt text for a PDF preview.
30. Record pages are fully usable without WebGL2: the location is stated in text (Location title, Place description, Areas, Site, approximate notice) when the mini-map cannot render.
31. Archive content is marked up with the Content language's `lang` (and `dir`); Sources and text or link Documentation items with their own language tag use that tag.
32. No user-facing string (labels, statuses, Condition and vocabulary names, error codes, aria labels, empty states) is hardcoded; the build fails on a missing message key.
33. The Timeline is a semantic, chronologically ordered list; the gallery exposes each item's Observed date as text.
34. Axe checks report no violations on each record page kind, in both UI languages, in the states: complete record, Untitled, unknown artist, disputed attribution, approximate location, disappeared, destroyed, no image (link-only documentation), pending (as Submitter), merged, withdrawn.

**Physical history and Uncertain dates**

35. The History event type vocabulary is exactly the nine types of Physical history, and each condition-changing type sets the Condition in its table.
36. The derived range matches the rules of Uncertain date for every precision × qualifier, including open bounds for `before` and `unknown`, `after` closed at the Submission date, and no latest bound after the Submission date; a second value is rejected unless the qualifier is `exact`.
37. Of two condition-changing events with equal chronological keys, the later-approved one sets the Condition; an `unknown`-dated event never overrides a dated one.
38. A Submission that would leave an Artwork with no condition-changing History event is rejected with a stable error code; an Artwork whose condition-changing events are all non-public shows `unknown` with "state not documented".
39. Changing an Artwork's Location creates no History event, and the Artwork leaves its former Location's stratigraphy.
40. The stratigraphy lists Artworks by the chronological key of their Creation event, or of their first documentation without one, most recent first, regardless of `covered` links.

**Descriptive fields, text alternatives and slugs**

41. Sites, Areas, and Series accept an optional description, rendered after the page header in the Content language.
42. A Source without a Title is rejected with a stable error code; its page renders "Author, *Title*, Publication, Date" omitting absent parts, then the URL.
43. A period whose start has a later chronological key than its end is rejected; a period with only a start shows "from …", with only an end "until …".
44. An Artwork can be linked to several Series; a Crew membership that would make a collective a member of itself, directly or through a chain, is rejected.
45. A Location's title is its Place description, else "Surface type · Site or first Area", else "Location {id}"; a Place description longer than 200 characters is rejected.
46. An image Documentation item without alt text, or with one longer than 250 characters, is rejected; every image rendition is served with its item's alt text.
47. An untitled Artwork is canonical at `/it/opere/{id}` and `/en/artworks/{id}`; after it gets a title, the bare id answers 301 to `…/{id}-{slug}`.
48. The slug of "Lupa à rebours — Stencil n°3" is `lupa-a-rebours-stencil-n-3`; a name yielding no alphanumeric character gives the bare-id URL.
49. A new Instance's Surface type file holds the platform's default list, in its order, with `it` and `en` labels.

## Instance configuration

Exact key names belong to the [Foundations](foundations.md) spec, which owns `instance.toml`; this spec reads the following values.

| Setting | Use here | Rome |
|---|---|---|
| Content language | `lang`/`dir` of all archive content | `it` |
| Enabled UI languages and default | Route prefixes, labels | `it` (default), `en` |
| Time zone | Formatting of Observed, submitted, and approved dates | `Europe/Rome` |
| Archive name | Browser title `<Page> — <Archive name>` | "Rome Urban Art Archive" |
| Expression type vocabulary | Artwork Expression types, labels per UI language, `retired` | Starting from the brief's §9 list |
| Surface type vocabulary | Location Surface type, labels per UI language, `retired` | Starting from the platform default list below |
| Boundary (GeoJSON) | Rejects Location geometries outside it | Not yet decided |
| File licence allowlist | Licence values shown on Documentation items | `CC-BY-4.0`, `CC-BY-SA-4.0`, `CC0-1.0`; default `CC-BY-SA-4.0` |
| Public image rendition cap | Maximum resolution of public renditions | Not yet decided |

The Data licence is shown in the footer (Foundations); this spec does not render it per record.

**Default Surface type list** ([Record descriptive fields, text alternatives and slugs](https://github.com/spippoli/tart/issues/90)), shipped by the platform as a starting vocabulary in this order; an Instance edits or retires entries in its own file (ADR 0009). Vehicles and trains are not Locations, so they have no entry.

| `key` | `it` | `en` |
|---|---|---|
| `building_wall` | Muro di edificio | Building wall |
| `boundary_wall` | Muro di cinta o di contenimento | Boundary or retaining wall |
| `shutter` | Saracinesca | Shutter |
| `door` | Porta o portone | Door |
| `hoarding` | Recinzione di cantiere | Construction hoarding |
| `fence` | Cancello o recinzione | Gate or fence |
| `bridge_underpass` | Ponte, sottopasso, galleria | Bridge, underpass, tunnel |
| `railway` | Infrastruttura ferroviaria | Railway infrastructure |
| `street_furniture` | Arredo urbano (cabina, palo, cartello) | Street furniture (cabinet, pole, sign) |
| `ground` | Pavimentazione, scala | Pavement, steps |
| `free_standing` | Struttura autonoma | Free-standing structure |
| `other` | Altro | Other |

## Testing Decisions

- Test external behaviour only: the archive domain's public interface (read views, the write operation, derivations), the API's responses, and the rendered pages. Never assert on table layouts or private helpers.
- **Archive domain (unit, pytest)**: Uncertain date construction and the precision × qualifier matrix; Condition derivation over sequences of History events, including `condition recorded`, disappearance, and ordering by chronological key, ties, and `unknown`-dated events; range derivation for every precision × qualifier; the at-least-one-condition-changing-event invariant; Condition group mapping; Evidence level derivation, including record-level citations not counting; Attribution rules (`confirmed` needs a citation, collaboration, disputed alternatives); the image-shows-a-single-Location rule; the boundary and self-intersection checks; that no operation deletes Artworks or Locations.
- **Persistence and API (integration, pytest against PostGIS)**: Area membership by geometry, including overlapping Areas; one Revision per touched record in one transaction; visibility of pending content by caller (public, Submitter, Moderator, other User); 301 for slugs and Merge, 410 for Withdrawal, 404 for pending-only records; Moderation notes never returned to non-Moderators.
- **Pages (end-to-end, Playwright with axe)**: each record page kind in both UI languages, through the state matrix in acceptance criterion 34; keyboard-only reading of gallery and Timeline; rendering without WebGL2; grayscale check of the three signs.
- **i18n**: the missing-key check covers every Condition, History event type, certainty, Evidence level, Uncertain date, and vocabulary label message.
- Test data uses fictional records only, marked as fictional, with no claims about real artworks or artists.
- Prior art: none in the repository yet; this is among the first feature specs to be implemented. The throwaway prototypes on `prototype/17-status-presentation` and `prototype/27-submission-form` show the intended presentation and are not test fixtures.

## Out of Scope

- Writing records: the Submission form, lifecycle, moderation queue, Outdated computation, and Merge mechanics (Contribution and moderation).
- Withdrawal, Redaction, Reinstatement, Purge, Notices, and their logs and statements of reasons (Rights and legal actions).
- The map: markers, clustering, overlays, cartography, the basemap, and map/list sync (Discovery). The Explore and Archive views, search, and filters (Discovery).
- Uploading, validating, and rendering media files (Foundations media pipeline).
- Email notifications (Notifications).
- Public data dumps (Operations and portability).
- Custom metadata fields, video and audio Documentation items, bulk import (so Areas are not seeded from official datasets), cross-Instance Artists, a User–Artist claim, translated content, public User profiles, and any engagement mechanics (likes, follows, popularity ranking, view counters).
- SEO metadata beyond the URL scheme of ADR 0010.

## Further Notes

### Open items

The inputs leave these questions unsettled. Implementers must not fill them by assumption; each needs a decision (a resolution comment or an ADR) before the affected ticket is built.

1. **History event type list and Condition mapping.** Answered by [History event types and Uncertain-date ordering](https://github.com/spippoli/tart/issues/89): nine types, seven of them condition-changing; see Physical history.
2. **"Most recent" with Uncertain dates.** Answered by [History event types and Uncertain-date ordering](https://github.com/spippoli/tart/issues/89): the chronological key with ties broken by later approval; see Uncertain date.
3. **Artwork with no condition-changing event.** Answered by [History event types and Uncertain-date ordering](https://github.com/spippoli/tart/issues/89): such a Submission is rejected; with no public condition-changing event the Condition shows `unknown` ("state not documented"); see Physical history.
4. **Range derivation.** Answered by [History event types and Uncertain-date ordering](https://github.com/spippoli/tart/issues/89): see Uncertain date; `unknown` is a precision only.
5. **Relocation and the Location field.** Answered by [History event types and Uncertain-date ordering](https://github.com/spippoli/tart/issues/89): there is no `relocated` type; a detached piece is `removed` on its original Location, and the Location field changes only by correction (ADR 0003 amended).
6. **Stratigraphy order.** Answered by [History event types and Uncertain-date ordering](https://github.com/spippoli/tart/issues/89): by the chronological key of the Creation event, else first documentation, most recent first; see Location.
7. **Descriptive fields of Site, Area, Series, and Source.** Answered by [Record descriptive fields, text alternatives and slugs](https://github.com/spippoli/tart/issues/90): Sites, Areas, and Series have an optional description; a Source has Title (required), Author, Publication, Date, URL, Note, and Language; a period is a start and an end, each an optional Uncertain date.
8. **Series membership cardinality.** Answered by [Record descriptive fields, text alternatives and slugs](https://github.com/spippoli/tart/issues/90): an Artwork may belong to zero or more Series; a collective may be a member of another collective, without cycles.
9. **Location text.** Answered by [Record descriptive fields, text alternatives and slugs](https://github.com/spippoli/tart/issues/90): an optional one-line Place description, which also gives the Location's title, with a composed fallback; the route stays slugless.
10. **Image text alternatives.** Answered by [Record descriptive fields, text alternatives and slugs](https://github.com/spippoli/tart/issues/90): a required alt text on image Documentation items, written by the Submitter and checked by the Moderator; no separate caption; a platform alt text for PDF previews.
11. **Slug for untitled records.** Answered by [Record descriptive fields, text alternatives and slugs](https://github.com/spippoli/tart/issues/90): an untitled record is canonical at the bare id; see Public record pages for the slug derivation.
12. **Withdrawal effects beyond Artists.** ADR 0014 settles a withdrawn Artist. Not settled: whether a Claim whose only citation is a withdrawn Documentation item or Source becomes `reported`, whether a `confirmed` Attribution then stays valid, how a withdrawn Artwork appears in its Location's stratigraphy, Series, or as a covering-Artwork link, and what a withdrawn Location means for its Artworks. These belong to Rights and legal actions but change what record pages show.
13. **Public provenance details.** Decided: `/revisions` shows the Submitter's display name. Not decided: whether the approving Moderator's name is public, whether the Timeline names the Submitter of each History event (handed from [#4](https://github.com/spippoli/tart/issues/4) to [#14](https://github.com/spippoli/tart/issues/14), which settled only `/revisions`), and how a Revision's content is shown on `/revisions` (snapshot or change list).
14. **Public file rights fields.** The licence notice and Creator credit must be public; whether the Rights basis and a third party's origin URL are shown publicly is not decided.
15. **Deliberate position obfuscation.** Handed from [#4](https://github.com/spippoli/tart/issues/4) to [#14](https://github.com/spippoli/tart/issues/14): whether a Location's public position may be deliberately coarsened (fragile or private-property pieces), separate from the approximate flag. The resolution of #14 does not address it.
16. **Public signal of pending Submissions.** [#15](https://github.com/spippoli/tart/issues/15) decided that the public sees nothing; ADR 0015 still lists as open whether the public sees that a record has Submissions under review. This spec follows #15.
17. **Timeline dates for Documentation items.** ADR 0015 requires the three dates for History events; whether Documentation items on the Timeline also show submitted and approved dates is not stated.
18. **Index ordering.** Answered by [Search and filters](https://github.com/spippoli/tart/issues/41), as compiled in [Discovery](discovery.md#index-name-filter): alphabetical by name in the Content language, with a "Filter by name" field (name plus Aliases for Artists) and pagination by 24; see Indexes.
19. **Default Surface type list.** Answered by [Record descriptive fields, text alternatives and slugs](https://github.com/spippoli/tart/issues/90): see Instance configuration.
20. **Mini-map fallback without WebGL2.** Answered by [Map behaviour: clustering, geometries, overlays, stratigraphy](https://github.com/spippoli/tart/issues/39), as compiled in [Discovery](discovery.md#mini-map): no server-rendered image; a text box with Location, Areas, Site, the approximate notice, coordinates, and an "Open in a maps app" `geo:` link replaces it.

### Notes

- Whether disappeared Artworks are shown on the map by default is a Discovery question (ADR 0015 open item); this spec only guarantees their records and pages.
- The legal-review items that touch records (lawfulness of publishing photos of in-copyright works, whether pseudonymous Attributions of unauthorised works are Art. 10 GDPR data) are carried in ADRs 0012 and 0014 and do not change this spec's behaviour.
- The traceability table in the index lists [#5](https://github.com/spippoli/tart/issues/5), [#14](https://github.com/spippoli/tart/issues/14), and [#27](https://github.com/spippoli/tart/issues/27) as feeding other specs; this spec also draws on them for record-shaping rules, as listed under References.
