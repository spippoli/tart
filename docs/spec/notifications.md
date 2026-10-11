# Notifications

Feature spec 6 of 7 in the [delivery order](index.md#delivery-order). It covers the emails an **Instance** sends: which events trigger them, who receives them, the legal emails required by the Digital Services Act, which emails a User may turn off, the **Moderator digest**, the language each email is written in, and how emails are formed and delivered. It depends on [Foundations](foundations.md) (email adapter, `worker`, backend message catalogue, Account page), [Archive records](archive-records.md), Contribution and moderation (the Submission lifecycle and Invitations that raise the events), and Rights and legal actions (the Notices, Withdrawals, Redactions, and Reinstatements that raise the legal emails). Compile ticket: [Compile Notifications spec](https://github.com/spippoli/tart/issues/55).

Every section except Further Notes is normative. The invariants, language rules, and implementation principles in [`CLAUDE.md`](../../CLAUDE.md) apply and override any reading of this spec that contradicts them. Terms in **bold** are [glossary](../../GLOSSARY.md) terms and carry exactly that meaning ([spec index, Sources of truth](index.md#sources-of-truth)).

## References

**ADRs applied**

| ADR | What this spec takes from it |
|---|---|
| [0004](../adr/0004-mvp-tech-stack.md) | Email delivery is a `worker` job (Procrastinate on PostgreSQL); a generic SMTP adapter per Instance; Mailpit in development |
| [0005](../adr/0005-passwordless-in-app-auth.md) | The sign-in code is an email; reliable delivery is critical because sign-in depends on it |
| [0008](../adr/0008-single-content-language-and-prefixed-ui-languages.md) | Emails rendered by the worker from a backend message catalogue under the missing-key check; the language of each email by recipient (amended by [Notifications](https://github.com/spippoli/tart/issues/44)); quoted content keeps its own language, configured labels are translated |
| [0009](../adr/0009-instance-configuration-as-validated-files.md) | SMTP settings in the environment; archive name in the Content language; contact points; `self_approval`; Invitations issued by Moderators and by `tart invites create` |
| [0013](../adr/0013-hide-not-delete-for-legal-removals.md) | The Notice acknowledgement and decision notice; the Art. 17 statement of reasons for every Withdrawal, Redaction, Reinstatement, and rejection, its elements, and who the affected Submitters are; contesting by email reply; notifier data erased six months after the decision |

**Glossary terms applied**: Instance, Operator, Instance configuration, UI language, Content language, User, Invitation, Moderator, Submitter, Submission, Submission status, Changes requested, Retraction, Outdated, Submission log, Decision message, Moderation note, Moderator digest, Archive record, Revision, Merge, Withdrawal, Redaction, Reinstatement, Purge, Notice.

**Decision tickets incorporated**: [Notifications](https://github.com/spippoli/tart/issues/44) (the whole of this spec's content), and, for the parts that shape emails, [Submission and moderation lifecycle](https://github.com/spippoli/tart/issues/5) (statuses, Outdated, Decision message), [Content rights and GDPR product rules](https://github.com/spippoli/tart/issues/14) (Notice acknowledgement, statements of reasons, contesting by email), [Research: Digital Services Act duties for an archive Instance](https://github.com/spippoli/tart/issues/19) (Art. 16 and 17 elements, as background), [Moderation roles and permissions](https://github.com/spippoli/tart/issues/43) (`self_approval`, Moderator anonymity, Invitation email), [Backups, upgrades and monitoring](https://github.com/spippoli/tart/issues/45) (visibility of failed emails), [Instance configuration keys and contacts](https://github.com/spippoli/tart/issues/85) (the DSA contact as `Reply-To`), and [Operator as decider and Moderator self-review](https://github.com/spippoli/tart/issues/93) (Notice received recipients, digest contents), and [Redaction, current-value removal and Purge](https://github.com/spippoli/tart/issues/95) (the statement of reasons for a Purge), and [Security constants and abuse protection](https://github.com/spippoli/tart/issues/84) (retry policy, digest hour, the Notice received cap, the Suspension and "registration is not open" emails), and [Notice handling details](https://github.com/spippoli/tart/issues/94) (the redress block, the Notice reference and short reason, New Submission content, deleted recipients, email wording as implementation), [Rome Instance values](https://github.com/spippoli/tart/issues/86) (Rome's archive name as From name).

## Problem Statement

A collaborative, pre-moderated archive only works if people learn, without having to check, that something needs them. A Submitter waits for a decision and must hear when a Moderator asks for changes, approves, or rejects, or when their open Submission has become **Outdated**. A Moderator must hear about new work in the queue without being flooded, and must hear immediately about a **Notice**, because the Digital Services Act expects notices to be handled in a timely way. A person who reports content, often without an account, must get an acknowledgement and later a decision. Every person whose content is hidden or refused is owed a statement of reasons and a way to contest it, and contesting happens by email reply because the MVP has no in-app complaint system. All of this must reach people in a language they read, while archive content stays in its single Content language, and must never become an engagement channel, a tracking channel, or a way to expose who reported whom or which Moderator decided.

## Solution

Domain actions in the Contribution and moderation and the Rights and legal actions features raise events; a notifications module decides, for each event, which emails to send, to whom, and in which language, and enqueues them. The `worker` renders each email from the backend message catalogue as plain text plus minimal HTML, with no remote images, tracking pixels, or tracked links, and sends it through the Foundations SMTP adapter with bounded retries. Each email summarises the event and links to the page where the person can act; it never copies Submission content or files. Legal emails (Notice acknowledgement and decision, statements of reasons) cannot be turned off and set `Reply-To` to the Operator's DSA contact so that a reply contests the decision. Submitters have one optional switch for updates on their Submissions; Moderators choose between one email per Submission, a daily **Moderator digest** (the default), or none, while Notice emails always arrive immediately. No email goes to the person who performed the action, and emails never name the Moderator.

## User Stories

**Submitter**

1. As a Submitter, I want an email when a Moderator requests changes, with the Decision message, so that I know what to fix.
2. As a Submitter, I want an email when my Submission is approved, with a link to the published record, so that I can see my contribution in the archive.
3. As a Submitter, I want an email when my Submission is rejected that states the reasons and how to contest, so that I understand the decision and can challenge it.
4. As a Submitter, I want an email when my open Submission becomes Outdated, so that I revise it before it can be approved.
5. As a Submitter, I want no email confirming what I just did myself (submitting, retracting), so that my inbox only carries news.
6. As a Submitter, I want a single Account-page switch for updates on my Submissions, on by default, so that I can stop the optional emails without losing the legal ones.
7. As a Submitter, I want a statement of reasons when content I contributed is withdrawn, redacted, or reinstated, so that I know what happened and can contest it by replying.
8. As a Submitter, I want to hear nothing when someone merely reports my content, so that I am informed of measures, not pressured by unreviewed reports.

**Moderator**

9. As a Moderator, I want an immediate email for every Notice, with its reason, the reported URL, and a link to the Notice page, so that I can act in time.
10. As a Moderator, I want to choose on my Account page between one email per new or resubmitted Submission, a daily digest, and no email, so that queue emails fit how I work.
11. As a Moderator, I want the daily digest only when something new has arrived, listing the pending count, the new Submissions, and the oldest one waiting, so that I see the queue at a glance without empty emails.
12. As a Moderator, I want my name never to appear in emails to Submitters or notifiers, so that I am not exposed for my decisions.

**Notifier**

13. As a person who reported content and gave an email, I want an acknowledgement right away with a reference and a copy of what I sent, so that I know the report arrived.
14. As a notifier, I want an email with the decision when my Notice is closed, including the reason and how to seek redress, so that I know the outcome and my options.
15. As a notifier without an account, I want these emails in the language of the form I used, so that I can read them.

**Invitee and new User**

16. As a person invited to an archive, I want the Invitation email in the inviting Moderator's language (or the archive default), so that I can register.
17. As a new person signing in for the first time, I want the sign-in code in the language of the sign-in page, so that I can read it.

**Any recipient**

18. As a recipient, I want emails without remote images, tracking pixels, or tracked links, so that opening an email reveals nothing about me.
19. As a recipient, I want a plain-text version of every email, so that I can read it in any client or with a screen reader.
20. As a User, I want my emails in my preferred UI language, with archive content quoted in its own language, so that I read the frame in my language and the content as written.
21. As a recipient of an optional email, I want a footer link to my Account page, so that I can change what I receive.

**Operator**

22. As an Operator, I want replies to legal emails to reach my configured DSA contact, so that contested decisions come to me.
23. As an Operator, I want a final delivery failure logged, so that I can see when people are not being reached.
24. As a Moderator, I want a burst of Notices to arrive as at most ten emails an hour plus one summary, so that a flood of reports does not bury my inbox while every Notice still reaches the queue.
25. As a suspended User, I want an email with the reason and how to contest it, so that I am not cut off without an explanation.
26. As a notifier, I want the decision email to carry my Notice reference and the same redress routes as every other legal email, so that I can match it to my report and know my options.
27. As a Moderator receiving one email per Submission, I want each email to say what kind of change arrived, on which record, and how many are waiting, so that I can triage from my inbox.

## Implementation Decisions

### Scope and dependencies

- This spec owns the catalogue of emails, their recipients, opt-out, the digest, language selection, and form and delivery.
- It does not own the actions that raise the events. The Submission lifecycle, Invitations, and `self_approval` are specified by Contribution and moderation; Notices, Withdrawal, Redaction, Reinstatement, the inputs a Moderator gives for a statement of reasons, and account deletion are specified by Rights and legal actions. This spec reads their outcomes.
- The SMTP adapter, the `worker`, the backend message catalogue and its missing-key check, and the Account page shell are specified by [Foundations](foundations.md). The sign-in code email belongs to Foundations ([ADR 0005](../adr/0005-passwordless-in-app-auth.md)); this spec adds only its language rule and its mandatory status.

### Modules

| Module | Interface (what callers see) | Lives in |
|---|---|---|
| Notifications | Receive a domain event (Submission status change, Submission becoming Outdated, Notice received or closed, Withdrawal, Redaction, Reinstatement, Invitation issued); resolve recipients, applying opt-out and the performer rule; enqueue one email job per recipient | backend (`api`) |
| Email rendering | Render one email kind for one recipient and language from the backend message catalogue into a plain-text and a minimal HTML part | backend (`worker`) |
| Moderator digest | A daily scheduled job that builds and enqueues one digest per Moderator who chose it, when something new has arrived | backend (`worker`) |
| Notification preferences | Read and update a User's "Updates on my Submissions" switch and, for Moderators, their Submission email mode | backend, Account page (frontend) |

Email sending goes through the Foundations email port and its SMTP adapter. The domain modules that raise events depend only on the notifications module's narrow event interface, never on email rendering.

### Email catalogue

Each row is one email kind. "Mandatory" emails cannot be turned off. Content columns list what the email must contain; every email also summarises the event and links to its page ([Form and delivery](#form-and-delivery)).

**Submitter emails**

| Email | Trigger | Recipient | Opt-out | Content |
|---|---|---|---|---|
| Changes requested | A Moderator sets the Submission to **changes requested** | The Submitter | Optional ("Updates on my Submissions") | The **Decision message**; the date on which the Submission is retracted if no one responds ([Submission lifecycle edge cases](https://github.com/spippoli/tart/issues/96)); link to the Submission page |
| Approved | A Moderator approves the Submission | The Submitter | Optional ("Updates on my Submissions") | Link to the published record |
| Rejected | A Moderator rejects the Submission | The Submitter | Mandatory | The Decision message, given as the Art. 17 statement of reasons ([Statement of reasons](#statement-of-reasons)); link to the Submission page |
| Outdated | An open Submission (**submitted** or **changes requested**) becomes **Outdated** | The Submitter | Optional ("Updates on my Submissions") | That the Submission must be revised before it can be approved; link to the Submission page |

- **Outdated** emails go only to open Submissions, once per transition to Outdated. Outdated is computed, not a status ([#5](https://github.com/spippoli/tart/issues/5)), so the transition is the moment the Submission changes from not Outdated to Outdated.
- No email on **submitted**: the Submission page confirms it. No email on **retracted**: it is the Submitter's own act, and after account deletion there is no address.
- Merge, Duplicate retirement, and Unmerge are Submissions ([ADR 0018](../adr/0018-merge-as-reconciling-multi-record-submission.md)) and get the same emails.

**Moderator emails**

| Email | Trigger | Recipient | Opt-out | Content |
|---|---|---|---|---|
| Notice received | A Notice is sent | Every Moderator, including one whose own content is reported; never the Operator | Mandatory; immediate up to the hourly cap, never in the digest | The Notice reason, the reported URL, a link to the Notice page |
| Notices summary | The hourly cap of Notice received was reached for a Moderator in the hour that ends | That Moderator | Mandatory | The number of Notices not emailed one by one, and a link to the Notice queue |
| New Submission | A Submission is submitted or resubmitted | Every Moderator whose mode is *one email per Submission* | Optional (Submission email mode) | The derived kind; the record's current name, or "new" plus the kind for a record not yet approved (never a proposed name); new or resubmitted; a link to the Submission page; the number of pending Submissions that Moderator may decide, counted as in the digest. No Submitter name and no note to Moderators ([Notice handling details](https://github.com/spippoli/tart/issues/94)) |
| Moderator digest | Daily, see [Moderator digest](#moderator-digest) | Every Moderator whose mode is *digest* | Optional (Submission email mode) | Pending count, the new Submissions (kind, record, link), the oldest one waiting |

- Notice received is always sent and cannot be turned off or moved into the digest, for the Art. 16 timing ([#19](https://github.com/spippoli/tart/issues/19)).
- **Hourly cap** ([Security constants and abuse protection](https://github.com/spippoli/tart/issues/84)): each Moderator receives at most 10 Notice received emails per clock hour. Past the cap, the later Notices of that hour are not emailed one by one; at the end of the hour that Moderator receives one Notices summary instead. Every Notice is recorded and listed in the queue regardless.
- The Submission email mode is one of *one email per Submission*, *Moderator digest* (the default), and *no email*.

**Legal emails** ([ADR 0013](../adr/0013-hide-not-delete-for-legal-removals.md), DSA Art. 16–17)

| Email | Trigger | Recipient | Opt-out | Content |
|---|---|---|---|---|
| Notice acknowledgement | A Notice is sent with an email address | The notifier | Mandatory | The Notice reference (`N-XXXX-XXXX`, [Rights and legal actions](rights-and-legal-actions.md#2-notices)); a copy of the reason, URL, and explanation; that the decision will follow by email |
| Notice decision | The Notice is closed | The notifier, if they gave an email | Mandatory | The decision (Withdrawal, Redaction, no action, or already removed); the Notice reference; the short reason, which is the Moderator's facts and reasons text (none for already removed); the redress block ([Notice handling details](https://github.com/spippoli/tart/issues/94)) |
| Statement of reasons | A Withdrawal, Redaction, Reinstatement, or Purge is performed, or a Submission is rejected | The affected Submitters (for a Purge, those of the purged measure) | Mandatory | See [Statement of reasons](#statement-of-reasons) |

- The rejection email of the Submitter table *is* the statement of reasons for a rejection; it is one email, not two.
- The affected Submitters are as defined in [ADR 0013](../adr/0013-hide-not-delete-for-legal-removals.md): for a Documentation item, the Submitter who created it; for a record, its creator and the Submitters of the affected Revisions.
- A Submitter gets no email when a Notice arrives about their content, only when a measure is taken. This keeps the notifier anonymous and avoids pressure before the decision.
- A notifier gets no email on a later Reinstatement.
- A notifier who gave no email gets no email. The notifier's name and email are erased six months after the decision ([ADR 0013](../adr/0013-hide-not-delete-for-legal-removals.md)).
- Every legal email sets `Reply-To` to the Operator's DSA contact, `contacts.dsa` ([Instance configuration keys and contacts](https://github.com/spippoli/tart/issues/85)), because contesting is done by reply ([ADR 0013](../adr/0013-hide-not-delete-for-legal-removals.md)).

**Account and access emails**

| Email | Trigger | Recipient | Opt-out | Specified in |
|---|---|---|---|---|
| Sign-in code | A code is requested | The email address entered | Mandatory | [Foundations](foundations.md) ([ADR 0005](../adr/0005-passwordless-in-app-auth.md)) |
| Invitation | A Moderator issues an Invitation in the Moderation area, or the Operator runs `tart invites create <email>` | The invited address | Mandatory | Contribution and moderation ([#43](https://github.com/spippoli/tart/issues/43)) |
| Registration not open | A code is requested, under `invite` or `closed`, for an address that may not register | The email address entered, in the sign-in page's UI language | Mandatory | [Foundations](foundations.md#2-authentication-and-sessions) ([Security constants and abuse protection](https://github.com/spippoli/tart/issues/84)) |
| Suspension | The Operator runs `tart users suspend` | The suspended User | Mandatory; `Reply-To` is `contacts.dsa`, so a reply contests the Suspension | [Foundations](foundations.md#2-authentication-and-sessions) ([Security constants and abuse protection](https://github.com/spippoli/tart/issues/84)); carries the reason given to the command and the redress block |
| New address code | A User asks to change their email address | The new address | Mandatory | [Foundations](foundations.md#2-authentication-and-sessions) ([#87](https://github.com/spippoli/tart/issues/87)); a one-time code with the sign-in code's rules |
| Address already in use | A User asks to change their email to an address that already has a User | That address | Mandatory; sent instead of the code, so the page's answer stays neutral | [Foundations](foundations.md#2-authentication-and-sessions) ([#87](https://github.com/spippoli/tart/issues/87)) |
| Email changed | An email change is confirmed | The old address | Mandatory | [Foundations](foundations.md#2-authentication-and-sessions) ([#87](https://github.com/spippoli/tart/issues/87)); the new address masked, and how to contest by writing to `contacts.privacy` |
| Deletion code | A User starts account deletion | The account's address | Mandatory | [Rights and legal actions](rights-and-legal-actions.md#9-account-deletion) ([#87](https://github.com/spippoli/tart/issues/87)); a one-time code with the sign-in code's rules. No email follows the deletion |

Under `registration = invite` the Invitation link can also be copied by the issuing Moderator ([#43](https://github.com/spippoli/tart/issues/43)); the email is sent regardless.

### Statement of reasons

Sent for every Withdrawal, Redaction, Reinstatement, Purge, and Submission rejection to every affected Submitter ([ADR 0013](../adr/0013-hide-not-delete-for-legal-removals.md)). It gives:

1. the measure taken;
2. the facts it rests on;
3. whether it followed a Notice or was taken on the Instance's own initiative;
4. the ground in the terms of use or the law;
5. that no automated means were used (never, in the MVP);
6. redress: the redress block.

For a rejection, the Decision message (a configured reason plus free text, [#5](https://github.com/spippoli/tart/issues/5)) supplies the facts and ground. For Withdrawal and Redaction, the ground (a Notice reason) and the facts and reasons text are captured on the measure form, and for a Reinstatement the facts and reasons text, as specified in [Rights and legal actions](rights-and-legal-actions.md#2-notices); for a Purge, by the Operator CLI's `--ground` (never its `--reference`). This spec renders them.

**Redress block** ([Notice handling details](https://github.com/spippoli/tart/issues/94)). Every legal email (statements of reasons, the Notice decision, Suspension) ends with the same platform text: contest by replying to this email, which reaches `contacts.dsa`, or go to court. Out-of-court settlement is not mentioned: DSA Art. 21 is an online-platform duty that small Instances are exempt from, and Art. 17(3)(f) asks for redress routes only where applicable. The text is a catalogue string, not configuration. ⚖️ legal review.

### Recipient rules

- **Performer rule.** No email goes to the person who performed the action. Account and access emails a User triggers for their own account (sign-in code, New address code, Address already in use, Email changed, Deletion code) are the exception, since they are the action's proof or its safeguard. For example, a Moderator approving their own Submission under `self_approval = true` gets no Approved email; a Moderator submitting a Submission gets no New Submission email for it.
- **Moderator anonymity.** Emails never name the Moderator; they say "a Moderator" ([#43](https://github.com/spippoli/tart/issues/43)).
- **No address, no email.** A User whose account was deleted has no email address ([ADR 0013](../adr/0013-hide-not-delete-for-legal-removals.md)); nothing is sent to them. A statement of reasons due to such a User is recorded as not sent in the legal action log, and its Submission log entry is still written; nothing else is done, since DSA Art. 17(2) applies the duty only where contact details are known ([Notice handling details](https://github.com/spippoli/tart/issues/94)). ⚖️ legal review.
- **Digest and self-approval.** A Moderator's digest counts the Submissions that Moderator may decide: with `self_approval = false` it leaves out their own, with `true` it counts them. Their own Submissions are never listed as new, by the performer rule ([#93](https://github.com/spippoli/tart/issues/93)).
- **Notices about a Moderator's content.** The rule that a Submitter learns nothing before a measure applies to Submitters as such; a Moderator whose content is reported receives Notice received like every other Moderator. The Operator is not a recipient: with no Moderator, nobody receives it, and the configuration warning in Foundations flags that state.

### Opt-out

- **Mandatory** (no switch): the sign-in code, the Invitation, Registration not open, Suspension, all legal emails (rejection, Withdrawal, Redaction, Reinstatement, Purge, Notice acknowledgement and decision) and, for Moderators, Notice received and the Notices summary.
- **Optional, for every User**: one Account-page switch, "Updates on my Submissions", on by default, covering Changes requested, Approved, and Outdated.
- **Optional, for Moderators**: the Submission email mode on the Account page, default *Moderator digest*. The setting is shown only to Moderators.
- Every optional email links to the Account page in its footer. There is no RFC 8058 one-click unsubscribe, because these are transactional emails.

### Moderator digest

- Sent daily at 08:00 in the Instance time zone (`geography.time_zone`), a platform constant ([Security constants and abuse protection](https://github.com/spippoli/tart/issues/84)).
- Sent to a Moderator only when something new (a new or resubmitted Submission by another User) has arrived since that Moderator's previous digest; otherwise nothing is sent. The Moderator's own Submissions are never "something new".
- Lists the pending count, the new Submissions (kind, record, link), and the oldest Submission waiting.
- The pending count and the oldest Submission waiting cover the Submissions the Moderator may decide: with `self_approval = false` they leave out the Moderator's own, with `true` they include them. The list of new Submissions always leaves them out.
- Notices are never in the digest.

### Language

Per [ADR 0008](../adr/0008-single-content-language-and-prefixed-ui-languages.md) as amended by [Notifications](https://github.com/spippoli/tart/issues/44):

| Recipient | Email language |
|---|---|
| Registered User | Their preferred UI language; initially the UI language of the page they registered from. If the Instance has disabled it, the Instance's default UI language. This includes the emails of an email change, to the new and the old address |
| Notifier | The UI language of the Notice form, stored with the Notice |
| Unregistered address receiving a sign-in code | The UI language of the sign-in page |
| Invitee | The issuing Moderator's UI language, or the Instance default when issued from `tart invites create` |

- Quoted content (record titles, Decision message free text, the notifier's own explanation) keeps its own language. Configured labels (Decision message reasons, Notice reasons) are translated into the recipient's language.
- Every user-facing string in an email (subject, body text, labels, footer, statuses) comes from the backend message catalogue, held to the missing-key check ([ADR 0008](../adr/0008-single-content-language-and-prefixed-ui-languages.md)). No email text is hardcoded in templates or code.
- Dates use the recipient's language and the Instance time zone ([ADR 0008](../adr/0008-single-content-language-and-prefixed-ui-languages.md)).

### Form and delivery

- **Format**: multipart, plain text plus minimal HTML. No remote images, tracking pixels, or tracked links.
- **Sender**: the From name is the archive name in the Content language; the From address comes from the SMTP environment settings.
- **Subjects and wording** ([Notice handling details](https://github.com/spippoli/tart/issues/94)): every subject reads `[<archive name>] <event>`, short, with no Submission content and no person's name. A statement of reasons gives the six elements in order, each under its own heading; the Notice decision gives the decision, the short reason, the Notice reference, and the redress block. The wording of every subject and body is an implementation task: catalogue strings in every platform UI language, without invented legal formulas. The legal texts and the redress block need legal review before launch ([Operations and portability](operations-and-portability.md#9-operator-compliance-checklist), checklist item 3). ⚖️
- **Content**: each email summarises the event and links to its page; it does not copy Submission content or files. The Notice acknowledgement is the one exception: it echoes the notifier's own input.
- **Reply-To**: the Operator's DSA contact on legal emails ([Legal emails](#email-catalogue)).
- **Delivery**: the `worker` sends with bounded retries and backoff ([Security constants and abuse protection](https://github.com/spippoli/tart/issues/84)):
  - **ordinary emails**: 6 attempts in all, the retries 1, 5, 15, 60, and 240 minutes after the previous attempt, about 5½ hours in total;
  - **sign-in code**: 3 attempts, at 0, 30 seconds, and 2 minutes, then `failed`: a late code is useless, since it expires after 10 minutes and the User can ask for another. The sign-in page does not report the failure (its answer stays neutral), but the failure counts for the Email health check like any other.

  A final failure leaves the email job `failed` and is logged for the Operator, who lists failed jobs with `tart jobs failed` and retries them with `tart jobs retry <id|--all>`. Any permanently failed email in the last 24 hours turns the Email health check to `fail`, which the Operator's external monitor sees on `/api/health` and the `worker` reports to `OPERATOR_ALERT_EMAIL` at most once per check per day ([Operations and portability](operations-and-portability.md#5-monitoring), from [Backups, upgrades and monitoring](https://github.com/spippoli/tart/issues/45)). Bounce and complaint handling is not in the MVP.

## Testing Decisions

A good test drives a module through its external interface and asserts observable behaviour (which emails were captured, for whom, with what headers and text), never internal calls. Prior art: the Foundations email adapter that captures messages, used by the authentication tests.

- **Recipient resolution (unit, pytest)**: for each event, the set of emails and recipients, including the performer rule, the "Updates on my Submissions" switch, each Moderator mode, `self_approval` true and false, a deleted User, a notifier with and without an email, no Submitter email on Notice received, no notifier email on Reinstatement, and the Outdated "open Submissions only, once per transition" rule.
- **Rendering (unit, pytest)**: each email kind in every platform UI language, from fixtures of fictional records marked as fictional: both parts present; no remote resources or tracking parameters in the HTML; no Moderator name; quoted content unchanged while configured labels are translated; the statement of reasons contains all six elements; `Reply-To` set on legal emails only; footer Account link on optional emails only.
- **Language selection (unit)**: the four recipient cases of [Language](#language), and the fallback when a User's preferred UI language is disabled.
- **Digest (integration, against PostgreSQL with a controlled clock)**: sent at the configured hour in the Instance time zone; skipped when nothing new arrived; contents (count, new items, oldest waiting); own Submissions left out under `self_approval = false`.
- **Delivery (integration)**: a failing SMTP adapter triggers bounded retries and, after the last, a logged failure; Mailpit for manual checks in development.
- **End to end (Playwright with axe)**: the Account-page notification settings in both UI languages, keyboard-only, with the Moderator mode shown only to Moderators.
- **i18n**: the backend catalogue's missing-key check covers every email string.
- **Rendering**: each email renders in every platform UI language and contains its required elements (the subject pattern, the six headed elements of a statement, the redress block); tests never assert exact wording.

## Acceptance criteria

**Submitter emails**
1. Requesting changes sends the Submitter an email with the Decision message and a link to the Submission page, unless their "Updates on my Submissions" switch is off.
2. Approving sends the Submitter an email linking to the published record, unless the switch is off.
3. Rejecting always sends the Submitter an email containing the Decision message and the six statement-of-reasons elements, whatever the switch.
4. An open Submission (submitted or changes requested) becoming Outdated sends one email per transition; a Submission in a final status becoming Outdated sends none.
5. Submitting, resubmitting, and retracting send no email to the Submitter.

**Moderator emails**
6. A new Notice sends every Moderator an immediate email with the reason, the reported URL, and a link to the Notice page, whatever their Submission email mode.
7. A new or resubmitted Submission sends one email to each Moderator in *one email per Submission* mode and none to others.
8. A Moderator in *digest* mode receives at most one digest per day, at the platform-constant hour in the Instance time zone, only if something new arrived since their previous digest, listing the pending count, the new Submissions, and the oldest one waiting.
9. With `self_approval = false`, a Moderator's digest omits their own Submissions; with `true`, its pending count and oldest waiting include them, but they are never listed as new and alone never trigger a digest.
10. A new Moderator defaults to *digest*; a new User's "Updates on my Submissions" switch defaults to on.

**Legal emails**
11. A Notice with an email address gets an immediate acknowledgement with the Notice reference and a copy of the reason, URL, and explanation; a Notice without one gets none.
12. Closing a Notice sends the notifier (if they gave an email) the decision, the Notice reference, the short reason (none for already removed), and the redress block.
13. A Withdrawal, Redaction, Reinstatement, or Purge sends every affected Submitter, as defined in ADR 0013 (for a Purge, those of the purged measure), a statement of reasons with all six elements.
14. No email goes to a Submitter when a Notice about their content arrives; no email goes to a notifier on a later Reinstatement.
15. Every legal email has `Reply-To` set to `contacts.dsa`.
16. Legal emails, Notice received, the sign-in code, and the Invitation cannot be turned off from any setting.

**All emails**
17. No email goes to the person who performed the action, except the account and access emails a User triggers for their own account.
18. No email names a Moderator.
19. Every email has a plain-text and an HTML part; the HTML loads no remote resource and contains no tracking pixel or tracked link.
20. No email copies Submission content or files, except the Notice acknowledgement echoing the notifier's own input.
21. Every optional email has a footer link to the Account page; no email has a one-click unsubscribe header.
22. The From name is the archive name in the Content language.
23. Each email is in the language set by [Language](#language); quoted content keeps its own language, configured labels are translated, and dates use the Instance time zone.
24. Every email string comes from the backend message catalogue; a missing key fails CI.
25. A failed send is retried 5 times, 1, 5, 15, 60, and 240 minutes after the previous attempt, and a sign-in code twice, 30 seconds and 2 minutes after; a final failure is logged and leaves the job `failed`.

**Account page**
26. The notification settings on the Account page pass axe with no WCAG 2.2 AA violations in every enabled UI language; each control has a visible, translated label, is keyboard-operable, and does not convey its state by colour alone.

**Self-review** ([Operator as decider and Moderator self-review](https://github.com/spippoli/tart/issues/93))

27. A Notice about a Moderator's own content sends Notice received to that Moderator as well; no Notice received is ever sent to an Operator address.

**Abuse protection** ([Security constants and abuse protection](https://github.com/spippoli/tart/issues/84))

28. Twelve Notices within one clock hour send each Moderator 10 Notice received emails and, at the end of the hour, one Notices summary counting 2; all twelve are in the queue.
29. A code request under `invite` or `closed` for an address that may not register sends Registration not open, in the sign-in page's UI language, and no code.
30. `tart users suspend <email> --reason <text>` sends the User a Suspension email carrying the reason, with `Reply-To` set to `contacts.dsa`; `tart users unsuspend` sends nothing.
31. The Moderator digest is sent at 08:00 in `geography.time_zone`.

**Notice handling and wording** ([Notice handling details](https://github.com/spippoli/tart/issues/94))

32. A New Submission email gives the derived kind, the record's current name or "new" plus the kind, whether it is new or resubmitted, the link, and the pending count, and never the Submitter's name, the note to Moderators, or a proposed name.
33. Every legal email, the Suspension email included, ends with the same redress block, naming an email reply and the courts and not out-of-court settlement.
34. A statement of reasons due to a deleted account sends nothing and is recorded as not sent.
35. Every subject reads `[<archive name>] <event>`

**Account emails** ([Accounts: registration, email change, deletion and export](https://github.com/spippoli/tart/issues/87))

36. An email change sends New address code to the new address and, once confirmed, Email changed to the old one, both in the User's preferred UI language; a change to an address in use sends Address already in use and no code; account deletion sends a Deletion code and nothing after the deletion.

## Instance configuration

The [Foundations](foundations.md#1-instance-configuration) spec owns `instance.toml` and the file layout; this spec reads the following values.

| Setting | Key or path | Use here | Rome |
|---|---|---|---|
| Archive name (Content language) | `identity.name` | From name | "Archivio dell'arte urbana di Roma" |
| Content language | `languages.content` | Language of the From name | `it` |
| Enabled UI languages, default first | `languages.ui` | Email language; fallback when a User's language is disabled; Invitations from the CLI | `it` (default), `en` |
| Time zone | `geography.time_zone` | Digest hour; dates in emails | `Europe/Rome` |
| DSA contact | `contacts.dsa` | `Reply-To` of legal emails | Launch value ([Foundations](foundations.md#romes-launch-values)) |
| Decision message reasons, Notice reasons (labels per UI language) | `vocabularies/decision_reasons.toml` plus the platform's `duplicate`, `vocabularies/notice_reasons.toml` | Translated labels quoted in emails | [Rome's Decision message reasons](contribution-and-moderation.md#romes-decision-message-reasons), [Rome's Notice reasons](rights-and-legal-actions.md#romes-notice-reasons) |
| Self-review | `community.self_approval` | Digest contents | `true` at launch |
| Registration mode | `community.registration` | Whether Invitation emails occur (`invite` only) | `open` |

Environment: the SMTP settings, including the From address ([ADR 0009](../adr/0009-instance-configuration-as-validated-files.md)).

**Platform constants, not configuration**: the digest hour (08:00), the retry schedules (ordinary emails: 6 attempts at 1, 5, 15, 60, and 240 minutes; sign-in code: 3 attempts at 0, 30 seconds, and 2 minutes), the Notice received cap (10 per Moderator per hour, then one summary), and the Invitation expiry (14 days, [#43](https://github.com/spippoli/tart/issues/43)).

## Out of Scope

- An in-app notification centre ([spec index](index.md#out-of-scope-for-the-mvp)).
- Bounce and complaint handling, and suppression lists.
- RFC 8058 one-click unsubscribe.
- Any engagement email: newsletters, activity feeds, "people viewed your contribution", popularity or follower notices.
- Notifications about records a User did not submit (watching or following records, Artists, or Areas).
- Emails to the public or to Artists as such; an Artist record has no link to a User ([ADR 0014](../adr/0014-artist-records-hold-only-a-public-identity.md)).
- An in-app complaint system; contesting is by email reply ([ADR 0013](../adr/0013-hide-not-delete-for-legal-removals.md)).
- The actions that raise the events and the inputs they collect (Contribution and moderation; Rights and legal actions).
- Non-email channels (SMS, push, chat).

## Further Notes

Not normative.

### Open items

The inputs leave these questions unsettled. Implementers must not fill them by assumption; each needs a decision (a resolution comment or an ADR) before the affected ticket is built.

**Recipients**
1. **Notice about a Moderator's own content.** Answered by [Operator as decider and Moderator self-review](https://github.com/spippoli/tart/issues/93): that Moderator receives Notice received like every Moderator; see Recipient rules.
2. **No Moderator, or Operator escalation.** Answered by [Operator as decider and Moderator self-review](https://github.com/spippoli/tart/issues/93): the Operator receives no Notice received and has no decision path of its own; with no Moderator the Notice waits, and startup warns.
3. **Own Submissions under `self_approval = true`.** Answered by [Operator as decider and Moderator self-review](https://github.com/spippoli/tart/issues/93): they count in the pending count and the oldest waiting, but are never listed as new and never trigger a digest; see Moderator digest.
4. **Statements of reasons to deleted accounts.** Answered by [Notice handling details](https://github.com/spippoli/tart/issues/94): nothing else is sent; the legal action log records the statement as not sent, and the Submission log entry is written; ⚖️ legal review of the Art. 17(2) reading. See Recipient rules.

**Content**
5. **Redress text in statements of reasons.** Answered by [Notice handling details](https://github.com/spippoli/tart/issues/94): one redress block in every legal email, email reply and courts, without out-of-court settlement; ⚖️ legal review. See Statement of reasons.
6. **Notice decision "short reason".** Answered by [Notice handling details](https://github.com/spippoli/tart/issues/94): the Moderator's facts and reasons text, the same as element 2 of the Submitters' statement; see [Rights and legal actions](rights-and-legal-actions.md#2-notices).
7. **Notice reference.** Answered by [Notice handling details](https://github.com/spippoli/tart/issues/94): a random `N-XXXX-XXXX` code, separate from the Notice id; see [Rights and legal actions](rights-and-legal-actions.md#2-notices).
8. **Per-Submission email content.** Answered by [Notice handling details](https://github.com/spippoli/tart/issues/94): kind, record name, new or resubmitted, link, and the pending count; see [Email catalogue](#email-catalogue).
9. **Email subjects and wording.** Answered by [Notice handling details](https://github.com/spippoli/tart/issues/94): implementation detail, within the subject pattern and the fixed structure of legal emails, with legal review of the legal texts before launch; see [Form and delivery](#form-and-delivery).

**Configuration**
10. **Legal contact.** Answered by [Instance configuration keys and contacts](https://github.com/spippoli/tart/issues/85): `Reply-To` is the DSA contact, `contacts.dsa`; there is no separate legal contact key.
11. **Archive name for the From name.** Answered by [Rome Instance values](https://github.com/spippoli/tart/issues/86): "Archivio dell'arte urbana di Roma".
12. **Platform constants.** Answered by [Security constants and abuse protection](https://github.com/spippoli/tart/issues/84): digest at 08:00 in the Instance time zone; ordinary emails 6 attempts over about 5½ hours; the sign-in code 3 attempts within 2 minutes; see [Moderator digest](#moderator-digest) and [Form and delivery](#form-and-delivery).

**Delivery and abuse**
13. **Abuse of the Notice form.** Answered by [Security constants and abuse protection](https://github.com/spippoli/tart/issues/84): per-IP and per-notifier-email limits, a honeypot and minimum fill time ([Rights and legal actions](rights-and-legal-actions.md#2-notices)), and an hourly cap of 10 Notice received emails per Moderator with a summary past it; see [Email catalogue](#email-catalogue).
14. **Visibility of delivery failures.** Answered by [Backups, upgrades and monitoring](https://github.com/spippoli/tart/issues/45): a permanently failed email turns the Email health check to `fail` (external monitor on `/api/health`, alert email to `OPERATOR_ALERT_EMAIL`), and `tart jobs failed` / `tart jobs retry` list and retry failed jobs; see Form and delivery.

**Interactions with other specs**
15. **Email address change.** Answered by [Accounts: registration, email change, deletion and export](https://github.com/spippoli/tart/issues/87): New address code, Address already in use, and Email changed, all mandatory, plus a Deletion code for account deletion; see [Email catalogue](#email-catalogue).
16. **Notice page route.** Answered by [Notice handling details](https://github.com/spippoli/tart/issues/94): `/it/moderazione/segnalazioni/{id}` (`/en/moderation/notices/{id}`); see [Rights and legal actions](rights-and-legal-actions.md#2-notices).

### Notes

- The language rules of [#44](https://github.com/spippoli/tart/issues/44), recorded in [ADR 0008](../adr/0008-single-content-language-and-prefixed-ui-languages.md), answer [Foundations open item 17](foundations.md#open-items) (language of a sign-in code to an unregistered address) and the initial-language part of item 15 (initial preferred UI language). The Foundations spec is not edited by this PR.
- Links in emails would naturally point to pages under the email language's prefix ([ADR 0010](../adr/0010-public-url-scheme.md)); no decision states it.
- HTML parts should set `lang` to the email language and mark quoted content with its own `lang`, mirroring how pages render content ([ADR 0008](../adr/0008-single-content-language-and-prefixed-ui-languages.md)).
- Example fixtures for rendering tests must use fictional records, marked as fictional, with no claims about real artworks or artists.
