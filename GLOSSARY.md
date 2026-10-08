# TART

TART is a collaborative platform for documenting and preserving the history of urban art. Each deployment runs one local archive, maintained by a community through moderated contributions.

## Language

### Platform

**Instance**:
One deployment of TART serving one local archive (e.g. Rome), with its own configuration, users, and data.
_Avoid_: Tenant, site, city

### Archive

**Artwork**:
A single physical urban art intervention, of any kind, that occupies, or once occupied, a Location.
_Avoid_: Mural (as a generic term), piece, work, item

**Expression type**:
A kind of urban expression (e.g. mural, graffiti, stencil, paste-up, sticker, installation), drawn from the Instance's configured vocabulary; an Artwork has one or more.
_Avoid_: Category, genre, medium

**Location**:
The physical surface an Artwork occupies (a wall, façade, pole, pavement, shutter), drawn as a point, line, or polygon and marked exact or approximate; one Location can host many Artworks, side by side or in succession, has no Condition of its own, and is never deleted.
_Avoid_: Spot, place, wall, support, address

**Surface type**:
The kind of physical surface a Location is, drawn from the Instance's configured vocabulary.
_Avoid_: Support, medium

**Site**:
A named grouping of nearby Locations, such as a hall of fame or a legal wall; a Location belongs to at most one Site.
_Avoid_: Spot, area, zone, hall of fame (as the entity name)

**Area**:
A named geographic region (e.g. a rione, quartiere, or municipio) drawn as a polygon; Areas may overlap, Locations fall within them by geometry, and Areas may be used as an Artist's areas of activity.
_Avoid_: Zone, district, neighbourhood (as the entity name)

**Series**:
A named grouping of Artworks connected by intent (same subject or project), regardless of where they are.
_Avoid_: Collection, set, project

**Documentation item**:
An independent piece of evidence of physical state (image, PDF, text, or link) about one or more Artworks, dated by its Observed date; an image shows a single Location, and only documentation of a disappearance links to the Location itself.
_Avoid_: Media, attachment, upload, photo (as the generic term)

**Condition**:
The physical state of an Artwork (intact, deteriorated, damaged, modified, covered, removed, destroyed, missing, unknown), always derived from its most recent condition-changing History event.
_Avoid_: Status (reserved for Submissions)

**Missing**:
The Condition of an Artwork that could no longer be found, with the cause unknown.
_Avoid_: Deleted, gone

### Physical history

**History event**:
A dated, documented occurrence in an Artwork's physical life, such as damage, overpainting (optionally linked to the covering Artwork), relocation between Locations, removal, destruction, or an attribution change.
_Avoid_: Change, edit, update, log entry

**Timeline**:
The chronological presentation of an Artwork's History events and Documentation items; never includes Revisions.
_Avoid_: History (unqualified)

**Uncertain date**:
A historical date expressed as an earliest–latest range with a precision (day, month, year, decade, unknown) and a qualifier (exact, circa, before, after).
_Avoid_: Fuzzy date, approximate date

**Observed date**:
The Uncertain date on which a Documentation item or History event shows the Artwork's state; distinct from when it was submitted or approved.
_Avoid_: Photo date, upload date

### Evidence

**Source**:
A citable external reference (article, book, artist's own publication) that can be cited by Artworks, Artists, Sites, Areas, Attributions, and History events.
_Avoid_: Link, citation (as an entity name)

**Evidence level**:
Whether a claim is *documented* (supported by a cited Source or Documentation item) or *reported* (a community statement without supporting evidence).
_Avoid_: Verified, trusted, confidence

### People

**Artist**:
A public creative identity (an individual or a collective) to which Artworks may be attributed; never a legal identity.
_Avoid_: Author, creator, user

**Alias**:
An alternative public name under which an Artist is known.
_Avoid_: Tag (ambiguous with the artwork form), AKA

**Crew membership**:
A relation stating that one Artist is a member of a collective Artist.
_Avoid_: Group, team

**Attribution**:
A claim linking an Artwork to an Artist, with a certainty of confirmed, probable, or disputed; an Artwork without Attributions has unknown authorship.
_Avoid_: Authorship, credit, signature

**User**:
A registered account on an Instance; never implies control over any Artist.
_Avoid_: Contributor (as an entity), member, account holder

**Moderator**:
A role held by a User that permits reviewing Submissions.
_Avoid_: Admin, editor, reviewer

**Submitter**:
The User who authored a given Submission.
_Avoid_: Author, uploader

### Contribution and record keeping

**Submission**:
A proposed changeset with one primary target (a new or existing Archive record) that may also create or link related records, Sources, and Documentation items; it becomes part of the archive only once approved, as a whole.
_Avoid_: Proposal, change request, contribution, edit

**Archive record**:
An approved, authoritative Artwork, Artist, Location, Site, Series, or Area as published to the public.
_Avoid_: Entry, listing

**Revision**:
A version of an Archive record produced by one approved Submission; the sequence of Revisions is the record's audit trail.
_Avoid_: History, edit, change log

**Merge**:
Folding a duplicate Archive record into another of the same kind, with the duplicate's identifier redirecting to the survivor.
_Avoid_: Delete, dedupe

**Withdrawal**:
Hiding an Archive record or Documentation item from the public for legal, rights, or privacy reasons; not a physical Condition and never shown on the Timeline.
_Avoid_: Deletion, takedown, removal (reserved for the physical History event)
