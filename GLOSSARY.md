# TART

TART is a collaborative platform for documenting and preserving the history of urban art. Each deployment runs one local archive, maintained by a community through moderated contributions.

## Language

### Platform

**Instance**:
One deployment of TART serving one local archive (e.g. Rome), with its own configuration, users, and data.
_Avoid_: Tenant, site, city

**Operator**:
The person or organisation that runs an Instance: it owns the Instance configuration and the server, assigns roles, and answers for the Instance's legal duties; it is not a User role.
_Avoid_: Admin, owner, host

**Instance configuration**:
The settings that define what an Instance's archive is (identity, geography, languages, open vocabularies, policies, licences, and the Operator's own texts), set by the Operator and never edited through Submissions.
_Avoid_: Settings, preferences, Instance data

**Data licence**:
The licence under which an Instance publishes its structured archive data, chosen by the Operator from a fixed list of open licences; it never covers Documentation item files or the depicted Artworks.
_Avoid_: Archive licence, content licence

**Data dump**:
An export of the current state of an Instance's public archive data under its Data licence, produced by the Operator and published at the Operator's discretion; it holds no Revisions and no Users.
_Avoid_: Backup (the private, encrypted copy for restore), export (an individual User's data)

**Licensor**:
The holder who offers the TART software under its license and holds the TART name and logo; distinct from every Operator.
_Avoid_: Owner, maintainer (as the legal role)

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

**Creator credit**:
The name, possibly a pseudonym, credited as the creator of a Documentation item's file; independent of the Submitter who uploaded it.
_Avoid_: Author, photographer, uploader

**Rights basis**:
The Submitter's declaration of why a Documentation item's file may be published: either it is their own work, or it is a third party's work already under a licence the Instance accepts.
_Avoid_: Permission, copyright status

**Condition**:
The physical state of an Artwork (intact, deteriorated, damaged, modified, covered, removed, destroyed, missing, unknown), always derived from its most recent condition-changing History event.
_Avoid_: Status (reserved for Submissions)

**Missing**:
The Condition of an Artwork that could no longer be found, with the cause unknown.
_Avoid_: Deleted, gone

**Condition group**:
One of three groupings of Conditions: *present* (intact, deteriorated, damaged, modified), *disappeared* (covered, removed, destroyed, missing), or *unknown*; it says whether an Artwork can still be seen where it is, never whether its record is public.
_Avoid_: Visible, no longer visible, existing, gone, status

### Physical history

**History event**:
A dated occurrence in an Artwork's physical life, such as creation, damage, overpainting (optionally linked to the covering Artwork), a Condition record, removal (including detachment of a piece taken elsewhere), destruction, or a real-world attribution change (e.g. an artist publicly claiming a piece); a correction to an Attribution is a Revision, not a History event.
_Avoid_: Change, edit, update, log entry

**Condition record**:
A `condition recorded` History event stating the Condition an Artwork was observed in on its Observed date (e.g. intact after a restoration, or the Condition given when a new Artwork is documented), without asserting a change.
_Avoid_: Status update, check-in, condition field

**Creation event**:
The `created` History event that states when an Artwork was made; an Artwork without one has an unknown creation date, which is distinct from its first documentation (the earliest Observed date of its Documentation items).
_Avoid_: Creation date (as a field), first seen

**Timeline**:
The chronological presentation of an Artwork's History events and Documentation items; never includes Revisions.
_Avoid_: History (unqualified)

**Uncertain date**:
A historical date given as one or two values at a precision (day, month, year, decade, unknown) with a qualifier (exact, circa, before, after), from which an earliest–latest range is derived; an unknown date has no value and no qualifier.
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
A public creative identity (an individual or a collective) to which Artworks may be attributed, named only by the names it publicly uses as an artist, optionally with an Uncertain date period of activity; never a legal identity.
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

**Invitation**:
A single-use offer, issued by a Moderator or the Operator to one email address, that lets that person register on an Instance whose registration is by invitation; it expires and can be revoked while unused.
_Avoid_: Invite code, referral

**Moderator**:
A role held by a User that permits reviewing Submissions, handling Notices, and performing Withdrawals, Redactions, and Reinstatements; it is the only User role.
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
A remark on a Submission, a Notice, a Withdrawal, or a Redaction, visible only to Moderators and never changed once written.
_Avoid_: Comment, internal message

**Moderator digest**:
A daily email to a Moderator summarising the Submissions waiting for review, sent only when new ones have arrived since the previous digest; a Moderator may choose it instead of one email per Submission, or no email at all.
_Avoid_: Newsletter, notification feed

**Archive record**:
An approved, authoritative Artwork, Artist, Location, Site, Series, Area, Source, or Documentation item as published to the public.
_Avoid_: Entry, listing

**Revision**:
A version of one Archive record produced by an approved Submission; a Submission yields one Revision for each Archive record it creates or changes, and the sequence of Revisions is the record's audit trail.
_Avoid_: History, edit, change log

**Merge**:
Folding a duplicate Archive record into another of the same kind, with the duplicate's identifier redirecting to the survivor; it applies to every kind except Documentation items.
_Avoid_: Delete, dedupe

**Duplicate retirement**:
Setting a duplicate Documentation item aside in favour of another one, with its identifier redirecting to the kept item and its links and citations moving to it; the two items' content is never reconciled, and the retired item is kept in the archive but no longer shown.
_Avoid_: Deletion, Merge (reserved for the other record kinds), Withdrawal (reserved for legal reasons)

**Unmerge**:
Undoing a Merge or a Duplicate retirement through a Submission that brings the folded record back under its own identifier.
_Avoid_: Split, undo, Reinstatement (reserved for Withdrawal and Redaction)

**Withdrawal**:
Hiding an Archive record or Documentation item from the public for legal, rights, or privacy reasons; not a physical Condition and never shown on the Timeline.
_Avoid_: Deletion, takedown, removal (reserved for the physical History event)

**Redaction**:
Hiding from the public, for legal, rights, or privacy reasons, selected operations of one or more Revisions of one Archive record (up to whole Revisions), including a value that is still current, while the record itself stays public.
_Avoid_: Censoring, Withdrawal (reserved for whole records and Documentation items)

**Reinstatement**:
Undoing a Withdrawal or a Redaction so the hidden content is public again.
_Avoid_: Restore, undelete

**Purge**:
The permanent erasure of withdrawn or redacted content, done only when the law requires it; the only way content ever leaves the archive.
_Avoid_: Deletion, Withdrawal

**Erasure log**:
The content-free list of every Purge, account deletion, and Creator credit anonymisation, kept so that erasures are applied again after a restore from backup.
_Avoid_: Deletion log, Purge log

**Notice**:
A report, from anyone and without an account, that a public Archive record or Documentation item is unlawful or infringes someone's rights; it is closed by a decision of Withdrawal, Redaction, or no action.
_Avoid_: Flag, complaint, takedown request
