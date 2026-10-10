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

**Decision tickets incorporated**: [Notifications](https://github.com/spippoli/tart/issues/44) (the whole of this spec's content), and, for the parts that shape emails, [Submission and moderation lifecycle](https://github.com/spippoli/tart/issues/5) (statuses, Outdated, Decision message), [Content rights and GDPR product rules](https://github.com/spippoli/tart/issues/14) (Notice acknowledgement, statements of reasons, contesting by email), [Research: Digital Services Act duties for an archive Instance](https://github.com/spippoli/tart/issues/19) (Art. 16 and 17 elements, as background), [Moderation roles and permissions](https://github.com/spippoli/tart/issues/43) (`self_approval`, Moderator anonymity, Invitation email), [Backups, upgrades and monitoring](https://github.com/spippoli/tart/issues/45) (visibility of failed emails), [Instance configuration keys and contacts](https://github.com/spippoli/tart/issues/85) (the DSA contact as `Reply-To`), and [Operator as decider and Moderator self-review](https://github.com/spippoli/tart/issues/93) (Notice received recipients, digest contents).

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
| Changes requested | A Moderator sets the Submission to **changes requested** | The Submitter | Optional ("Updates on my Submissions") | The **Decision message**; link to the Submission page |
| Approved | A Moderator approves the Submission | The Submitter | Optional ("Updates on my Submissions") | Link to the published record |
| Rejected | A Moderator rejects the Submission | The Submitter | Mandatory | The Decision message, given as the Art. 17 statement of reasons ([Statement of reasons](#statement-of-reasons)); link to the Submission page |
| Outdated | An open Submission (**submitted** or **changes requested**) becomes **Outdated** | The Submitter | Optional ("Updates on my Submissions") | That the Submission must be revised before it can be approved; link to the Submission page |

- **Outdated** emails go only to open Submissions, once per transition to Outdated. Outdated is computed, not a status ([#5](https://github.com/spippoli/tart/issues/5)), so the transition is the moment the Submission changes from not Outdated to Outdated.
- No email on **submitted**: the Submission page confirms it. No email on **retracted**: it is the Submitter's own act, and after account deletion there is no address.
- Merge, Duplicate retirement, and Unmerge are Submissions ([ADR 0018](../adr/0018-merge-as-reconciling-multi-record-submission.md)) and get the same emails.

**Moderator emails**

| Email | Trigger | Recipient | Opt-out | Content |
|---|---|---|---|---|
| Notice received | A Notice is sent | Every Moderator, including one whose own content is reported; never the Operator | Mandatory; always immediate, never in the digest | The Notice reason, the reported URL, a link to the Notice page |
| New Submission | A Submission is submitted or resubmitted | Every Moderator whose mode is *one email per Submission* | Optional (Submission email mode) | A summary and a link to the Submission page (exact content: Open item 8) |
| Moderator digest | Daily, see [Moderator digest](#moderator-digest) | Every Moderator whose mode is *digest* | Optional (Submission email mode) | Pending count, the new Submissions (kind, record, link), the oldest one waiting |

- Notice received is always sent and cannot be turned off or moved into the digest, for the Art. 16 timing ([#19](https://github.com/spippoli/tart/issues/19)).
- The Submission email mode is one of *one email per Submission*, *Moderator digest* (the default), and *no email*.

**Legal emails** ([ADR 0013](../adr/0013-hide-not-delete-for-legal-removals.md), DSA Art. 16–17)

| Email | Trigger | Recipient | Opt-out | Content |
|---|---|---|---|---|
| Notice acknowledgement | A Notice is sent with an email address | The notifier | Mandatory | The Notice reference; a copy of the reason, URL, and explanation; that the decision will follow by email |
| Notice decision | The Notice is closed | The notifier, if they gave an email | Mandatory | The decision (Withdrawal, Redaction, or no action), a short reason, and redress: email reply, out-of-court settlement, courts |
| Statement of reasons | A Withdrawal, Redaction, or Reinstatement is performed, or a Submission is rejected | The affected Submitters | Mandatory | See [Statement of reasons](#statement-of-reasons) |

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

Under `registration = invite` the Invitation link can also be copied by the issuing Moderator ([#43](https://github.com/spippoli/tart/issues/43)); the email is sent regardless.

### Statement of reasons

Sent for every Withdrawal, Redaction, Reinstatement, and Submission rejection to every affected Submitter ([ADR 0013](../adr/0013-hide-not-delete-for-legal-removals.md)). It gives:

1. the measure taken;
2. the facts it rests on;
3. whether it followed a Notice or was taken on the Instance's own initiative;
4. the ground in the terms of use or the law;
5. that no automated means were used (never, in the MVP);
6. redress, starting with replying to the email.

For a rejection, the Decision message (a configured reason plus free text, [#5](https://github.com/spippoli/tart/issues/5)) supplies the facts and ground. For Withdrawal, Redaction, and Reinstatement, the inputs are captured by the Moderator as specified in Rights and legal actions; this spec renders them.

### Recipient rules

- **Performer rule.** No email goes to the person who performed the action. For example, a Moderator approving their own Submission under `self_approval = true` gets no Approved email; a Moderator submitting a Submission gets no New Submission email for it.
- **Moderator anonymity.** Emails never name the Moderator; they say "a Moderator" ([#43](https://github.com/spippoli/tart/issues/43)).
- **No address, no email.** A User whose account was deleted has no email address ([ADR 0013](../adr/0013-hide-not-delete-for-legal-removals.md)); nothing is sent to them.
- **Digest and self-approval.** A Moderator's digest counts the Submissions that Moderator may decide: with `self_approval = false` it leaves out their own, with `true` it counts them. Their own Submissions are never listed as new, by the performer rule ([#93](https://github.com/spippoli/tart/issues/93)).
- **Notices about a Moderator's content.** The rule that a Submitter learns nothing before a measure applies to Submitters as such; a Moderator whose content is reported receives Notice received like every other Moderator. The Operator is not a recipient: with no Moderator, nobody receives it, and the configuration warning in Foundations flags that state.

### Opt-out

- **Mandatory** (no switch): the sign-in code, the Invitation, all legal emails (rejection, Withdrawal, Redaction, Reinstatement, Notice acknowledgement and decision) and, for Moderators, Notice received.
- **Optional, for every User**: one Account-page switch, "Updates on my Submissions", on by default, covering Changes requested, Approved, and Outdated.
- **Optional, for Moderators**: the Submission email mode on the Account page, default *Moderator digest*. The setting is shown only to Moderators.
- Every optional email links to the Account page in its footer. There is no RFC 8058 one-click unsubscribe, because these are transactional emails.

### Moderator digest

- Sent daily, at a platform-constant hour in the Instance time zone.
- Sent to a Moderator only when something new (a new or resubmitted Submission by another User) has arrived since that Moderator's previous digest; otherwise nothing is sent. The Moderator's own Submissions are never "something new".
- Lists the pending count, the new Submissions (kind, record, link), and the oldest Submission waiting.
- The pending count and the oldest Submission waiting cover the Submissions the Moderator may decide: with `self_approval = false` they leave out the Moderator's own, with `true` they include them. The list of new Submissions always leaves them out.
- Notices are never in the digest.

### Language

Per [ADR 0008](../adr/0008-single-content-language-and-prefixed-ui-languages.md) as amended by [Notifications](https://github.com/spippoli/tart/issues/44):

| Recipient | Email language |
|---|---|
| Registered User | Their preferred UI language; initially the UI language of the page they registered from. If the Instance has disabled it, the Instance's default UI language |
| Notifier | The UI language of the Notice form, stored with the Notice |
| Unregistered address receiving a sign-in code | The UI language of the sign-in page |
| Invitee | The issuing Moderator's UI language, or the Instance default when issued from `tart invites create` |

- Quoted content (record titles, Decision message free text, the notifier's own explanation) keeps its own language. Configured labels (Decision message reasons, Notice reasons) are translated into the recipient's language.
- Every user-facing string in an email (subject, body text, labels, footer, statuses) comes from the backend message catalogue, held to the missing-key check ([ADR 0008](../adr/0008-single-content-language-and-prefixed-ui-languages.md)). No email text is hardcoded in templates or code.
- Dates use the recipient's language and the Instance time zone ([ADR 0008](../adr/0008-single-content-language-and-prefixed-ui-languages.md)).

### Form and delivery

- **Format**: multipart, plain text plus minimal HTML. No remote images, tracking pixels, or tracked links.
- **Sender**: the From name is the archive name in the Content language; the From address comes from the SMTP environment settings.
- **Content**: each email summarises the event and links to its page; it does not copy Submission content or files. The Notice acknowledgement is the one exception: it echoes the notifier's own input.
- **Reply-To**: the Operator's DSA contact on legal emails ([Legal emails](#email-catalogue)).
- **Delivery**: the `worker` sends with bounded retries and backoff. A final failure leaves the email job `failed` and is logged for the Operator, who lists failed jobs with `tart jobs failed` and retries them with `tart jobs retry <id|--all>`. Any permanently failed email in the last 24 hours turns the Email health check to `fail`, which the Operator's external monitor sees on `/api/health` and the `worker` reports to `OPERATOR_ALERT_EMAIL` at most once per check per day ([Operations and portability](operations-and-portability.md#5-monitoring), from [Backups, upgrades and monitoring](https://github.com/spippoli/tart/issues/45)). Bounce and complaint handling is not in the MVP.

## Testing Decisions

A good test drives a module through its external interface and asserts observable behaviour (which emails were captured, for whom, with what headers and text), never internal calls. Prior art: the Foundations email adapter that captures messages, used by the authentication tests.

- **Recipient resolution (unit, pytest)**: for each event, the set of emails and recipients, including the performer rule, the "Updates on my Submissions" switch, each Moderator mode, `self_approval` true and false, a deleted User, a notifier with and without an email, no Submitter email on Notice received, no notifier email on Reinstatement, and the Outdated "open Submissions only, once per transition" rule.
- **Rendering (unit, pytest)**: each email kind in every platform UI language, from fixtures of fictional records marked as fictional: both parts present; no remote resources or tracking parameters in the HTML; no Moderator name; quoted content unchanged while configured labels are translated; the statement of reasons contains all six elements; `Reply-To` set on legal emails only; footer Account link on optional emails only.
- **Language selection (unit)**: the four recipient cases of [Language](#language), and the fallback when a User's preferred UI language is disabled.
- **Digest (integration, against PostgreSQL with a controlled clock)**: sent at the configured hour in the Instance time zone; skipped when nothing new arrived; contents (count, new items, oldest waiting); own Submissions left out under `self_approval = false`.
- **Delivery (integration)**: a failing SMTP adapter triggers bounded retries and, after the last, a logged failure; Mailpit for manual checks in development.
- **End to end (Playwright with axe)**: the Account-page notification settings in both UI languages, keyboard-only, with the Moderator mode shown only to Moderators.
- **i18n**: the backend catalogue's missing-key check covers every email string.

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
12. Closing a Notice sends the notifier (if they gave an email) the decision, a short reason, and redress (email reply, out-of-court settlement, courts).
13. A Withdrawal, Redaction, or Reinstatement sends every affected Submitter, as defined in ADR 0013, a statement of reasons with all six elements.
14. No email goes to a Submitter when a Notice about their content arrives; no email goes to a notifier on a later Reinstatement.
15. Every legal email has `Reply-To` set to `contacts.dsa`.
16. Legal emails, Notice received, the sign-in code, and the Invitation cannot be turned off from any setting.

**All emails**
17. No email goes to the person who performed the action.
18. No email names a Moderator.
19. Every email has a plain-text and an HTML part; the HTML loads no remote resource and contains no tracking pixel or tracked link.
20. No email copies Submission content or files, except the Notice acknowledgement echoing the notifier's own input.
21. Every optional email has a footer link to the Account page; no email has a one-click unsubscribe header.
22. The From name is the archive name in the Content language.
23. Each email is in the language set by [Language](#language); quoted content keeps its own language, configured labels are translated, and dates use the Instance time zone.
24. Every email string comes from the backend message catalogue; a missing key fails CI.
25. A failed send is retried a bounded number of times with backoff, and a final failure is logged.

**Account page**
26. The notification settings on the Account page pass axe with no WCAG 2.2 AA violations in every enabled UI language; each control has a visible, translated label, is keyboard-operable, and does not convey its state by colour alone.

**Self-review** ([Operator as decider and Moderator self-review](https://github.com/spippoli/tart/issues/93))

27. A Notice about a Moderator's own content sends Notice received to that Moderator as well; no Notice received is ever sent to an Operator address.

## Instance configuration

The [Foundations](foundations.md#1-instance-configuration) spec owns `instance.toml` and the file layout; this spec reads the following values.

| Setting | Key or path | Use here | Rome |
|---|---|---|---|
| Archive name (Content language) | `identity.name` | From name | Not decided ([Foundations open item 1](foundations.md#open-items)) |
| Content language | `languages.content` | Language of the From name | `it` |
| Enabled UI languages, default first | `languages.ui` | Email language; fallback when a User's language is disabled; Invitations from the CLI | `it` (default), `en` |
| Time zone | `geography.time_zone` | Digest hour; dates in emails | `Europe/Rome` |
| DSA contact | `contacts.dsa` | `Reply-To` of legal emails | Not decided |
| Decision message reasons, Notice reasons (labels per UI language) | `vocabularies/decision_reasons.toml` plus the platform's `duplicate`, `vocabularies/notice_reasons.toml` | Translated labels quoted in emails | Not decided |
| Self-review | `community.self_approval` | Digest contents | `true` at launch |
| Registration mode | `community.registration` | Whether Invitation emails occur (`invite` only) | `open` |

Environment: the SMTP settings, including the From address ([ADR 0009](../adr/0009-instance-configuration-as-validated-files.md)).

**Platform constants, not configuration**: the digest hour, the retry count and backoff, and the Invitation expiry (14 days, [#43](https://github.com/spippoli/tart/issues/43)).

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
4. **Statements of reasons to deleted accounts.** A deleted User has no address, so an affected Submitter whose account was deleted receives no statement of reasons. Whether the Art. 17 duty needs any other handling in that case is not decided (and ties to the legal-review item on "affected recipients", [#19](https://github.com/spippoli/tart/issues/19) item 5).

**Content**
5. **Redress text in statements of reasons.** The notifier's decision email lists email reply, out-of-court settlement, and courts. For statements of reasons the decisions say "redress" and "contesting by email reply" only; whether they list the same three routes is not decided. Out-of-court settlement under DSA Art. 21 is an online-platform duty that small Instances may be exempt from ([#19](https://github.com/spippoli/tart/issues/19)); legal review applies.
6. **Notice decision "short reason".** Whether it is the same text as the ground in the Submitters' statement of reasons, a separate Moderator input, or a configured label is not decided; Rights and legal actions owns the inputs.
7. **Notice reference.** The acknowledgement carries "the Notice reference"; its format (for example the Notice identifier) is not decided.
8. **Per-Submission email content.** The digest lists kind, record, and link; the decisions do not detail the *one email per Submission* content beyond the general rule (summarise and link). Whether it carries the same three items is not decided.
9. **Email subjects and wording.** No decision fixes subjects or body wording; they are catalogue strings to be written, in every platform UI language, without inventing legal text that needs review.

**Configuration**
10. **Legal contact.** Answered by [Instance configuration keys and contacts](https://github.com/spippoli/tart/issues/85): `Reply-To` is the DSA contact, `contacts.dsa`; there is no separate legal contact key.
11. **Archive name for the From name.** Rome's archive name in the Content language (`it`) is not decided ([Foundations open item 1](foundations.md#open-items)).
12. **Platform constants.** The digest hour, the retry count, and the backoff schedule are not decided. Whether the sign-in code, which expires after 10 minutes, needs a shorter retry window than other emails is not stated.

**Delivery and abuse**
13. **Abuse of the Notice form.** The Notice form needs no login and accepts any email address, so it can make the Instance send acknowledgements to arbitrary addresses and flood Moderators with Notice received emails. Rate limiting of Notices is still unticketed ("Performance and limits" in the [spec index](index.md#traceability)).
14. **Visibility of delivery failures.** Answered by [Backups, upgrades and monitoring](https://github.com/spippoli/tart/issues/45): a permanently failed email turns the Email health check to `fail` (external monitor on `/api/health`, alert email to `OPERATOR_ALERT_EMAIL`), and `tart jobs failed` / `tart jobs retry` list and retry failed jobs; see Form and delivery.

**Interactions with other specs**
15. **Email address change.** Whether changing the Account email sends a confirmation code to the new address is [Foundations open item 16](foundations.md#open-items); if so, it is a further mandatory email.
16. **Notice page route.** Notice received links to "the Notice page"; that Moderator page and its route belong to Rights and legal actions and are not in the [#15](https://github.com/spippoli/tart/issues/15) route table.

### Notes

- The language rules of [#44](https://github.com/spippoli/tart/issues/44), recorded in [ADR 0008](../adr/0008-single-content-language-and-prefixed-ui-languages.md), answer [Foundations open item 17](foundations.md#open-items) (language of a sign-in code to an unregistered address) and the initial-language part of item 15 (initial preferred UI language). The Foundations spec is not edited by this PR.
- Links in emails would naturally point to pages under the email language's prefix ([ADR 0010](../adr/0010-public-url-scheme.md)); no decision states it.
- HTML parts should set `lang` to the email language and mark quoted content with its own `lang`, mirroring how pages render content ([ADR 0008](../adr/0008-single-content-language-and-prefixed-ui-languages.md)).
- Example fixtures for rendering tests must use fictional records, marked as fictional, with no claims about real artworks or artists.
