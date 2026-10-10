# Contribution and moderation

Feature spec 4 of 7 in the [delivery order](index.md#delivery-order). It defines how the archive is written: the **Submission** model and its lifecycle, the Submission form (the editor), duplicate detection, **Merge**, **Duplicate retirement** and **Unmerge**, and the Moderator role, its permissions, the review queue, and **Invitations**. It covers Journeys B, C, D and E of the brief (`README.md` §11). Compile ticket: [Compile Contribution and moderation spec](https://github.com/spippoli/tart/issues/53).

Every section except Further Notes is normative. The invariants, language rules, and implementation principles in [`CLAUDE.md`](../../CLAUDE.md) apply and override any reading of this spec that contradicts them. Terms in **bold** are [glossary](../../GLOSSARY.md) terms and carry exactly that meaning.

## References

**ADRs applied**

| ADR | What this spec takes from it |
|---|---|
| [0001](../adr/0001-one-instance-per-deployment.md) | Users, roles, and Submissions are local to one Instance |
| [0002](../adr/0002-every-change-is-a-submission.md) | Every change, a Moderator's included, is a Submission; whole-Submission approval; one Revision per touched record; Moderators never amend content; undo is a new Submission; Withdrawal is not a Submission |
| [0003](../adr/0003-location-as-shared-physical-surface.md) | The Location step reuses or creates a shared surface; an image shows a single Location |
| [0006](../adr/0006-derived-evidence-level.md) | Live Evidence level readout in the form; `confirmed` needs a citation; Moderators judge sources at review, never through a flag |
| [0007](../adr/0007-edit-submissions-as-field-changesets.md) | Edits as field- and item-level changesets against a Base revision; rebase on approval; Outdated; the rule on related records |
| [0008](../adr/0008-single-content-language-and-prefixed-ui-languages.md) | Submitted content is in the Content language; stable API error codes translated by the frontend; email language |
| [0009](../adr/0009-instance-configuration-as-validated-files.md) | Decision message reasons as an open vocabulary; `retired` entries not selectable; boundary check; `registration`; `draft_expiry_days`; `max_upload_mb`; Moderator role CLI; Invitations; `self_approval` (amended by [#43](https://github.com/spippoli/tart/issues/43)) |
| [0010](../adr/0010-public-url-scheme.md) | Translated path segments; 301 after Merge and Duplicate retirement without chains |
| [0012](../adr/0012-per-file-licence-with-rights-basis.md) | Per-file licence, Creator credit, Rights basis; link instead of upload; EXIF only as suggestions; terms accepted before the first Submission and when they change |
| [0013](../adr/0013-hide-not-delete-for-legal-removals.md) | Rejection carries an Art. 17 statement of reasons; screening for people and number plates; blurred re-upload instead of a blurring tool; account deletion retracts open Submissions |
| [0014](../adr/0014-artist-records-hold-only-a-public-identity.md) | Public-name-only Artists; no legality claims; "I made this" is not a citation; Artists correct records through ordinary edit Submissions |
| [0015](../adr/0015-condition-and-uncertainty-presentation.md) | Proposed content drawn hatched with a dashed outline and labelled as under review; it never changes the displayed Condition |
| [0018](../adr/0018-merge-as-reconciling-multi-record-submission.md) | Merge, Duplicate retirement and Unmerge as reconciling Submissions with Revisions on every referencing record; ordinary Moderator duty |

**Glossary terms applied**: Instance, Operator, Instance configuration, Content language, UI language, User, Invitation, Moderator, Submitter, Submission, Submission status, Changes requested, Retraction, Base revision, Outdated, Submission log, Decision message, Moderation note, Moderator digest, Archive record, Revision, Merge, Duplicate retirement, Unmerge, Withdrawal, Redaction, Reinstatement, Notice, Artwork, Expression type, Location, Surface type, Site, Area, Series, Documentation item, Creator credit, Rights basis, Condition, Condition group, History event, Condition record, Creation event, Uncertain date, Observed date, Claim, Source, Evidence level, Artist, Alias, Crew membership, Attribution.

**Decision tickets incorporated**: [Core domain model and glossary](https://github.com/spippoli/tart/issues/3) (Submission targets), [Uncertainty and provenance model](https://github.com/spippoli/tart/issues/4) (validation), [Submission and moderation lifecycle](https://github.com/spippoli/tart/issues/5), [Content rights and GDPR product rules](https://github.com/spippoli/tart/issues/14) (upload rights fields, terms, screening), [Information architecture and page inventory](https://github.com/spippoli/tart/issues/15) (hub, Submission page, queue, routes), [Status, uncertainty and condition presentation rules](https://github.com/spippoli/tart/issues/17) (proposal preview), [Submission form flow](https://github.com/spippoli/tart/issues/27), [Duplicate detection and Merge](https://github.com/spippoli/tart/issues/42), [Moderation roles and permissions](https://github.com/spippoli/tart/issues/43), [List alternative and map/list sync](https://github.com/spippoli/tart/issues/40) (Location step entry modes and the step without WebGL2). [Notifications](https://github.com/spippoli/tart/issues/44) is cited only for the emails that lifecycle transitions trigger.

**Depends on**: [Foundations](foundations.md) (Instance configuration, authentication and sessions, media pipeline, i18n shell, Operator CLI), [Archive records](archive-records.md) (record model, the archive write operation, Revisions, pending-content display on record pages), and Discovery (the map module, used by the Location step and the Submission page).

## Problem Statement

A community archive is only as good as the way it is written. Contributors in Rome see a new stencil on a shutter, notice that a mural has been painted over, or know who made a paste-up. They need to record that from a phone in the street, saying how sure they are, without a form that demands what they cannot know, and without their guess ending up published as fact. Several people will document the same wall, so the archive has to catch duplicates before they multiply and repair them when they slip through, without losing either record's history.

The volunteer Moderators who keep the archive reliable need to see exactly what a contribution changes against the current record, check the files for rights and for people's faces, judge the evidence, and either accept the whole contribution or send it back with a reason. Their decisions must be traceable, must not collide when two Moderators look at the same item, and rejections must meet the Digital Services Act duty to give reasons. A small community starts with one Moderator, so the rules on reviewing one's own work have to bend for launch without becoming invisible.

## Solution

Every change to the archive is a **Submission** (ADR 0002). A Submission has one primary target, may create or link related records, and becomes part of the archive only when a Moderator approves it as a whole. Edits are field- and item-level changesets against a **Base revision**, so unrelated approvals rebase silently and only real conflicts make a Submission **Outdated** (ADR 0007).

Contributors write Submissions in one stepper editor whose steps depend on the kind of contribution: a new Artwork, an edit, added documentation, a History event (including disappearance), or a new Artist. Drafts are saved on the server as the contributor works. Proposed content is previewed in the archive's editorial label, hatched and marked as not public. Possible duplicates are shown where they can still be avoided: when a Location is chosen, and when a named record is created.

Moderators work from a FIFO queue without claiming. Each Submission has one page shared by its Submitter and Moderators, showing current against proposed data, the **Submission log**, and the **Decision messages**. A Moderator approves, rejects, or requests changes, never edits. A fixed review checklist sits beside the decision buttons. Duplicates that reached the archive are folded with a reconciling **Merge** (or a **Duplicate retirement** for Documentation items), which any User may propose and an **Unmerge** can undo (ADR 0018).

Moderator is the only User role, granted by the Operator from the CLI. Whether a Moderator may approve their own Submission is the `self_approval` key. No Submission skips review.

## User Stories

**Starting and writing a Submission**

1. As a signed-in User, I want a Contribute hub with "document a new artwork", the editorial guidelines, the contribution licence, and a link to my contributions, so that I know where to start and on what terms.
2. As a signed-in User, I want to propose an edit, add documentation, or record a condition change from the Artwork page, so that I contribute from where I noticed something.
3. As an anonymous visitor, I want a contribution action to send me to sign-in and back, so that I don't lose my place.
4. As a contributor, I want the editor split into numbered steps that I can visit in any order, so that I fill in what I know first.
5. As a contributor, I want my draft saved on the server automatically, with the time of the last save shown, so that I never lose work on a phone.
6. As a contributor, I want to leave and resume a draft later, landing on the first incomplete step with a notice, so that I can finish when I have the information.
7. As a contributor, I want to delete a draft, so that I can abandon a contribution cleanly.
8. As a contributor, I want validation only when I submit, with a summary linking to each problem and every step marked complete, to complete, or to fix in words, so that I am never blocked while moving between steps.

**Documenting a new Artwork (Journey B)**

9. As a contributor, I want to choose an existing Location or draw a new one as a point, a line, or a simple polygon by clicking, so that I can describe a wall, a pole, or a pavement.
10. As a keyboard-only or touch-screen contributor, I want a crosshair mode with an "Add vertex here" button, so that I can place a geometry precisely without a mouse.
11. As a contributor, I want to mark a Location as approximate, with an uncertainty radius for a point, so that I don't claim more precision than I have.
12. As a contributor, I want to see the Artworks already on or near the Location I chose, including disappeared ones, with a way to add documentation to one of them, so that I don't create a duplicate.
13. As a contributor, I want to upload several files, each with its Observed date prefilled from the photo when available, so that I document quickly.
14. As a contributor, I want to give each file its Rights basis, Creator credit, and licence, with a reminder that the licence covers the file only, so that I publish only what I may.
15. As a contributor, I want a link to count as documentation, so that I can document a vanished work from a publication I may not upload.
16. As a contributor, I want to be asked explicitly what state the Artwork was in on the latest document, so that the archive never assumes it is intact.
17. As a contributor, I want to enter the title or mark it explicitly Untitled, choose Expression types, and write a description, so that the record says what the work is.
18. As a contributor, I want to say the authorship is unknown, or attribute it with a certainty, so that I never overstate who made it.
19. As a contributor, I want to create a new Artist inline, with a reminder that only public artist names are allowed, so that I can attribute a work to an Artist not yet in the archive.
20. As a contributor, I want to enter uncertain dates as a qualifier, a precision, and a value, with a live readout such as "c. 2019", so that I can say exactly how sure I am.
21. As a contributor, I want to cite Sources, so that my Claims are documented.
22. As a contributor, I want a preview of my contribution in the archive's own label, marked "Proposed · not public until approved", so that I see what Moderators will review.
23. As a contributor, I want to leave a note to the Moderators that is never public, so that I can explain something or answer their request.

**Contributing to an existing record (Journeys C and D)**

24. As a contributor, I want to choose which fields I change and see the current value beside my proposal, so that my edit is precise.
25. As a contributor, I want to add documentation and say whether it shows a change, so that a new photo can also record a History event.
26. As a contributor, I want to record a History event, including a disappearance, with its Observed date, its evidence, and a live Evidence level, so that the physical history grows with sources.
27. As a contributor, I want to link the Artwork that covered this one, existing or created inline, so that the layers of a wall stay connected.
28. As a contributor, I want to report a record as a duplicate of another, so that the archive can be cleaned up.

**Following my Submissions**

29. As a Submitter, I want a page for each of my Submissions showing its status, current against proposed data, and the log of what happened, so that I always know what action is expected of me.
30. As a Submitter, I want My contributions filtered by status, so that I find what needs my attention.
31. As a Submitter, I want to revise and resubmit after changes are requested, so that my contribution can still be accepted.
32. As a Submitter, I want to retract a Submission before a decision, so that I can withdraw a mistake myself.
33. As a Submitter, I want to know when my Submission became Outdated and must be revised against the current record, so that it does not wait forever.
34. As a Submitter, I want every rejection to give a reason and the facts, and to tell me how to contest it, so that the decision is fair and explained.

**Moderating (Journey E)**

35. As a Moderator, I want a queue of open Submissions, oldest first, with filters on kind, labels, target kind, Submitter, Area, and Outdated, so that I can work through it predictably.
36. As a Moderator, I want warnings about overlapping pending Submissions, Outdated ones, and pending create Submissions within 25 m of each other, so that I spot conflicts and duplicates.
37. As a Moderator, I want to compare the proposed data with the current record, and, after a resubmission, see what changed since my last review, so that I don't review twice.
38. As a Moderator, I want the review checklist beside the decision buttons, linked to the editorial guidelines, so that I check people, rights, Artists, legality, evidence, Location, duplicates, and relevance every time.
39. As a Moderator, I want to approve, reject, or request changes, giving a reason and an explanation for the latter two, so that the Submitter knows what to do.
40. As a Moderator, I want to write Moderation notes that only Moderators see, so that we can coordinate without exposing internal remarks.
41. As a Moderator, I want my decision refused, with an explanation and a reload, if another Moderator decided first, so that two decisions never collide.
42. As a Moderator, I want my identity hidden from Submitters, who read "a Moderator", so that I am not personally targeted.
43. As a Moderator, I want to settle two pending Submissions about the same Artwork by approving one and sending the other back with a "duplicate of an existing record" reason, so that the second contributor can turn it into documentation.
44. As a Moderator, I want to approve a Merge that also reconciles the two records' contradictions, so that the surviving record is consistent from the start.
45. As a Moderator, I want Unmerge to bring back a wrongly merged record under its own id, so that no identity is lost by mistake.

**Roles and access**

46. As an Operator, I want to grant, revoke, and list the Moderator role from the CLI, with revocation effective on the next request, so that I control who moderates.
47. As an Operator of a new Instance with a single Moderator, I want to allow self-approval and turn it off later, so that the archive can start without waiting for a second Moderator.
48. As a Moderator on an invite-only Instance, I want to issue, list, and revoke Invitations, so that I can bring new contributors in.
49. As an invited person, I want to register at the invited address with the ordinary email code, so that joining is simple.

**Accessibility and languages**

50. As a keyboard or screen-reader user, I want every step of the editor, including the map, uploads, and the queue, to work without a mouse and without hover, so that I can contribute and moderate.
51. As an Italian or English speaker, I want every label, step state, status, error, and reason in my UI language, while the content I write stays in the Content language, so that the interface reads naturally and the archive stays consistent.

## Implementation Decisions

### Scope and dependencies

- This spec owns the write side of the archive: the Submission store, the lifecycle, validation, the editor, duplicate detection, Merge mechanics, the queue, the Submission page, My contributions, the Contribute hub, the Moderator permission rules, and Invitations.
- Applying an approved changeset uses the single write operation of the Archive records domain ([Archive records](archive-records.md), Modules). This spec decides *when* it is called; Archive records decides what it writes to records, how Condition and Evidence level are derived, and how pending content appears on record pages.
- Withdrawal, Redaction, Reinstatement, Notices, Purge, account deletion, and the statement-of-reasons content belong to the Rights and legal actions spec. This spec owns only the permission rules shared with them (the Moderator role and `self_approval`) and the effect of their states on Submissions (Outdated).
- Email triggers and content belong to the Notifications spec ([#44](https://github.com/spippoli/tart/issues/44)). This spec owns the transitions that trigger them.
- The map module (rendering, cartography, fallback without WebGL2) belongs to Discovery; the editor uses it only through its public interface (ADR 0004).

### Modules

- **Moderation domain** (ports and adapters, per `CLAUDE.md`): the Submission aggregate (target, changeset, Base revisions, rounds, status), the lifecycle state machine, derived kind and labels, Outdated computation, the permission rules (role, `self_approval`, own content), Merge, Duplicate retirement and Unmerge planning (the list of referencing records to rewrite), and validation of a changeset against the current archive. No framework or persistence imports. It calls the Archive domain's write operation on approval.
- **Duplicate detection**: pure functions for the proximity rule and the name rule, behind a query port implemented with PostGIS (distances) and a fuzzy-matching library (names).
- **Moderation persistence**: PostgreSQL repositories for Submissions, rounds, the Submission log, Moderation notes, and Invitations.
- **Contribution API**: endpoints for drafts, autosave, submit, retract, decisions, notes, the queue, duplicate candidates, and Invitations, returning stable error codes (ADR 0008). It never sends Moderation notes or Moderator identities to non-Moderators.
- **Editor, Submission page, queue, hub, My contributions** (frontend): server-rendered pages with all UI strings through the i18n shell; the editor embeds the map module.

### Submission model

- A Submission has one **primary target**: a new or existing Artwork, Artist, Location, Site, Series, or Area ([#3](https://github.com/spippoli/tart/issues/3)). It may create new related records (including Sources and Documentation items) and link existing ones. Sources and Documentation items are Archive records editable through Submissions ([#5](https://github.com/spippoli/tart/issues/5)); see open item 3.
- A Submission never edits a second existing record and never references a record that exists only in another pending Submission (ADR 0007). Merge, Duplicate retirement and Unmerge are the one exception (ADR 0018).
- **Create** Submissions have no Base revision; the changeset is the whole new record and its related records. **Edit** Submissions store the Base revision and a changeset of operations: set a field, or add, change, or remove an item (Attribution, History event, link to a Source or Documentation item) (ADR 0007). A Merge stores two Base revisions (ADR 0018).
- There is one Submission model. Its **kind** is derived, never chosen: target kind × create | edit, plus Merge, Duplicate retirement, and Unmerge. It also carries computed **labels**: adds documentation, adds History event, changes Attribution, changes Condition ([#5](https://github.com/spippoli/tart/issues/5)). Journeys B, C, and D are entry points onto this one structure.
- Documentation item files are immutable; replacing a file means a new Documentation item ([#5](https://github.com/spippoli/tart/issues/5)).
- No Submission stores the Submitter's position. EXIF GPS only prefills a map pin that the Submitter must place (ADR 0012, [Foundations](foundations.md) §3).

### Lifecycle

**Submission status** (closed vocabulary, ADR 0009):

| From | Event | To | Who |
|---|---|---|---|
| — | Start a contribution | `draft` | Submitter |
| `draft` | Submit (validation passes, terms accepted) | `submitted` | Submitter |
| `draft` | Delete draft, or expiry | (deleted, with its media) | Submitter, or the system |
| `submitted` | Approve | `approved` (final) | Moderator |
| `submitted` | Reject, with a Decision message | `rejected` (final) | Moderator |
| `submitted` | Request changes, with a Decision message | `changes requested` | Moderator |
| `changes requested` | Resubmit (validation passes) | `submitted` | Submitter |
| `submitted`, `changes requested` | Retract | `retracted` (final) | Submitter |

- There is no `in review` status ([#5](https://github.com/spippoli/tart/issues/5)).
- **Retraction** is available before a decision; a Submission in `changes requested` may be retracted ([#42](https://github.com/spippoli/tart/issues/42), point 13). Account deletion retracts the User's open Submissions and deletes their drafts (ADR 0013).
- A retry after rejection is a new Submission, optionally linked to the rejected one ([#5](https://github.com/spippoli/tart/issues/5)).
- **Submission log**: every transition is an entry with its actor, date, and message. The Decision message is the message of a reject or changes-requested entry. The Submitter's optional note to Moderators is the message of the `submitted` entry, one per round ([#27](https://github.com/spippoli/tart/issues/27)). The log is the moderation history, distinct from Revisions and from the Timeline.
- **Rounds**: each submission and resubmission is a numbered round with a snapshot of its changeset, so Moderators see what changed since the last review ([#5](https://github.com/spippoli/tart/issues/5)).
- **Drafts** are server-side and private, and their media are never public. A draft is created as soon as a contribution starts. A draft never edited is discarded after 24 hours ([#15](https://github.com/spippoli/tart/issues/15)); an abandoned draft expires after `draft_expiry_days` and its media are deleted ([#5](https://github.com/spippoli/tart/issues/5)). The jobs belong to the Foundations media pipeline; the rules are this spec's.
- Rejected and retracted Submissions stay visible only to their Submitter and to Moderators ([#5](https://github.com/spippoli/tart/issues/5)); their retention is open item 6.

**Outdated** (computed, never a status, ADR 0007):

- An edit Submission is Outdated when any of its operations touches a field or item changed since its Base revision, or when its target has been merged or withdrawn. A Merge, Duplicate retirement, or Unmerge is Outdated when either Base revision moves on, when either record is not public, or when either has an open Notice (ADR 0018).
- An Outdated Submission cannot be approved until its Submitter revises it against the current Revision. How that revision reopens a `submitted` Submission is open item 4.
- Otherwise, on approval, non-overlapping operations are applied to the current Revision.
- The Submitter is emailed once per transition to Outdated while the Submission is `submitted` or `changes requested` (Notifications spec).

**What approval writes** ([#5](https://github.com/spippoli/tart/issues/5)), in one atomic transaction: one Revision per touched record (recording the Submission, Submitter, approving Moderator, first-submitted date, approved date); new records and Documentation items become public; Condition is recomputed; a log entry is added. Observed dates stay on History events and Documentation items. Undo is a new Submission pre-filled from an earlier Revision, never a rollback (ADR 0002).

### Terms of use

- Submitting requires that the User has accepted the Instance's current versioned terms, which hold the contributor warranty and licence grant; acceptance is asked before the first Submission and again when the terms change (ADR 0012). The Review and submit step carries the acceptance ([#27](https://github.com/spippoli/tart/issues/27)). How a terms version is declared is [Foundations](foundations.md) open item 8; whether acceptance is asked on every Submission is open item 10.

### Submission form

**Structure** ([#27](https://github.com/spippoli/tart/issues/27)): a stepper for every kind. One section per step, with a numbered step list that can be navigated freely (not gated). The last step is always **Review and submit**: a preview in the editorial label (ADR 0015), the optional note to Moderators, and acceptance of the terms. Short kinds have fewer steps.

| Kind | Steps |
|---|---|
| New Artwork | Location → Documentation → The Artwork (title or explicit *Untitled*, Expression types, description) → Attribution → Creation date (optional) → Sources → Review and submit |
| Edit | What changes (per field: *Edit* reveals current vs proposed; item-level for Attributions) → Supporting Sources → Review and submit |
| Add documentation | Documentation → "Does it show a change?" (optionally adds a History event citing the new files) → Sources → Review and submit |
| History event (including disappearance) | Event type (grouped as still visible / no longer visible / other), Observed date, optional covering Artwork (existing or created inline) → Evidence (files and Sources, with a live Evidence level readout, *reported* if none) → Review and submit |
| New Artist | Public identity (artist name only, individual or collective, Aliases, biography) → Activity (Uncertain-date period, Areas, Crew memberships) → Sources → Review and submit |

- An edit may move the Artwork to another Location; editing a Location's geometry is a separate Submission on that Location ([#27](https://github.com/spippoli/tart/issues/27)). The relation to a `relocated` History event is [Archive records](archive-records.md) open item 5.
- The steps of the other kinds (new Site, Area, Series, or Source; Location geometry edits; Merge, Duplicate retirement, Unmerge) are open item 3.
- Values from a `retired` vocabulary entry are not selectable in new Submissions (ADR 0009).

**Entry points** ([#15](https://github.com/spippoli/tart/issues/15)): new Artworks from the Contribute hub; edits, documentation, and History events (including disappearance) from record pages; a new Artist from the Artists page or inline within a Submission; a Merge from a record page ("report as duplicate of…") or the form ([#42](https://github.com/spippoli/tart/issues/42)).

**Location step** ([#27](https://github.com/spippoli/tart/issues/27)):

- Choose an existing Location (on the map, or from a text list searched by Site, Area, or text, or among Locations near entered coordinates), or enter a geometry: shape choice Point / Line / Area (default Point).
- Drawing is by clicks only, with no freehand or drag drawing: each click adds a vertex; *Done* closes the line, or the polygon once it has at least 3 vertices; *Undo last vertex*. A vertex is edited by clicking it to select it and clicking elsewhere to move it; *Delete vertex*; clicking a segment midpoint inserts a vertex.
- **Crosshair mode** (alternative, not the default): a fixed crosshair at the map centre, the map panned by arrow keys or dragging, and an *Add vertex here* button. It serves keyboard-only users (WCAG 2.1.1) and precise placement on touch screens.
- **Coordinates field** ([#40](https://github.com/spippoli/tart/issues/40)): a third mode beside click drawing and the crosshair, **always available**, also with the map. It accepts decimal (`41.8986, 12.4769`), degrees-minutes-seconds, a `geo:` URI, or a pasted OpenStreetMap or Google Maps link, and confirms the parsed point in text ("41.8986 N, 12.4769 E, <Area>").
- **"Use my current position"** (Geolocation API), with an explicit reminder that the Location is the artwork's position, not the Submitter's.
- No geocoding or address search.
- Exact or approximate; an approximate point keeps the optional uncertainty radius in metres.
- Self-intersecting polygons and geometries outside the Instance boundary are rejected with a text message.
- The duplicate warning appears here (see Duplicate detection).
- **Without WebGL2** ([#40](https://github.com/spippoli/tart/issues/40)): the existing-Location list, the coordinates field, and the current position remain, and only a **Point** can be entered, with the optional uncertainty radius. For a line or polygon the form explains that drawing needs the map, suggests a representative point with the extent described in the note to Moderators, and notes that the geometry can later be refined by a separate Submission on that Location. The duplicate warning works unchanged, computed server-side from the coordinates and shown as a text list with the "add documentation" exit. The full rules are in [Discovery](discovery.md#location-entry-without-the-map).

**Documentation step** ([#27](https://github.com/spippoli/tart/issues/27), ADR 0012):

- A new Artwork requires at least one Documentation item; a link counts.
- Multiple files per step. Each file carries an Observed date (prefilled from EXIF, with a notice that it is a suggestion), a Rights basis (own work, or third-party work already under an allowlisted licence, with its creator and origin URL), a Creator credit, and a licence from the allowlist, with the notice that it covers the file only. Material that fits neither Rights basis is linked, never uploaded.
- A reminder about identifiable people and number plates.
- The **initial Condition** is asked explicitly and is required: "what state was it in, in the most recent document?", with options grouped as present / disappeared / unknown. The answer creates a **Condition record** dated to the latest Observed date and citing that document. There is no implicit `intact`.
- Upload size is bounded by `max_upload_mb`; file types and processing are the Foundations media pipeline's.

**Common rules** ([#27](https://github.com/spippoli/tart/issues/27)):

- **Autosave** to the server draft, with a status line ("saved automatically · 10:42"), plus *Exit and continue later* and *Delete draft*.
- **Resume**: reopening a draft lands on the first incomplete step with a dismissible notice.
- **Validation** runs only on submit (and resubmit), never blocking navigation between steps. It shows a focused error summary at the top linking to each field, inline text errors bound with `aria-describedby` and `aria-invalid`, and step states as words (complete / to complete / to fix), never colour alone. The server validates again and answers with stable error codes.
- **Uncertain date input**: qualifier, precision, and value, with a live readout ("c. 2019") and the stored range. The input lists the qualifiers exact, circa, before, after, unknown and the precisions day, month, year, decade; how this maps to the glossary's model is [Archive records](archive-records.md) open item 4.
- **Attribution**: unknown authorship is an explicit choice. `confirmed` requires at least one citation (ADR 0006). Several non-disputed Attributions mean collaboration; alternatives are all `disputed`. A new Artist can be created inline, with the public-name-only rule shown (ADR 0014).
- **Preview**: proposed content is drawn hatched with a dashed outline and labelled "Proposed · not public until approved". For History events, the displayed Condition stays unchanged until approval (ADR 0015).
- **Note to Moderators**: optional, in the Review step, never public, stored as the message of that round's `submitted` log entry.
- All free text a Submitter writes is archive content in the Content language and is rendered with its `lang` (ADR 0008).

**Validation rules** (applied on submit and again on approval to the result):

- Every rule of the Archive records model: required fields, the boundary and self-intersection checks, the uncertainty radius on approximate points only, an image showing a single Location, `confirmed` with a citation, at least one Documentation item on a new Artwork, the required initial Condition record ([Archive records](archive-records.md)).
- The related-record rule of ADR 0007 and, for Merge, the merged result's validity and the Artist rules of ADR 0018 (self- or duplicate Crew memberships fail).

### Duplicate detection

**Proximity rule** ([#42](https://github.com/spippoli/tart/issues/42), point 10): a Location is a candidate when the minimum geometry-to-geometry distance is at most 25 m plus the uncertainty radius of each side, if any. 25 m is a platform constant, not Instance configuration. Candidates are ordered by distance.

**Location warning** ([#27](https://github.com/spippoli/tart/issues/27), [#42](https://github.com/spippoli/tart/issues/42), point 12): choosing an existing Location, or placing a geometry within the proximity rule of existing ones, lists the candidates grouped by Location: highlighted geometry, Surface type, Site, and **all** its Artworks, including disappeared ones, with their Condition group signs (ADR 0015). Actions:

- "Add documentation to this Artwork" (leaves this editor for an Add documentation Submission on that Artwork);
- "New Artwork on this Location" (reuses that Location and drops the drawn geometry);
- at the end, "It's another surface", which requires an explicit confirmation and creates a new Location.

Continuing with a new Artwork requires confirming "it is a different Artwork". There is no second check at submission. Whether the Submission reuses or creates a Location is visible to the Moderator.

**Name rule** ([#42](https://github.com/spippoli/tart/issues/42), point 11): when an Artist, Site, Series, Area, or Source is created (in its dedicated form or by "create new" in a link picker), the name is normalized (lowercase, no accents, no punctuation) and compared by fuzzy similarity on a 0–100 scale (for example rapidfuzz `ratio`, MIT) against the name and every Alias of existing records; the best score wins and a score above 90 is a candidate. Sources also match on exact normalized URL. Artwork titles are excluded. The warning never blocks: "use this" or continue.

**Pending duplicates** ([#42](https://github.com/spippoli/tart/issues/42), point 13): Merge is only between Archive records. The queue flags pending create Submissions within 25 m of each other. When two describe the same thing, the Moderator approves one and sets the other to `changes requested` with the platform-provided "duplicate of an existing record" reason, linking the new record. The Submitter may convert it into a documentation Submission on that record, keeping files and dates (open item 12), or retract it.

### Merge, Duplicate retirement, Unmerge

As ADR 0018, with these details from [#42](https://github.com/spippoli/tart/issues/42):

- **Kinds**: Merge applies to Artwork, Artist, Location, Site, Series, Area, and Source. Documentation items are never merged; a duplicate one is set aside by a Duplicate retirement.
- **Shape**: "X into Y" plus an item-level changeset on Y's merged items (for example dropping the wrong `created` event, choosing among Attributions). Field values stay Y's unless the changeset sets them. Validation applies to the merged result.
- **References**: every record referencing X is rewritten to Y and gets its own Revision attributed to the Merge: Artworks on a merged Location, Attributions and Crew memberships of a merged Artist, Locations of a merged Site, Artworks of a merged Series, citations of a merged Source, Areas of activity of a merged Area. Area membership by geometry needs no rewrite. The Moderator sees the list of records to rewrite in the comparison. Redirects are flattened.
- **Artist Merge**: X's name and Aliases are added to Y as Aliases, pre-filled and editable (never a legal name, ADR 0014); Attributions naming an Alias of X name the same Alias on Y.
- **Duplicate retirement**: X's Artwork links, disappearance-Location link, and citations move to Y with Revisions, so no Evidence level drops. File, licence, Creator credit, and fields are never reconciled. It is rejected if the two items' Artworks sit on different Locations (ADR 0003).
- **Unmerge**: brings X back under its own id from its last pre-merge Revision, removes X's items from Y through a changeset, and proposes, pre-filled and editable, re-pointing the records that referenced X before the Merge. It also undoes a Duplicate retirement.
- **Legal states**: both records must be public with no open Notice; otherwise the Submission is Outdated until resolved. Redacted Revisions of X stay redacted.
- **Roles**: any User proposes; approving is an ordinary Moderator duty with no higher tier.
- The public effects (301, the read-only `/revisions` of X with its "merged into" notice) are specified in [Archive records](archive-records.md).

### Roles and permissions

([#43](https://github.com/spippoli/tart/issues/43), ADR 0009 amended)

- **Moderator** is the only User role. It covers Submission review (Merge, Duplicate retirement, and Unmerge included), Notice handling, Withdrawal, Redaction, Reinstatement, and issuing and revoking Invitations. A second tier waits for a concrete case.
- Any signed-in User may author any Submission kind, subject to the terms. A Moderator acting as Submitter appears under their display name like anyone else.
- The **Operator** is not a User role. From the CLI it grants, revokes, and lists the role and creates Invitations; it runs Purge and is the escalation level for Notices (Moderator → Operator → counsel).

| Command | Behaviour |
|---|---|
| `tart users grant moderator <email>` | Grants the role, creating the User if needed ([Foundations](foundations.md) §5) |
| `tart users revoke moderator <email>` | Removes the role; roles are checked on every request, so revocation is immediate, open sessions included |
| `tart users list --role moderator` | Lists the role's holders |
| `tart invites create <email>` | Creates an Invitation issued by the Operator |

- On revocation, past decisions, Moderation notes, and issued Invitations stay attributed to the former Moderator, and their pending Invitations stay valid.
- **No auto-approval**: every Submission kind goes through a Moderator.
- **Self-review**, key `self_approval` (default `false`):
  - With `false`, a Moderator may not approve their own Submission, close a Notice about their own content, or reinstate it. "Own content" is a record or Documentation item created by their Submission, or content in a Revision they submitted. Another Moderator decides, or, if there is none, the Operator (open item 1).
  - Withdrawing or redacting their own content is always allowed.
  - With `true`, a self-approval is recorded as such: Submitter and approving Moderator coincide in the Submission log and the Revision.
  - Whether rejecting or requesting changes on one's own Submission is restricted is not stated (open item 1).

### Moderator identity and Moderation notes

- Moderator identity is visible only to Moderators and the Operator. The Submitter reads "a Moderator" in the Submission log, Decision messages, and statements of reasons. `/revisions` names the Submitter but not the approving Moderator ([#43](https://github.com/spippoli/tart/issues/43); answers part of [Archive records](archive-records.md) open item 13).
- **Moderation notes** can be written on Submissions (here) and on Notices, Withdrawals, and Redactions (Rights and legal actions). They are immutable, carry author and date, and are visible only to Moderators, never to the Submitter or the public. The API never sends them to non-Moderators.

### Queue

- Route `/it/moderazione` (`/en/moderation`). The nav entry appears only for Moderators; an anonymous user is sent to sign-in and a signed-in non-Moderator gets an explanatory 403 ([Foundations](foundations.md) §2).
- Lists Submissions awaiting a decision, **FIFO by default**, with sorting and with filters on derived labels, target kind, Submitter, Area, and Outdated ([#5](https://github.com/spippoli/tart/issues/5), [#15](https://github.com/spippoli/tart/issues/15)). It never ranks by popularity. The other sort orders are open item 9.
- Each entry shows its derived kind and labels and opens the Submission page.
- Flags: Outdated; overlapping pending Submissions on the same record (ADR 0007); pending create Submissions within 25 m of each other ([#42](https://github.com/spippoli/tart/issues/42)).
- **No claiming or assignment**. The first decision wins. A decision is accepted only if the Submission is still in the state the Moderator saw; otherwise the API answers a stable error code, the page shows a translated message, and it reloads ([#43](https://github.com/spippoli/tart/issues/43)).
- An empty queue has its own translated empty state (brief §21).
- With `self_approval = false`, the approve action is unavailable to a Moderator on their own Submissions (the Moderator digest also leaves them out, Notifications spec).

### Submission page

- One page `/it/contributi/{id}` (`/en/contributions/{id}`) for the Submitter and Moderators; the editor is at `…/modifica` (`…/edit`) ([#15](https://github.com/spippoli/tart/issues/15)). No one else can open it.
- It shows: status in words; current against proposed data (field and item level, from the Base revision and the changeset; for creates, the proposed record in the preview style); the Submission log with each round and its changeset snapshot, and a comparison of the current round with the previous one; Decision messages; for Merge, the list of referencing records to rewrite; for Moderators, Moderation notes and the review checklist.
- Actions by role and status:

| Actor | `draft` | `submitted` | `changes requested` |
|---|---|---|---|
| Submitter | Edit, Submit, Delete draft | Retract | Edit, Resubmit, Retract |
| Moderator | — | Approve (unless Outdated, or own under `self_approval = false`), Reject, Request changes, add Moderation note | Add Moderation note |

- A Moderator's actions on `changes requested` beyond notes are open item 5. A Moderator never edits the Submitter's content (ADR 0002).
- **Decision message**: required for rejection and for changes requested, none on approval. It is a reason from the Decision message reasons vocabulary plus free text, quoted in the Submitter's emails in its own language with the reason label translated (ADR 0008). On rejection it serves as the Art. 17 statement of reasons (ADR 0013); its full content is specified by Rights and legal actions.

**Review checklist** ([#43](https://github.com/spippoli/tart/issues/43)): fixed by the platform, translated, always shown beside the decision buttons, not blocking (no per-item ticks), and linked to the Instance's editorial guidelines:

1. People and plates: no identifiable person or readable number plate in files; otherwise request a blurred re-upload (ADR 0013).
2. File rights: each file has an allowlisted licence, Creator credit, and a plausible Rights basis (ADR 0012).
3. Artists: public artist names only; no legal identity, age, residence, appearance, or image of the person (ADR 0014).
4. No legality claims: no offence allegations or authorised/illegal judgements; a commission only if documented by a Source (ADR 0014).
5. Claims and sources: a `confirmed` Attribution has a citation; dates and precision are consistent; uncertainty is not stated as fact (ADR 0006).
6. Location: plausible against the files, and not the Submitter's own position.
7. Duplicates: duplicate warnings considered, Merge proposed where needed (ADR 0018).
8. Relevance: urban expression within the Instance's territory; no spam or abusive content.

### Invitations

([#43](https://github.com/spippoli/tart/issues/43); only under `registration = invite`)

- Issued by Moderators in the Moderation area and by the Operator with `tart invites create <email>`; each records its issuer.
- Bound to one email address, single-use, and expiring after 14 days (platform constant). Redeemed by registering with the ordinary email code (ADR 0005) at that address.
- TART sends the invitation email (Notifications spec) in the issuing Moderator's UI language, or the Instance default from the CLI; the link can also be copied.
- Moderators see a list with each Invitation's status (pending, used, expired), and any Moderator can revoke a pending one.
- An Invitation creates a User without any role.
- The route of the Invitations page is open item 15.

### Contribute hub and My contributions

- **Contribute hub** `/it/contribuisci` (`/en/contribute`): start a new Artwork, the editorial guidelines and contribution licence, and a link to My contributions ([#15](https://github.com/spippoli/tart/issues/15)).
- **My contributions** `/it/account/contributi` (`/en/account/contributions`): the User's Submissions, drafts included, filterable by Submission status, each linking to its Submission page or editor. It has no rankings or engagement figures.
- An anonymous user triggering any contribution action goes to sign-in with `?next=` and returns ([Foundations](foundations.md) §2).

### Visibility

- Pending content (drafts, submitted, changes requested) and its media are visible only to the Submitter and Moderators. Rejected and retracted Submissions likewise. The public sees only approved data ([#5](https://github.com/spippoli/tart/issues/5), [#15](https://github.com/spippoli/tart/issues/15)). How pending content appears on record pages is [Archive records](archive-records.md) (Visibility).
- A record that exists only in a pending Submission is not an Archive record and answers 404 to everyone else.

### Routes

From [#15](https://github.com/spippoli/tart/issues/15). Path segments are UI strings and may change before launch; ids never do (ADR 0010).

| Page | `it` | `en` |
|---|---|---|
| Contribute hub | `/it/contribuisci` | `/en/contribute` |
| Submission | `/it/contributi/{id}` | `/en/contributions/{id}` |
| Editor | `/it/contributi/{id}/modifica` | `/en/contributions/{id}/edit` |
| My contributions | `/it/account/contributi` | `/en/account/contributions` |
| Moderation queue | `/it/moderazione` | `/en/moderation` |

## Acceptance criteria

**Lifecycle and model**

1. No API path changes an Archive record except approving a Submission (and the Withdrawal, Redaction, and Reinstatement actions of Rights and legal actions, which change visibility only).
2. The status transitions are exactly those of the Lifecycle table; any other transition is refused with a stable error code. `approved`, `rejected`, and `retracted` accept no further transition.
3. Every transition adds a Submission log entry with actor, date, and message; each submit and resubmit creates a new numbered round with a changeset snapshot.
4. Rejecting or requesting changes without a reason and free text is refused; approving accepts no Decision message.
5. A Submission that edits a second existing record, or references a record that exists only in another pending Submission, fails validation; a Merge, Duplicate retirement, or Unmerge is the only exception.
6. Approving an edit whose Base revision is behind the current Revision succeeds when no operation overlaps a changed field or item, and the result contains both changes; with an overlap the Submission is Outdated and approve is refused.
7. A Submission whose target is merged or withdrawn is Outdated; a Merge is Outdated when either Base revision moves on, when either record is not public, or when either has an open Notice.
8. Approval creates, in one transaction, one Revision per touched record recording Submission, Submitter, approving Moderator, first-submitted date, and approved date; a failure leaves no partial Revision and no public record.
9. The derived kind and labels (adds documentation, adds History event, changes Attribution, changes Condition) match the changeset for every Submission kind and are never stored as user input.
10. A draft never edited is discarded after 24 hours; a draft older than `draft_expiry_days` is deleted together with its media; draft media are never served publicly.
11. A User who has not accepted the current terms cannot submit.

**Form and validation**

12. Every step of every kind can be reached in any order; no step blocks navigation; validation runs on submit and resubmit only.
13. On a failed submit, focus moves to an error summary listing every error as a link to its field; each field error is text bound with `aria-describedby` and the field has `aria-invalid`; each step's state is a word.
14. A new Artwork without a Documentation item, or without an initial Condition, fails validation; a single link Documentation item is enough.
15. Approving a new Artwork creates a `condition recorded` History event with the chosen Condition, dated to the latest Observed date and citing that Documentation item.
16. A `confirmed` Attribution without a citation fails validation; the Evidence level readout reads *reported* when the Claim cites nothing.
17. An uploaded file without an Observed date, Rights basis, Creator credit, or allowlisted licence fails validation; a third-party Rights basis requires the creator and the origin URL.
18. EXIF capture date and GPS appear only as prefilled suggestions with a notice; no Location is created from GPS unless the Submitter places it.
19. A geometry outside the boundary, a self-intersecting polygon, a polygon with fewer than 3 vertices, or a radius on anything but an approximate point is rejected with a text message.
20. Every drawing operation (add, move, delete, insert vertex, close, undo) can be done in crosshair mode with the keyboard alone.
21. A retired vocabulary entry is not offered in the form.
22. The preview shows proposed content hatched with a dashed outline and the label "Proposed · not public until approved", and a proposed History event does not change the displayed Condition.

**Duplicates and Merge**

23. Placing a geometry within 25 m (plus uncertainty radii) of an existing Location lists that Location with all its Artworks, disappeared ones included, ordered by distance; continuing as a new Location requires an explicit confirmation.
24. Creating an Artist, Site, Series, Area, or Source whose normalized name scores above 90 against an existing name or Alias, or a Source with the same normalized URL, shows the candidate without blocking.
25. The queue flags pending create Submissions within 25 m of each other.
26. Approving a Merge rewrites every record that referenced X to Y, each with its own Revision attributed to the Merge; X's URL answers 301 to Y without chains.
27. An Artist Merge adds X's name and Aliases to Y as Aliases unless the changeset removes them; a resulting self- or duplicate Crew membership fails validation.
28. A Duplicate retirement between items whose Artworks sit on different Locations is rejected; an accepted one moves links and citations so that no Evidence level changes.
29. An Unmerge restores X under its own id from its last pre-merge Revision.

**Roles and moderation**

30. Every moderation endpoint answers 403 to a User without the role; after `tart users revoke moderator`, the next request of an open session is refused.
31. With `self_approval = false`, approving one's own Submission is refused; with `true`, it succeeds and the log and Revision show the same User as Submitter and approving Moderator.
32. When two Moderators decide on the same Submission, only the first decision is applied; the second gets a translated error and a reload.
33. No response to a non-Moderator contains a Moderation note or a Moderator's identity; the Submitter's log and Decision messages read "a Moderator".
34. The queue defaults to FIFO and offers the filters listed; nothing in it ranks by popularity.
35. The review checklist is shown beside the decision buttons on every Submission page a Moderator opens, in their UI language, with a link to the editorial guidelines.
36. An Invitation can be redeemed once, only at its email address, only within 14 days, and not after revocation; the created User has no role. Invitations cannot be issued unless `registration = invite`.
37. The Submission page and its API never return the Submission to anyone other than the Submitter and Moderators.

**Accessibility (WCAG 2.2 AA) and i18n**

38. The editor, Submission page, queue, hub, and My contributions are fully operable by keyboard with visible focus; nothing depends on hover; status, step state, Outdated, and proposed content are conveyed in text, never by colour alone.
39. The duplicate warning, the autosave status, and validation results are announced to assistive technology.
40. No user-facing string (step names, statuses, labels, checklist items, errors, empty states, aria labels) is hardcoded; Decision message reasons are shown with the label of the current UI language; submitted free text is marked up with the Content language's `lang`.
41. Axe checks report no violations on each page of this spec, in both UI languages, in the states: empty draft, resumed draft, validation errors, duplicate warning, submitted, changes requested, Outdated, approved, rejected, retracted, empty queue, non-Moderator 403.

## Instance configuration

Exact key names belong to the [Foundations](foundations.md) spec, which owns `instance.toml`; this spec reads the following values.

| Setting | Key | Use here | Rome |
|---|---|---|---|
| Registration mode | `registration` | Invitations exist only under `invite` | `open` |
| Self-review | `self_approval` | Whether a Moderator may approve their own Submission, close a Notice about, or reinstate, their own content | `true` at launch; the Operator checklist says to switch to `false` once at least two Moderators are active |
| Decision message reasons | vocabulary file | Reasons for rejection and changes requested | Not decided |
| Expression types, Surface types | vocabulary files | Choices in the form; `retired` entries not offered | As in [Archive records](archive-records.md) |
| Boundary (GeoJSON) | — | Rejects geometries outside it | Not decided |
| File licence allowlist and default | `contribution_license` (shape: [Foundations](foundations.md) open item 5) | Licence choice per file | `CC-BY-4.0`, `CC-BY-SA-4.0`, `CC0-1.0`; default `CC-BY-SA-4.0` |
| Draft expiry | `draft_expiry_days` | Deletion of abandoned drafts and their media | `90` |
| Maximum upload size | `max_upload_mb` | Upload limit in the Documentation step | `25` |
| Content language | — | `lang` of submitted text | `it` |
| Enabled UI languages, time zone | — | Labels, dates in the Submission log | `it` (default), `en`; `Europe/Rome` |
| Editorial guidelines, contribution policy, terms of use | Markdown files | Linked from the hub, the checklist, and the Review step | Not written yet |

**Platform constants, not configuration**: the 25 m proximity distance, the never-edited draft discard after 24 hours, the 14-day Invitation lifetime, the review checklist, the "duplicate of an existing record" reason, and the closed Submission status vocabulary.

## Testing Decisions

- Test external behaviour only: the moderation domain's public interface, the API's responses, and the rendered pages. Never assert on table layouts or private helpers.
- **Moderation domain (unit, pytest)**: the lifecycle state machine (every allowed and refused transition); rounds and log entries; kind and label derivation; Outdated computation (overlapping and non-overlapping operations, merged or withdrawn targets, both Base revisions of a Merge, open Notices); the related-record rule; permission rules for each combination of role, ownership, and `self_approval`; Merge planning (the list of referencing records per kind, Artist Alias handling, Crew membership checks); Duplicate retirement's single-Location check; Unmerge.
- **Duplicate detection (unit and integration against PostGIS)**: the proximity rule with points, lines, polygons, and uncertainty radii at the 25 m boundary; the name rule with accents, punctuation, Aliases, the threshold, and Source URLs.
- **API (integration, pytest against PostGIS)**: approval as one transaction producing one Revision per touched record; the first-decision-wins check under concurrent decisions; draft expiry and media deletion; visibility of Submissions, media, Moderation notes, and Moderator identity by caller (Submitter, Moderator, other User, anonymous); role revocation effective on the next request; Invitation redemption, expiry, and revocation.
- **Pages (end-to-end, Playwright with axe)**: each Submission kind from entry point to approval in both UI languages; keyboard-only drawing in crosshair mode; the validation summary and focus; the duplicate warning; the state matrix of acceptance criterion 41.
- **i18n**: the missing-key check covers every status, step, label, checklist item, and error code of this spec.
- Test data uses fictional records only, marked as fictional, with no claims about real artworks or artists.
- Prior art: the throwaway prototype on `prototype/27-submission-form` (`frontend/prototypes/submission-editor.html`) shows the intended editor; it is not a fixture and its copy is placeholder text.

## Out of Scope

- The record model, derivations, record pages, and how pending content shows on them (Archive records).
- Withdrawal, Redaction, Reinstatement, Notices, Purge, account deletion, exports, and the content of statements of reasons (Rights and legal actions).
- Email content, triggers, preferences, and the Moderator digest (Notifications).
- The map module, cartography, and the map fallback without WebGL2 (Discovery).
- Geocoding and address search in the Location step ([#40](https://github.com/spippoli/tart/issues/40)).
- In-app role management, a second role tier, claiming or assignment in the queue, auto-approval, and an in-app complaint system.
- A blurring tool; partial approval; Moderators amending content.
- Bulk import, custom metadata fields, video and audio uploads, an in-app notification centre, public User profiles, and any engagement mechanics (likes, follows, rankings, contributor leaderboards).

## Further Notes

### Open items

The inputs leave these questions unsettled. Implementers must not fill them by assumption; each needs a decision (a resolution comment or an ADR) before the affected ticket is built.

1. **Operator as decider, and self-review scope.** With `self_approval = false` and no other Moderator, "the Operator" decides ([#43](https://github.com/spippoli/tart/issues/43)), but the Operator is not a User role and no CLI command or UI for approving a Submission or closing a Notice is decided. Also unstated: whether a Moderator may reject or request changes on their own Submission under `false`.
2. **ADR 0002 wording on auto-approval.** Answered by [Moderation roles and permissions](https://github.com/spippoli/tart/issues/43): no auto-approval; ADR 0002's consequences are amended to match.
3. **Primary targets and the missing editor kinds.** The primary target list ([#3](https://github.com/spippoli/tart/issues/3)) names Artwork, Artist, Location, Site, Series, and Area, while Sources and Documentation items are editable through Submissions with their own Revisions ([#5](https://github.com/spippoli/tart/issues/5)): whether they can be a primary target is not stated. The steps of new Site, Area (polygon drawing), Series, and Source Submissions, Location geometry edits, Documentation item and Artist edits beyond the generic Edit kind, and the Merge, Duplicate retirement, and Unmerge editors were not prototyped.
4. **Revising an Outdated Submission.** An Outdated Submission "cannot be approved until revised", but only `changes requested` lets a Submitter edit. Whether a `submitted` Outdated Submission can be edited directly, how the editor rebases it onto the current Revision, and whether that opens a new round are not decided. More generally, whether a Submitter may edit a `submitted` Submission before any decision is not stated.
5. **Moderator actions on `changes requested`.** Whether a Moderator may reject or approve a Submission waiting in `changes requested`, and whether such Submissions expire when the Submitter never responds (`draft_expiry_days` covers drafts only), are not decided.
6. **Retention of rejected and retracted Submissions.** [#5](https://github.com/spippoli/tart/issues/5) deferred retention to [#14](https://github.com/spippoli/tart/issues/14), whose resolution does not address it. How long rejected and retracted Submissions and their media are kept is not decided.
7. **Draft expiry clock.** "Never edited" (24-hour discard) and "abandoned" (`draft_expiry_days`) are not defined precisely (for example, measured from creation or from the last autosave).
8. **Linking a retry to a rejected Submission.** A retry is "optionally linked" ([#5](https://github.com/spippoli/tart/issues/5)); how the link is made and where it is shown is not decided.
9. **Queue sorting.** FIFO is the default, and [#15](https://github.com/spippoli/tart/issues/15) asks for sorting, but the other sort orders, and whether FIFO uses the first submission or the latest resubmission, are not decided.
10. **Terms acceptance in the Review step.** ADR 0012 requires acceptance before the first Submission and when the terms change; the prototype places it in every Review step. Whether it is asked on every Submission or only when the current version has not been accepted is not decided; terms versioning itself is [Foundations](foundations.md) open item 8.
11. **Decision message reasons.** Rome's list is not decided. How the platform-provided "duplicate of an existing record" reason ([#42](https://github.com/spippoli/tart/issues/42)) coexists with the configured open vocabulary (a reserved key, a platform entry outside the file) is not decided.
12. **Converting a duplicate create into documentation.** The mechanics of turning a pending create Submission into a documentation Submission on the approved record ([#42](https://github.com/spippoli/tart/issues/42), point 13) are not decided: the same Submission with a new primary target, or a new Submission pre-filled from it, and what happens to the rounds and log.
13. **Name-rule threshold.** The 25 m distance is stated to be a platform constant; the similarity threshold of 90 is not stated either way. ADR 0009 lists no such key, so this spec treats it as platform behaviour until decided.
14. **Abuse protection.** Rate limiting of Submissions and spam protection under `open` registration are still unticketed ("Performance and limits" on the [wayfinder map](https://github.com/spippoli/tart/issues/2)); once ticketed, that ticket blocks this spec and may add to it.
15. **Invitations page.** Its route and place in the Moderation area are not decided.
16. **What Moderators see of a Submitter.** The queue filters by Submitter; whether Moderators see only the display name or also the email address is not decided.
17. **Image and map comparison.** The brief (§17) asks for image comparison and a map preview in review. The decisions fix the current-versus-proposed comparison but not how files and geometries are compared (side by side, overlay).
18. **Location step without WebGL2.** Answered by [List alternative and map/list sync](https://github.com/spippoli/tart/issues/40), point 6: existing-Location text list, coordinates field (always available, as a third mode), current position, Point only without WebGL2, no geocoding; see the Location step and [Discovery](discovery.md#location-entry-without-the-map).
19. **Dependencies on Archive records open items.** The History event step's type grouping depends on the History event type list ([Archive records](archive-records.md) open item 1); the date input's `unknown` qualifier on open item 4; moving an Artwork versus a `relocated` event on open item 5; image text alternatives, which the Documentation step would collect, on open item 10.

### Notes

- The Operator checklist items mentioned here (switching `self_approval` to `false`, Moderation notes as personal data under GDPR Art. 15) belong to the Operations and portability spec.
- Pre-moderating into an authoritative archive may cost the Art. 6 DSA hosting exemption for approved content; this needs legal review (ADR 0013) and does not change this spec's behaviour.
