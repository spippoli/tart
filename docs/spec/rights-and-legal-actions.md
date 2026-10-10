# Rights and legal actions

Feature spec 5 of 7 in the [delivery order](index.md#delivery-order). It covers how an **Instance** keeps the rights of each file explicit and how it answers rights, privacy, and Digital Services Act (DSA) requests: per-file licences and the **Data licence**, **Notices**, **Withdrawal**, **Redaction**, **Reinstatement**, **Purge**, statements of reasons, account deletion, and data exports. Compile ticket: [Compile Rights and legal actions spec](https://github.com/spippoli/tart/issues/54).

Every section except Further Notes is normative. The invariants, language rules, and implementation principles in [`CLAUDE.md`](../../CLAUDE.md) apply and override any reading of this spec that contradicts them. Terms in **bold** are [glossary](../../GLOSSARY.md) terms and carry exactly that meaning. Nothing in this spec is legal advice; points marked **⚖️ legal review** are carried from the decisions and must not be settled by implementation.

## References

**ADRs applied**

| ADR | What this spec takes from it |
|---|---|
| [0002](../adr/0002-every-change-is-a-submission.md) | Withdrawal is a direct Moderator action with its own log and no Revision |
| [0004](../adr/0004-mvp-tech-stack.md) | All objects private and served through the app, so hiding is a database flag; Operator CLI and `worker` |
| [0007](../adr/0007-edit-submissions-as-field-changesets.md) | A Submission whose target is withdrawn is Outdated |
| [0008](../adr/0008-single-content-language-and-prefixed-ui-languages.md) | Notifier emails in the UI language of the Notice form, stored with the Notice; Notice reasons are translated labels |
| [0009](../adr/0009-instance-configuration-as-validated-files.md) | `data_license`, `contribution_license`, terms of use, privacy policy and DSA contact as required configuration; `self_approval`; role CLI |
| [0010](../adr/0010-public-url-scheme.md) | Withdrawn record or Documentation item and its `/revisions` subpage answer 410 with a neutral page |
| [0011](../adr/0011-provisional-software-license.md) | The software licence covers none of the archive data, contributor content, or Artworks |
| [0012](../adr/0012-per-file-licence-with-rights-basis.md) | Per-file licence from an allowlist, **Creator credit**, **Rights basis**; "covers the file only"; capped renditions; Data licence values; versioned terms; EXIF handling |
| [0013](../adr/0013-hide-not-delete-for-legal-removals.md) | Notice elements and lifecycle, Withdrawal, Redaction, Reinstatement, Purge, statements of reasons and affected Submitters, notifier data erasure, account deletion, exports, personal-data screening |
| [0014](../adr/0014-artist-records-hold-only-a-public-identity.md) | Notices from Artist pages; "personal data" reason covers an exposing Attribution; withdrawn Artist hides its Attributions and Crew memberships; requests judged on content, never on identity |
| [0016](../adr/0016-licence-policy-for-map-assets-and-data.md) | ODbL boundary: archive data is never derived from OpenStreetMap; tile extract and overlays are Instance data under the ODbL |
| [0018](../adr/0018-merge-as-reconciling-multi-record-submission.md) | No Merge, Duplicate retirement, or Unmerge while a Notice is open on either record; redacted Revisions stay redacted after a Merge |

**Glossary terms applied**: Instance, Operator, Instance configuration, Data licence, User, Moderator, Submitter, Submission, Submission status, Retraction, Outdated, Decision message, Moderation note, Archive record, Revision, Artwork, Artist, Attribution, Crew membership, Location, Source, Documentation item, Creator credit, Rights basis, Merge, Duplicate retirement, Unmerge, Withdrawal, Redaction, Reinstatement, Purge, Notice, UI language, Content language.

**Decision tickets incorporated**: [Content rights and GDPR product rules](https://github.com/spippoli/tart/issues/14), [Artist records, personal data, and artist claims](https://github.com/spippoli/tart/issues/20) (artist requests), [Moderation roles and permissions](https://github.com/spippoli/tart/issues/43) (who performs legal actions, self-review, Moderation notes, escalation), [Information architecture and page inventory](https://github.com/spippoli/tart/issues/15) (report entry point and route), [Licence policy for map assets and basemap data](https://github.com/spippoli/tart/issues/35) (ODbL boundary), [Basemap tile pipeline per Instance](https://github.com/spippoli/tart/issues/38) (external tile provider as a recipient), [Operator compliance checklist](https://github.com/spippoli/tart/issues/46) (escalation, authority orders, GDPR requests, processing inventory), and, for the parts that set legal message triggers, [Notifications](https://github.com/spippoli/tart/issues/44). Background research: [Research: archive data and contributor content licensing, GDPR](https://github.com/spippoli/tart/issues/8), [Research: Digital Services Act duties for an archive Instance](https://github.com/spippoli/tart/issues/19).

**Depends on**: [Foundations](foundations.md) (configuration, sessions, storage and media pipeline, Account page, Operator CLI, email adapter), [Archive records](archive-records.md) (record model, visibility table, `/revisions`, "Report" action), and Contribution and moderation (roles and permission checks, Submission rejection and Decision messages, the review checklist, terms acceptance).

## Problem Statement

An urban art archive stacks rights it does not own. A photo of a mural carries the Artist's copyright in the work, the photographer's copyright in the file, the privacy of anyone shown in it, and the Instance's database right; Italy has no freedom of panorama, so a contributor's licence cannot clear the depicted work. Artist records can expose real people, and attributing unauthorised work to a person may be criminal-offence data. Because Moderators approve content into an authoritative archive, the Operator may not enjoy the DSA hosting exemption for approved records, and GDPR duties are never shielded.

At the same time, the archive's value is that nothing disappears: a painted-over work stays a record, and a moderation mistake or an abusive complaint must not destroy evidence. The Operator, usually a small volunteer group, needs a way to receive reports from anyone, decide them quickly and reversibly, tell affected contributors why, and erase content for real only when the law requires it. Contributors need to know what they license, to keep their own position and identity out of the archive, and to leave without taking the archive's history with them.

## Solution

Every uploaded file carries its own licence from the Instance's allowlist, a Creator credit independent of the User, and a declared Rights basis; every licence notice says it covers the file only, and public renditions are capped while originals stay private. Structured data is published under the Instance's Data licence and is never derived from OpenStreetMap.

Anyone can send a Notice from any public record or Documentation item page, without an account. Moderators close it with a Withdrawal (hide a whole record or Documentation item), a Redaction (hide the content of past Revisions), or no action; they can also act on their own initiative. Both actions hide, never delete, and a Reinstatement undoes them. Every measure produces a structured statement of reasons for the affected Submitters, who contest it by replying to the email. Only the Operator, from the CLI, can Purge content that is already hidden, and only when the law requires it. Users delete their own accounts: their identity goes, their approved contributions stay under a stable pseudonym. Exports for access and portability requests are produced by the Operator through the CLI.

## User Stories

**Contributors and files**

1. As a contributor, I want to choose a licence for each file I upload from the archive's allowed list, with a sensible default, so that I decide how my photo may be reused.
2. As a contributor, I want to declare whether a file is my own work or a third party's work already under an allowed licence, so that the archive knows which rights are cleared.
3. As a contributor, I want to credit a file to a name of my choice, possibly a pseudonym, independent of my account, so that the credit is right even when someone else took the photo.
4. As a contributor, I want material I cannot license to be linked rather than uploaded, so that I can still document a work without infringing anyone's rights.
5. As a contributor, I want to be reminded about identifiable people and number plates when I upload, so that I don't expose bystanders.
6. As a visitor, I want every file's licence notice to say that it covers the file only, so that I don't assume I may reuse the depicted Artwork.
7. As a re-user, I want to know the Data licence of the structured archive data, so that I can reuse it lawfully.

**Notifiers**

8. As anyone, without an account, I want a "Report" action on every public record and Documentation item page, including Artist pages, so that I can report unlawful or infringing content where I see it.
9. As a notifier, I want to choose a reason, explain the problem, and leave my name and email only if I want to, so that I can report without exposing myself.
10. As a notifier who gave an email, I want an acknowledgement right away and the decision later, in the language of the form I used, so that I know my report was received and handled.
11. As a notifier, I want my name and email erased some time after the decision, so that the archive does not keep my data longer than needed.
12. As an artist, I want to raise a personal-data concern, including an Attribution that exposes me, without proving who I am, so that the request is judged on its content.

**Moderators**

13. As a Moderator, I want to be told immediately when a Notice arrives, so that I can act quickly.
14. As a Moderator, I want to see each Notice with its reason, URL, and explanation, and close it with Withdrawal, Redaction, or no action, so that every report gets a recorded decision.
15. As a Moderator, I want to withdraw a whole record or a single Documentation item, so that the measure is no broader than needed.
16. As a Moderator, I want to redact the content of past Revisions while the record stays public, so that a single unlawful value disappears from the audit trail without hiding the whole record.
17. As a Moderator, I want to withdraw or redact on my own initiative, without a Notice, so that I can act on what I find during review.
18. As a Moderator, I want to reinstate withdrawn or redacted content, so that mistakes and abusive Notices are reversible.
19. As a Moderator, I want to write Moderation notes on Notices, Withdrawals, and Redactions that only Moderators see, so that the reasoning stays with the decision.
20. As a Moderator, I want my decision refused if another Moderator decided the same Notice first, so that two decisions never collide.
21. As a Moderator who cannot judge a Notice, I want a clear escalation path to the Operator and to counsel, and to withdraw while in doubt, so that risk is contained without losing the content.

**Affected Submitters**

22. As a Submitter whose content was withdrawn, redacted, reinstated, or whose Submission was rejected, I want a statement of reasons with the measure, the facts, the ground, and how to contest it, so that I understand and can respond.
23. As a Submitter, I want to contest a measure by replying to the email, so that I don't need another system.
24. As a Submitter, I want not to be told who reported my content or which Moderator decided, so that neither side is pressured.

**Users and their data**

25. As a User, I want to delete my account myself, so that I don't need to write to anyone.
26. As a User deleting my account, I want my email and credentials erased and my name replaced by a stable pseudonym on public pages, so that I am no longer identifiable while my contributions remain.
27. As a User deleting my account, I want the option to anonymise Creator credits that carry my name, so that my name leaves the files too.
28. As a User, I want my drafts deleted and my open Submissions retracted when I delete my account, so that nothing I left unfinished is published later.
29. As a User, I want to ask the Operator's privacy contact for a copy of my data, so that I can exercise my access and portability rights.

**Operator**

30. As an Operator, I want to Purge content that is already withdrawn or redacted, from the CLI, when an erasure request is founded or an authority orders it, so that real deletion is rare and deliberate.
31. As an Operator, I want to produce a User's data export from the CLI, so that I can answer GDPR access and portability requests within a month.
32. As an Operator, I want the notifier's personal data erased automatically six months after the decision, so that retention is enforced without manual work.
33. As an Operator, I want a documented inventory of what the platform processes, so that my privacy notice and record of processing start from facts.

## Implementation Decisions

### Scope and dependencies

- This spec owns the rights rules for files and data, the Notice intake and its log, the legal actions (Withdrawal, Redaction, Reinstatement, Purge) and their log, the computation of affected Submitters and the content of statements of reasons, the 410 page content, account deletion, and the data export command.
- [Archive records](archive-records.md) owns how pages behave for content in those states (its visibility table); this spec changes the states.
- Contribution and moderation owns the upload form fields' place in the Submission editor, the review checklist, terms acceptance, Submission rejection with its Decision message, and the permission checks shared by all Moderator actions. This spec sets the rules those fields and checks enforce.
- The Notifications spec owns email rendering, language, `Reply-To`, opt-out and delivery ([Notifications](https://github.com/spippoli/tart/issues/44)). This spec decides **when** a legal message is due, **to whom**, and **what it must contain**, and hands it to an outbound port; until Notifications is built, a capturing adapter stands in.
- The Operator compliance checklist, the public data dump, and backups belong to Operations and portability.

### Modules

Legal actions are domain-rich (reversibility, affected recipients, self-review rules), so they get ports and adapters, as `CLAUDE.md` requires.

| Module | Interface (what callers see) | Lives in |
|---|---|---|
| Legal actions domain | Open a Notice; close it (Withdrawal, Redaction, no action); withdraw, redact, reinstate on own initiative; compute affected Submitters; build the statement of reasons; check that a Purge target is hidden. No framework or persistence imports | backend |
| Archive visibility port | Set and clear the withdrawn flag of a record or Documentation item, and the redacted flag of a Revision; implemented by the archive persistence of [Archive records](archive-records.md) | backend |
| Legal message port | Queue an acknowledgement, a decision notice, or a statement of reasons for a recipient; implemented by the Notifications spec's email sender | backend (`worker`) |
| Notice intake API | Public endpoint for the report form; no session required | backend |
| Legal actions API | Moderator endpoints for Notices, Withdrawal, Redaction, Reinstatement, and their logs; Moderation notes never returned to non-Moderators | backend |
| Account deletion service | Delete a User's identity, drafts, and open Submissions in one operation | backend |
| Operator CLI | Purge and user data export subcommands | backend |
| Retention job | Erase notifier name and email six months after the decision | `worker` |
| Pages | Report form, 410 page content, Moderator Notice and legal-action pages, account deletion on the Account page | frontend |

### 1. Files, licences, and data

**Per-file rights fields** ([ADR 0012](../adr/0012-per-file-licence-with-rights-basis.md)). Every uploaded Documentation item file carries:

| Field | Rule |
|---|---|
| Licence | Required. One value from the Instance's file licence allowlist, preselected to the Instance default. Only allowlisted values are accepted by the API |
| Creator credit | Required. Free text, may be a pseudonym, never a link to the User. It defaults to the User's display name only when the Rights basis is own work |
| Rights basis | Required. Either *own work*, or *third-party work already under an allowlisted licence*, which also requires the creator and the origin URL |

- Material that fits neither Rights basis is linked (a link Documentation item or a Source), never uploaded.
- These fields apply to uploaded files ([Archive records](archive-records.md)); how the editor presents them is in Contribution and moderation ([Submission form flow](https://github.com/spippoli/tart/issues/27)).
- Every licence notice, wherever a file is shown, states that the licence covers the file only, never the depicted Artwork.
- Public image renditions are capped at the resolution set in the Instance configuration; the original is never public; GPS and device identifiers are stripped from the stored original and public renditions carry no EXIF (pipeline in [Foundations](foundations.md#3-storage-and-media-pipeline)).
- EXIF capture date and GPS only prefill the Observed date and the map pin; they are never stored as a Location (Foundations).
- Moderators screen every Submission for identifiable people and readable number plates before approval. There is no blurring tool: the Moderator requests changes and the Submitter uploads a blurred file ([ADR 0013](../adr/0013-hide-not-delete-for-legal-removals.md); review checklist item 1 in Contribution and moderation).
- The Submitter accepts the Instance's versioned terms, which hold the contributor warranty and licence grant, before their first Submission and again when the terms change; the per-file Rights basis is the specific warranty ([ADR 0012](../adr/0012-per-file-licence-with-rights-basis.md)). The acceptance flow is specified in Contribution and moderation.

**Data licence.** Structured archive data is published under the Instance's `data_license`, one of `CC0-1.0`, `CC-BY-4.0`, `CC-BY-SA-4.0`, `ODbL-1.0`; non-commercial licences are not offered ([ADR 0012](../adr/0012-per-file-licence-with-rights-basis.md)). It never covers Documentation item files or the depicted Artworks. It is shown in the footer and on the data licence About page ([Foundations](foundations.md#4-i18n-shell)).

**ODbL boundary** ([ADR 0016](../adr/0016-licence-policy-for-map-assets-and-data.md)):
- Archive data is never derived from OpenStreetMap: no import, no snapping to OSM geometries, no stored geocoding results in Locations or any other record. Drawing a Location by clicking on the basemap is allowed.
- The rendered basemap is a Produced Work and needs attribution only. The Instance's PMTiles extract and OSM-derived overlays are Instance data under the ODbL; offering them, or the method that recreates them, is the Operator's responsibility (Discovery spec).

**Separate concerns.** The software licence ([ADR 0011](../adr/0011-provisional-software-license.md)), the TART brand, the Data licence, per-file licences, and the rights in the Artworks are distinct; no page or notice may imply that one covers another.

### 2. Notices

**Entry point.** Every public Archive record page (all kinds, including Artist and Source) and every Documentation item page has a "Report" action ([Archive records](archive-records.md#public-record-pages)) leading to the report form. It is available to everyone, signed in or not.

| Page | `it` | `en` |
|---|---|---|
| Report form | `/it/segnala?oggetto=…` | `/en/report?object=…` |

**Form fields** (the DSA Art. 16(2) elements, [ADR 0013](../adr/0013-hide-not-delete-for-legal-removals.md)):

| Field | Rule |
|---|---|
| Reason | Required. One entry from the Instance's Notice reasons list. Platform defaults: copyright in the depicted Artwork, copyright in the file, personal data, illegal content, other |
| URL | Required. The exact URL of the content, prefilled from the page the report started from |
| Explanation | Required. Free text |
| Name | Optional |
| Email | Optional. Without it, no acknowledgement or decision is sent |
| Good-faith statement | Required confirmation |

- The UI language of the form is stored with the Notice and used for the notifier's emails ([ADR 0008](../adr/0008-single-content-language-and-prefixed-ui-languages.md)).
- The "personal data" reason covers an Attribution that exposes someone ([ADR 0014](../adr/0014-artist-records-hold-only-a-public-identity.md)).
- Notices are judged on their content, never on who sends them; no identity is verified.
- After sending, the page confirms receipt in text (a status message announced to assistive technology).

**Lifecycle.** A Notice is *open* until a Moderator closes it with exactly one decision: **Withdrawal**, **Redaction**, or **no action**. On receipt:
- if the notifier gave an email, an acknowledgement is queued at once: Notice reference, a copy of the reason, URL and explanation, and that the decision will follow by email ([#44](https://github.com/spippoli/tart/issues/44));
- every Moderator is notified at once; this cannot be turned off or batched (Notifications spec).

On closing, a decision notice is queued for the notifier (if they gave an email) with the decision, a short reason, and redress: email reply, out-of-court settlement, courts. The Submitter of the reported content is told nothing when a Notice arrives, only when a measure is taken.

**Who decides** ([Moderation roles and permissions](https://github.com/spippoli/tart/issues/43)):
- Any Moderator. There is no claiming or assignment: the first decision wins, and a decision is accepted only if the Notice is still in the state the Moderator saw; otherwise the API returns a translated error and the page reloads.
- With `self_approval = false`, a Moderator may not close a Notice about their own content (a record or Documentation item created by their Submission, or content in a Revision they submitted). Another Moderator decides, or, if there is none, the Operator.
- Escalation is Moderator → Operator → legal counsel. While a Notice cannot be judged, the guidance is "when in doubt, withdraw", because Withdrawal is reversible ([#46](https://github.com/spippoli/tart/issues/46)). The recommended target is a decision within 7 days; it is guidance in the Operator documentation, not configuration or an enforced deadline.

**Notice log.** Every Notice is kept with its reason, URL, explanation, form language, receipt time, decision, deciding Moderator, decision time, and any Moderation notes. The log is visible only to Moderators and the Operator. Six months after the decision, the `worker` erases the notifier's name and email; the rest of the log is kept ([ADR 0013](../adr/0013-hide-not-delete-for-legal-removals.md)).

**Effects on other flows.** While a Notice is open on a record, a Merge, Duplicate retirement, or Unmerge involving it is Outdated ([ADR 0018](../adr/0018-merge-as-reconciling-multi-record-submission.md)).

### 3. Withdrawal

- **Target**: a whole Archive record of any kind, or a single Documentation item ([ADR 0013](../adr/0013-hide-not-delete-for-legal-removals.md)).
- **Trigger**: closing a Notice, or a Moderator's own initiative.
- **Effect**: the target is hidden from the public, everywhere content is shown publicly. Its public page and its `/revisions` subpage answer 410 ([ADR 0010](../adr/0010-public-url-scheme.md)); withdrawn Documentation items are absent from galleries and Timelines; a withdrawn Artist's Attributions and Crew memberships are hidden with it, and its Artworks show no Attribution ([ADR 0014](../adr/0014-artist-records-hold-only-a-public-identity.md), [Archive records](archive-records.md#visibility)).
- Hiding is a database flag; no record, Revision, or stored object is changed or deleted ([ADR 0004](../adr/0004-mvp-tech-stack.md)).
- A Withdrawal produces no Revision and never appears on the Timeline; it is not a Condition ([ADR 0002](../adr/0002-every-change-is-a-submission.md)).
- Pending Submissions whose target is withdrawn are Outdated ([ADR 0007](../adr/0007-edit-submissions-as-field-changesets.md)).
- Withdrawing one's own content is always allowed, whatever `self_approval` says.

**410 page.** It states, in the UI language, that the content was removed for legal, rights, or privacy reasons, and shows none of its content: no title, name, image, or metadata.

### 4. Redaction

- **Target**: the content of past Revisions of an Archive record, when only a value must go (for example a person's real name in an earlier description). The record itself stays public ([ADR 0013](../adr/0013-hide-not-delete-for-legal-removals.md)).
- **Trigger**: closing a Notice, or a Moderator's own initiative.
- **Effect**: on `/revisions`, a redacted Revision stays listed but its content is hidden from the public ([Archive records](archive-records.md#visibility)). A Redaction produces no Revision.
- Redacted Revisions of a record merged into another stay redacted ([ADR 0018](../adr/0018-merge-as-reconciling-multi-record-submission.md)).
- After an Artist's Reinstatement, past Revisions that still carry an exposing name are handled by Redaction where needed ([ADR 0014](../adr/0014-artist-records-hold-only-a-public-identity.md)).
- Redacting one's own content is always allowed, whatever `self_approval` says.

### 5. Reinstatement

- Undoes a Withdrawal or a Redaction: the hidden content is public again, exactly as before; a reinstated Artist's Attributions and Crew memberships return ([ADR 0014](../adr/0014-artist-records-hold-only-a-public-identity.md)).
- Performed by a Moderator. With `self_approval = false`, a Moderator may not reinstate their own content.
- Produces a statement of reasons to the affected Submitters. The original notifier gets no email ([#44](https://github.com/spippoli/tart/issues/44)).
- Purged content cannot be reinstated.

### 6. Legal action log and Moderation notes

- Withdrawals, Redactions, and Reinstatements are recorded in their own log, not as Revisions ([ADR 0002](../adr/0002-every-change-is-a-submission.md)). Each entry records the target, the measure, the Moderator, the time, the Notice it closes (or own initiative), and the statement of reasons sent.
- Moderation notes can be written on Notices, Withdrawals, and Redactions. They are immutable, carry author and date, and are visible only to Moderators and the Operator ([#43](https://github.com/spippoli/tart/issues/43)).
- Moderator identity is visible only to Moderators and the Operator. Statements of reasons, decision notices, and every public page say "a Moderator".

### 7. Statements of reasons

**When**: for every Withdrawal, Redaction, Reinstatement, and Submission rejection ([ADR 0013](../adr/0013-hide-not-delete-for-legal-removals.md)). For a rejection, the Decision message is the statement of reasons (Contribution and moderation).

**To whom (affected Submitters)**:
- for a Documentation item: the Submitter who created it;
- for a record: its creator and the Submitters of the affected Revisions;
- for a rejection: the Submission's Submitter.

A recipient whose account was deleted has no address and gets nothing. The person who performed the action gets no email ([#44](https://github.com/spippoli/tart/issues/44)).

**Content** (DSA Art. 17):
1. the measure taken and its target;
2. the facts and circumstances;
3. whether it followed a Notice or was taken on the Moderator's own initiative;
4. the ground in the terms of use or in law;
5. whether automation was used (always "no" in the MVP);
6. redress: replying to the email, out-of-court settlement, and courts.

Contesting is done by replying to the email; legal emails set `Reply-To` to the Operator's legal contact. There is no in-app complaint system ([ADR 0013](../adr/0013-hide-not-delete-for-legal-removals.md)). Statements never identify the notifier or the Moderator.

### 8. Purge

- **Only** the Operator, from the Operator CLI; there is no Purge in any Moderator UI ([ADR 0013](../adr/0013-hide-not-delete-for-legal-removals.md)).
- **Only** on content already withdrawn or redacted; the command refuses anything public.
- **Only** when the law requires it: a founded GDPR erasure request or an authority order (DSA Art. 9–10; the Operator answers orders alone, [#46](https://github.com/spippoli/tart/issues/46)).
- Effect: the targeted content, including stored file objects of a withdrawn Documentation item, is permanently erased from the database and storage. It is the only way content ever leaves the archive.
- The command name and its exact output are not decided (see Open items).

### 9. Account deletion

Self-service from the Account page (`/it/account`, `/en/account`, [Foundations](foundations.md#2-authentication-and-sessions)). In one operation ([ADR 0013](../adr/0013-hide-not-delete-for-legal-removals.md)):

1. the email, passkeys, and sessions are erased;
2. the display name is replaced by a stable pseudonym, which is what `/revisions` and every other public mention shows from then on;
3. drafts are deleted, with their private media;
4. open Submissions (*submitted*, *changes requested*) are retracted;
5. approved content stays in the archive;
6. if the User chose so in the deletion flow, Creator credits that carry their name are anonymised.

No email is sent about the retractions, since the account no longer has an address ([#44](https://github.com/spippoli/tart/issues/44)). Account-level GDPR requests that are not self-service go to the Operator's privacy contact, not through Notices. ⚖️ legal review: the lawful basis for keeping deleted Users' contributions.

### 10. Data exports

- Access (GDPR Art. 15) and portability (Art. 20) exports are produced by the Operator through the CLI on request; there is no self-service export ([ADR 0013](../adr/0013-hide-not-delete-for-legal-removals.md)).
- The answer is due within one month (GDPR Art. 12; Operator guidance, [#46](https://github.com/spippoli/tart/issues/46)).
- Moderation notes are personal data that may fall under an access request; the Operator documentation warns Moderators to keep them factual ([#43](https://github.com/spippoli/tart/issues/43)).

### 11. Processing inventory

The platform documents what it processes so that the Operator's privacy notice and record of processing start from facts, not a template ([#46](https://github.com/spippoli/tart/issues/46)). For each data category it states the purpose and retention: account email, sessions, logs, display name and pseudonym, Submission content, Notice data (notifier name and email erased six months after the decision), EXIF GPS (stripped on publish). It lists the external recipients: hosting, storage, SMTP, and, when an Instance style uses an external `https` tile source, the tile provider ([#38](https://github.com/spippoli/tart/issues/38)). The matching Operator checklist items (name the tile provider in the privacy policy, among others) are in Operations and portability.

### Example

Fictional scenario, invented for illustration (no real artwork, artist, or person): an approved Artwork description once read "painted by Mario R., who lives on Via dei Glicini", and a later edit Submission removed the sentence. Someone sends a Notice with the "personal data" reason from the Artwork page. A Moderator closes it with a Redaction of the earlier Revision: the Artwork stays public, `/revisions` still lists that Revision with its content hidden, the Submitter of that Revision receives a statement of reasons (measure: Redaction; ground: personal data in the terms; following a Notice; no automation; redress by reply), and the notifier, who left an email, receives the decision.

## Testing Decisions

A good test exercises a module through its external interface and asserts observable behaviour (an HTTP status, a page's text, a queued legal message, a stored or erased object), never internal calls. Test data uses fictional records, people, and Notices only, marked as fictional.

- **Legal actions domain (unit, pytest)**: Notice lifecycle (one decision, no reopening by a second decision); affected-Submitter computation for a Documentation item, a record with many Revisions, and a rejection, including a deleted account; statement of reasons content (all six elements present, "no automation", no Moderator or notifier identity); `self_approval` rules for closing, reinstating, withdrawing, and redacting own content; Purge refusal on public content.
- **Persistence and API (integration, pytest against PostGIS)**: after a Withdrawal the record page and `/revisions` answer 410 and the content is absent from lists, the map data, search, galleries, and Timelines; a withdrawn Artist's Attributions and Crew memberships disappear and return on Reinstatement; a redacted Revision is listed without content; Withdrawal and Redaction create no Revision; pending Submissions on a withdrawn target become Outdated; a Merge on a record with an open Notice is Outdated; concurrent Notice decisions (second one refused with a stable error code); the Notice intake works without a session; Moderation notes and the Notice log are never returned to non-Moderators.
- **Retention job**: with a controlled clock, the notifier's name and email are erased six months after the decision and the rest of the Notice is kept.
- **Account deletion (integration)**: email, passkeys, and sessions gone; pseudonym on `/revisions`; drafts and their media deleted; open Submissions retracted; approved records unchanged; Creator credits anonymised only when chosen.
- **CLI**: Purge erases database content and stored objects of a withdrawn Documentation item and refuses public content; the export command produces an export for a User.
- **Legal message port**: a capturing adapter asserts which messages are queued, to whom, in which UI language, and that no message goes to the actor or to a deleted account.
- **Pages (Playwright with axe)**: the report form signed out and signed in, in both UI languages, with validation errors and the confirmation; the 410 page; the Moderator Notice and legal-action pages; account deletion. Keyboard-only completion of the report form and of the deletion flow.
- Prior art: none in the repository yet; the seams of [Foundations](foundations.md#testing-decisions) and [Archive records](archive-records.md#testing-decisions) are reused.

## Acceptance criteria

**Files and data**

1. The API refuses an uploaded file without a licence from the Instance allowlist, without a Creator credit, or without a Rights basis; a third-party Rights basis without creator and origin URL is refused.
2. The Creator credit is prefilled with the User's display name only for own work, and stays editable.
3. Every place a file is shown publicly displays its Creator credit and licence with a notice that the licence covers the file only.
4. No public rendition exceeds the configured cap or carries EXIF; originals are never served publicly.
5. The Data licence appears in the footer and on the data licence About page; no page states or implies that the software licence, the Data licence, or a file licence covers the depicted Artworks.
6. No Archive record field is populated from OpenStreetMap data or stored geocoding results.

**Notices**

7. Every public record page of every kind and every Documentation item page has a "Report" action leading to `/it/segnala?oggetto=…` (`/en/report?object=…`) with the URL prefilled.
8. The report form can be sent without an account; it requires a reason, URL, explanation, and the good-faith statement, and accepts optional name and email.
9. With an email, the notifier receives an acknowledgement (reference, reason, URL, explanation) and, on closing, a decision with redress, both in the UI language of the form; without an email, nothing is sent.
10. Every Moderator is notified of each new Notice immediately; the reported content's Submitter is notified of nothing until a measure is taken.
11. A Notice is closed with exactly one of Withdrawal, Redaction, or no action; a second decision on a Notice that is no longer open is refused with a translated error.
12. With `self_approval = false`, a Moderator cannot close a Notice about their own content or reinstate their own content, and can always withdraw or redact their own content.
13. Six months after a Notice's decision, the notifier's name and email are erased and the rest of the Notice log remains.
14. The Notice log, legal action log, and Moderation notes are never returned to non-Moderators.

**Withdrawal, Redaction, Reinstatement**

15. A withdrawn record or Documentation item, and its `/revisions` subpage, answer 410 with a neutral page that shows none of its content; the content is absent from every public list, map, search result, gallery, and Timeline.
16. A Withdrawal or Redaction changes no record content, Revision, or stored object, and creates no Revision.
17. A redacted Revision stays listed on `/revisions` with its content hidden; the record stays public.
18. A Reinstatement restores exactly what was hidden, including a withdrawn Artist's Attributions and Crew memberships.
19. Each Withdrawal, Redaction, Reinstatement, and Submission rejection queues a statement of reasons to every affected Submitter with an address, containing the six Art. 17 elements, `Reply-To` the legal contact, and no Moderator or notifier identity; the actor gets no email; a Reinstatement sends nothing to the notifier.
20. Withdrawal, Redaction, Reinstatement, and Purge are never shown on the Timeline.

**Purge**

21. No Moderator page or API endpoint can Purge; the Operator CLI Purge refuses content that is not withdrawn or redacted.
22. After a Purge, the content and its stored objects are gone from the database and storage, and it cannot be reinstated.

**Accounts and exports**

23. Deleting an account from the Account page erases email, passkeys, and sessions, deletes drafts and their media, retracts open Submissions, keeps approved content, and shows a stable pseudonym wherever the display name appeared.
24. Creator credits carrying the User's name are anonymised only if the User chose it during deletion.
25. The Operator CLI produces a data export for a given User.

**Accessibility (WCAG 2.2 AA) and i18n**

26. The report form, the 410 page, the Moderator Notice and legal-action pages, and the account deletion flow pass axe with no violations in both UI languages, light and dark themes, desktop and mobile widths.
27. Every form control has a visible label; validation follows the Submission editor's pattern ([#27](https://github.com/spippoli/tart/issues/27)): on submit, an error summary linking to each field, with inline text errors (`aria-describedby`, `aria-invalid`); the receipt confirmation is announced as a status message.
28. Notice state, decision, and legal-action state are conveyed in words, never by colour alone; nothing depends on hover.
29. Every user-facing string (reasons, decisions, measures, statement-of-reasons wording, errors, 410 text, aria labels, empty states) comes from the message catalogues; configured Notice reason labels exist for every enabled UI language; quoted content keeps its own language and `lang` attribute.
30. Dates in logs and emails are formatted with `Intl` in the Instance time zone.

## Instance configuration

Exact key names belong to the [Foundations](foundations.md#instance-configuration) spec, which owns `instance.toml`; "Not decided" means the decisions give no value or shape.

| Setting | Key | Use here | Rome |
|---|---|---|---|
| Data licence (SPDX) | `data_license` | Footer, About page, data reuse | `CC-BY-SA-4.0` |
| File licence allowlist and default | `contribution_license` (shape not decided) | Licence choice per file | `CC-BY-4.0`, `CC-BY-SA-4.0`, `CC0-1.0`; default `CC-BY-SA-4.0` |
| Public image rendition cap | Not decided | Maximum public resolution | Not decided |
| Notice reasons | Not decided | Report form reason list, labels per UI language | Not decided (platform defaults: copyright in the depicted Artwork, copyright in the file, personal data, illegal content, other) |
| Self-review | `self_approval` | Closing Notices about, and reinstating, own content | `true` at launch; the Operator checklist says to switch to `false` once at least two Moderators are active |
| DSA contact (required) | Not decided | About contacts page | Not decided |
| Privacy contact | Not decided (may not exist) | Account-level GDPR requests | Not decided |
| Legal contact for `Reply-To` | Not decided | Statements of reasons and notifier emails | Not decided |
| Terms of use, privacy policy (required) | Markdown files | Grounds cited in statements of reasons; About pages | Not written yet (drafting out of scope) |
| Content language, UI languages, time zone | Foundations | Labels, email language, date formatting | `it`; `it` (default), `en`; `Europe/Rome` |

**Platform constants, not configuration**: notifier name and email retention (six months after the decision); "no automation" in statements of reasons; Purge only from the CLI. The 7-day decision target is Operator guidance only.

## Out of Scope

- An in-app complaint system, out-of-court dispute body integration, trusted-flagger priority, the statement-of-reasons database, transparency reports, and every other online-platform duty that small Instances are exempt from; full platform duties for publicly controlled Operators ([#46](https://github.com/spippoli/tart/issues/46)).
- A blurring tool for images.
- Verifying the identity of notifiers or artists; any User–Artist link or claim ([ADR 0014](../adr/0014-artist-records-hold-only-a-public-identity.md)).
- Self-service data export.
- Purge or deletion from the Moderator UI.
- Email rendering, delivery, opt-out, and bounce handling (Notifications).
- The Operator compliance checklist, the public data dump, and backups (Operations and portability).
- Drafting the terms of use, privacy policy, trademark policy, or any licence notice text beyond the platform's UI strings; professional legal review itself.
- Rate limiting and spam protection of Notices (unticketed "Performance and limits").

## Further Notes

Not normative.

### Legal review points carried from the decisions

These do not change the behaviour specified above, but the Operator must not treat it as legal clearance:

1. Publishing photos of in-copyright works without freedom of panorama (art. 70 / 70(1-bis) L. 633/1941), and licence notice wording that does not imply rights in the Artwork ([ADR 0012](../adr/0012-per-file-licence-with-rights-basis.md), [#8](https://github.com/spippoli/tart/issues/8)).
2. The lawful basis for keeping deleted Users' contributions ([ADR 0013](../adr/0013-hide-not-delete-for-legal-removals.md)).
3. The loss of the DSA Art. 6 hosting exemption for approved records; fast, granular Withdrawal and Redaction are the mitigation ([ADR 0013](../adr/0013-hide-not-delete-for-legal-removals.md), [#19](https://github.com/spippoli/tart/issues/19)).
4. Whether pseudonymous Attributions of unauthorised works are Art. 10 GDPR data ([ADR 0014](../adr/0014-artist-records-hold-only-a-public-identity.md)).
5. Whether Art. 17 applies to Submission rejections and who counts as an "affected recipient" for records built by many Submitters ([#19](https://github.com/spippoli/tart/issues/19)); the MVP takes the safe path of [ADR 0013](../adr/0013-hide-not-delete-for-legal-removals.md).
6. Whether one intake channel can serve both DSA notices and GDPR requests ([#19](https://github.com/spippoli/tart/issues/19)); the MVP sends account-level GDPR requests to the privacy contact.
7. How much moderation history is disclosable in an access request ([#8](https://github.com/spippoli/tart/issues/8)).
8. Who holds the database right in a volunteer archive, and licence compatibility for cross-Instance aggregation and between ODbL data and the Instance's Data licence ([#8](https://github.com/spippoli/tart/issues/8), [ADR 0016](../adr/0016-licence-policy-for-map-assets-and-data.md)).

### Open items

The inputs leave these unsettled. Implementers must not fill them by assumption; each needs a decision (a resolution comment or an ADR) before the affected ticket is built.

**Notices**
1. **Notice reasons configuration.** Whether Notice reasons are a fourth open vocabulary (keys, labels per UI language, `retired`) and Rome's list are not decided (also [Foundations](foundations.md#open-items) item 7).
2. **Report form target.** The format of `?oggetto=` / `?object=` (record kind and id, or a URL), and whether a Notice can point at a specific Revision on `/revisions` (the natural target of a Redaction), are not decided.
3. **Moderator pages for Notices and legal actions.** The routes of the Notice list and Notice page, where they sit in the Moderation area (with or apart from the Submission queue), and where a Moderator starts an own-initiative Withdrawal or Redaction are not in the [#15](https://github.com/spippoli/tart/issues/15) route table.
4. **Notice reference and confirmation.** The acknowledgement email carries a "Notice reference" ([#44](https://github.com/spippoli/tart/issues/44)); its format, and whether the on-screen confirmation shows it, are not decided.
5. **Several Notices on the same content**, a Notice about content that is already withdrawn, and whether a closed Notice can be reopened are not decided.
6. **Signed-in notifiers.** Whether a Notice sent by a signed-in User is linked to the account (and what that means for the six-month erasure) is not decided.
7. **Operator as decider.** With `self_approval = false` and no other Moderator, "the Operator" decides; the Operator has no UI role and no CLI command for Notices, so how the Operator acts is not decided.
8. **Self-review wording.** "May not close a Notice about their own content" and "withdrawing or redacting their own content is always allowed" overlap: whether a Moderator may close a Notice about their own content *with* a Withdrawal or Redaction is not decided.
9. **Ground of a measure.** Whether the "ground in the terms or law" of a statement of reasons is picked from the Notice reasons list, from another list, or written freely is not decided.

**Withdrawal and Redaction**
10. **Removing a current value.** Redaction hides past Revisions only. How a current unlawful value (for example a name in the current description, or an exposing current Attribution) is removed while the record stays public is not decided: presumably an edit Submission followed by a Redaction of earlier Revisions, but who authors that Submission, and how it fits `self_approval = false`, are not stated.
11. **Redaction granularity.** Whether a Redaction hides a whole Revision's content or only selected fields of it, and whether the current Revision can be redacted, is not decided.
12. **Withdrawal effects beyond Artists** (carried from [Archive records](archive-records.md#open-items) item 12): whether a Claim whose only citation is withdrawn becomes `reported`, whether a `confirmed` Attribution then stays valid, how a withdrawn Artwork appears in its Location's stratigraphy, a Series, or as a covering-Artwork link, and what a withdrawn Location or Source means for the records that reference it.
13. **Moderator view of hidden content.** Moderators must see withdrawn and redacted content to decide a Reinstatement, but no decision says where and how it is shown to them.
14. **Submitter view.** Whether a Submitter sees their own withdrawn content or redacted Revisions (for example on My contributions) is not decided.
15. **In-app statements.** Statements of reasons are emailed; whether they are also visible in the app (for a rejection the Decision message is on the Submission page) is not decided for Withdrawal, Redaction, and Reinstatement.
16. **Legal contact.** Legal emails set `Reply-To` to "the Operator's legal contact"; whether that is the DSA contact, the privacy contact, or a separate key is not decided (see [Foundations](foundations.md#open-items) item 6 on the privacy contact).

**Purge**
17. **Command and scope.** The CLI command name, how a target is selected (record, Documentation item, Revision, field), whether a Purge requires a recorded legal ground, and whether it is logged are not decided.
18. **What remains after a Purge.** Whether the id still answers 410, whether a tombstone remains in the Revision sequence or the legal action log, and how a Purge of redacted Revision content keeps the audit trail consistent are not decided.
19. **Statement of reasons for a Purge.** The decisions list none; whether one is due (the content was already hidden and notified) is not decided.
20. **Backups.** How a Purge or an account deletion reaches existing backups is not decided; it belongs with [Backups, upgrades and monitoring](https://github.com/spippoli/tart/issues/45).

**Accounts and exports**
21. **Pseudonym format.** The shape of the stable pseudonym (for example based on the user id, as OpenStreetMap does) is not decided.
22. **Deletion flow details.** Confirmation step (for example re-entering a sign-in code), any grace period, and what happens to a deleting User's Moderator role, their immutable Moderation notes, and the Invitations they issued are not decided.
23. **Creator credit anonymisation.** What "carry their name" matches (exact display name, any free-text mention), what replaces it, and how a living User or a third party requests anonymisation outside account deletion (CC 4.0 attribution removal, [ADR 0012](../adr/0012-per-file-licence-with-rights-basis.md)) are not decided; nor whether a file's licence or Creator credit can ever change after approval.
24. **Export content and format.** Which data an export contains (profile, Submissions, uploaded files, Moderation notes about the User, Notice data), its format, and the CLI command name are not decided.

**Files and data**
25. **Public file rights fields** (carried from [Archive records](archive-records.md#open-items) item 14): whether the Rights basis and a third party's creator and origin URL are public.
26. **File licence keys and rendition cap** (also [Foundations](foundations.md#open-items) items 2 and 5): the shape of `contribution_license` as an allowlist plus a default, and Rome's rendition cap.
27. **Deliberate position obfuscation** (carried from [Archive records](archive-records.md#open-items) item 15): handed to [Content rights and GDPR product rules](https://github.com/spippoli/tart/issues/14), which did not address it.
28. **Terms versioning** (also [Foundations](foundations.md#open-items) item 8): how a new version of the terms is declared and recorded as accepted.

### Notes

- Abuse protection for the public report form (rate limits, spam) waits for the unticketed "Performance and limits" work on the [map](https://github.com/spippoli/tart/issues/2).
- The Operator obligations around this feature (AGCOM notification and declarations, authority orders, threats to life or safety, data breaches, the 7-day target) are Operator checklist items in Operations and portability ([#46](https://github.com/spippoli/tart/issues/46)), not software behaviour.
- The Rome Operator (an individual, an existing association, or a new entity) is not decided ([#46](https://github.com/spippoli/tart/issues/46)); it determines who acts as DSA provider and GDPR controller.
