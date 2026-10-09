# TART

TART is a collaborative platform for documenting and preserving the history of urban art. Each deployment runs one local archive, maintained by a community through moderated contributions.

## Language

### Platform

**Instance**:
One deployment of TART serving one local archive (e.g. Rome), with its own configuration, users, and data.
_Avoid_: Tenant, site, city

**UI language**:
A language the TART interface is offered in; the platform ships each one complete, and an Instance enables a subset and picks a default.
_Avoid_: Locale (as a domain term), interface translation

**Content language**:
The single language in which an Instance's archive content and own texts are written (e.g. Italian for Rome); it is never translated and may differ from the UI language a visitor reads.
_Avoid_: Default language, archive language

### Archive

**Artwork**:
A single physical urban art intervention, of any kind, that occupies, or once occupied, a Location.
_Avoid_: Mural (as a generic term), piece, work, item

**Expression type**:
A kind of urban expression (e.g. mural, graffiti, stencil, paste-up, sticker, installation), drawn from the Instance's configured vocabulary; an Artwork has one or more.
_Avoid_: Category, genre, medium

**Location**:
The physical surface an Artwork occupies (a wall, façade, pole, pavement, shutter), drawn as a point, line, or polygon and marked exact or approximate (an approximate point may carry an uncertainty radius); one Location can host many Artworks, side by side or in succession, has no Condition of its own, and is never deleted.
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
A dated occurrence in an Artwork's physical life, such as creation, damage, overpainting (optionally linked to the covering Artwork), relocation between Locations, removal, destruction, or a real-world attribution change (e.g. an artist publicly claiming a piece); a correction to an Attribution is a Revision, not a History event.
_Avoid_: Change, edit, update, log entry

**Creation event**:
The `created` History event that states when an Artwork was made; an Artwork without one has an unknown creation date, which is distinct from its first documentation (the earliest Observed date of its Documentation items).
_Avoid_: Creation date (as a field), first seen

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

**Claim**:
An Attribution or a History event: a statement about an Artwork that carries an Evidence level; all other fields are record data whose provenance is the Revision that introduced them.
_Avoid_: Fact, assertion

**Source**:
A citable external reference (article, book, artist's own publication) that can be cited by Artworks, Artists, Sites, Areas, Attributions, and History events.
_Avoid_: Link, citation (as an entity name)

**Evidence level**:
Whether a Claim is *documented* (it cites at least one Source or Documentation item) or *reported* (it cites nothing); always derived from the Claim's citations, never set by hand.
_Avoid_: Verified, trusted, confidence

### People

**Artist**:
A public creative identity (an individual or a collective) to which Artworks may be attributed, optionally with an Uncertain date period of activity; never a legal identity.
_Avoid_: Author, creator, user

**Alias**:
An alternative public name under which an Artist is known.
_Avoid_: Tag (ambiguous with the artwork form), AKA

**Crew membership**:
A relation stating that one Artist is a member of a collective Artist, optionally over an Uncertain date period.
_Avoid_: Group, team

**Attribution**:
A Claim linking an Artwork to an Artist, optionally naming the Alias it was signed with, with a certainty of confirmed (which requires a citation), probable, or disputed; several non-disputed Attributions mean a collaboration, competing alternatives are all disputed, and an Artwork without Attributions has unknown authorship.
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

**Submission status**:
Where a Submission stands: draft, submitted, changes requested, approved, rejected, or retracted; approved, rejected, and retracted are final.
_Avoid_: State, Condition (reserved for Artworks)

**Changes requested**:
The Submission status in which a Moderator has sent a Submission back to its Submitter for revision before deciding; resubmitting it returns it to submitted.
_Avoid_: Pending, on hold

**Retraction**:
The Submitter cancelling their own Submission before a decision is made.
_Avoid_: Withdrawal (reserved for legal hiding), cancellation, deletion

**Base revision**:
The Revision of an existing Archive record that an edit Submission was written against.
_Avoid_: Parent, original

**Outdated**:
Said of an edit Submission whose changes overlap with fields or items changed since its Base revision, or whose target has been merged or withdrawn; it cannot be approved until revised.
_Avoid_: Stale, conflicted

**Submission log**:
The dated record of a Submission's status changes, each with its actor and any Decision message; it is the moderation history, distinct from both Revisions and the Timeline.
_Avoid_: Audit trail (reserved for Revisions), history

**Decision message**:
The explanation a Moderator gives the Submitter when rejecting a Submission or requesting changes, made of a reason from the Instance's configured list plus free text.
_Avoid_: Feedback, comment

**Moderation note**:
A remark on a Submission visible only to Moderators.
_Avoid_: Comment, internal message

**Archive record**:
An approved, authoritative Artwork, Artist, Location, Site, Series, Area, Source, or Documentation item as published to the public.
_Avoid_: Entry, listing

**Revision**:
A version of one Archive record produced by an approved Submission; a Submission yields one Revision for each Archive record it creates or changes, and the sequence of Revisions is the record's audit trail.
_Avoid_: History, edit, change log

**Merge**:
Folding a duplicate Archive record into another of the same kind, with the duplicate's identifier redirecting to the survivor.
_Avoid_: Delete, dedupe

**Withdrawal**:
Hiding an Archive record or Documentation item from the public for legal, rights, or privacy reasons; not a physical Condition and never shown on the Timeline.
_Avoid_: Deletion, takedown, removal (reserved for the physical History event)
