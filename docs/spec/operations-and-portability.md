# Operations and portability

Feature spec 7 of 7 in the [delivery order](index.md#delivery-order). It covers how an **Operator** keeps an **Instance** running and its archive safe and reusable: releases and upgrades, backups and restore, monitoring and logs, the public **Data dump**, and the Operator compliance checklist with the Operator documentation that carries it. It depends on every spec above it: [Foundations](foundations.md) (topology, Instance configuration, `config_version`, Operator CLI, storage adapter, `worker`, email adapter), [Archive records](archive-records.md) (record kinds, physical history, visibility, public pages, redirects), Contribution and moderation (Moderator role, `self_approval`, Submission log), [Rights and legal actions](rights-and-legal-actions.md) (Withdrawal, Purge, account deletion, Notice log, processing inventory), and [Notifications](notifications.md) (email delivery and its failures). Compile ticket: [Compile Operations and portability spec](https://github.com/spippoli/tart/issues/56).

Every section except Further Notes is normative. The invariants, language rules, and implementation principles in [`CLAUDE.md`](../../CLAUDE.md) apply and override any reading of this spec that contradicts them. Terms in **bold** are [glossary](../../GLOSSARY.md) terms and carry exactly that meaning ([spec index, Sources of truth](index.md#sources-of-truth)).

## References

**ADRs applied**

| ADR | What this spec takes from it |
|---|---|
| [0004](../adr/0004-mvp-tech-stack.md) | Docker Compose topology (`caddy`, `frontend`, `api`, `worker`, `db`), Procrastinate jobs on PostgreSQL, storage adapter (filesystem or S3), sizing, the dependency licence allow-list in CI; backups outside the hosting budget |
| [0009](../adr/0009-instance-configuration-as-validated-files.md) | Secret-free configuration directory vs environment for infrastructure and secrets; fail-fast validation and `tart config check`; `config_version` with manual migration; `data_license` |
| [0011](../adr/0011-provisional-software-license.md) | Never call TART "Open Source"; "Powered by TART" permitted, not mandatory; the archive's identity stays distinct from TART; the software licence covers no archive data |
| [0012](../adr/0012-per-file-licence-with-rights-basis.md) | Data licence values; per-file licence, **Creator credit**, **Rights basis**; capped public renditions without EXIF; `min_age` |
| [0013](../adr/0013-hide-not-delete-for-legal-removals.md) | Withdrawal hides, Purge erases only when the law requires it; Purge and data exports run from the Operator CLI; account deletion is self-service; notifier data erased six months after the decision |
| [0016](../adr/0016-licence-policy-for-map-assets-and-data.md) | CI allow-list for asset packages and the third-party asset manifest; map attribution list; Operator documentation requires the OpenStreetMap attribution; tile extract and overlays are Instance data under the ODbL |
| [0018](../adr/0018-merge-as-reconciling-multi-record-submission.md) | Merged and duplicate-retired ids keep resolving to the surviving record |
| [0020](../adr/0020-backups-replay-erasures-and-forward-only-upgrades.md) | `pg_dump` into restic and encrypted `rclone sync --backup-dir` of media; backups never rewritten; the **Erasure log** replayed on every restore; `tart upgrade` with a pre-upgrade backup; forward-only migrations; rollback by restore; `api` and `worker` refuse to start on a revision mismatch |

**Glossary terms applied**: Instance, Operator, Instance configuration, Data licence, Data dump, Licensor, Content language, UI language, User, Moderator, Moderation note, Submission, Submission log, Archive record, Revision, Artwork, Artist, Location, Site, Area, Series, Source, Documentation item, Creator credit, Rights basis, History event, Claim, Attribution, Crew membership, Uncertain date, Merge, Duplicate retirement, Withdrawal, Redaction, Reinstatement, Purge, Erasure log, Notice.

**Decision tickets incorporated**: [Backups, upgrades and monitoring](https://github.com/spippoli/tart/issues/45), [Operator compliance checklist](https://github.com/spippoli/tart/issues/46), and [Public data dump](https://github.com/spippoli/tart/issues/47) (the core of this spec), and, for the parts that reach operations, [Tech stack decision](https://github.com/spippoli/tart/issues/13) (topology, sizing), [Licensing Decision Record (provisional)](https://github.com/spippoli/tart/issues/12) (CI licence allow-list, brand), [Licence policy for map assets and basemap data](https://github.com/spippoli/tart/issues/35) (CI allow-list, Operator documentation), [Basemap tile pipeline per Instance](https://github.com/spippoli/tart/issues/38) (tiles out of backups, tile cadence, external tile provider), and [Moderation roles and permissions](https://github.com/spippoli/tart/issues/43) (checklist items on `self_approval` and Moderation notes). Background research: [Research: archive data and contributor content licensing, GDPR](https://github.com/spippoli/tart/issues/8) (a public dump for preservation, distinct from portability), [Research: media pipeline and storage within budget](https://github.com/spippoli/tart/issues/10) (off-site media backups), [Research: Digital Services Act duties for an archive Instance](https://github.com/spippoli/tart/issues/19) (the checklist's legal basis), [Instance configuration keys and contacts](https://github.com/spippoli/tart/issues/85) (`operator.name`, the shape of `data_attribution`, `tart config check --database`), [Operator as decider and Moderator self-review](https://github.com/spippoli/tart/issues/93) (the Operator acts on Notices as a Moderator).

**Depends on**: every earlier feature spec, as listed above.

## Problem Statement

An Instance is usually run by a small volunteer group on one modest server. The archive's whole promise is that nothing is lost: a painted-over work stays a record, and so must the database that holds it survive a broken disk, a bad upgrade, a compromised server, or an Operator who walks away. At the same time, real erasures (a Purge, an account deletion) must not come back from a backup, and an old copy of personal data must not linger without limit. Upgrades must be safe for someone who is not a professional administrator: one command, a backup first, a clear way back. When something breaks (email stops, the `worker` dies, backups stop running) the Operator must hear about it before contributors do, without the platform phoning home or exposing personal data to a monitoring service.

Beyond the Instance itself, an archive meant for preservation must be able to outlive it: researchers and other projects need the public data in an open, documented format under the Instance's Data licence, without the dump leaking what the Instance has hidden or erased, and without implying that the Data licence covers photographs or the depicted works. Finally, running an Instance carries legal duties (DSA, GDPR, and in Italy AGCOM) that the software cannot discharge: the Operator needs a concrete checklist of what to do before launch, at launch, routinely, and when something happens.

## Solution

The platform ships generic, versioned images and a Compose stack. Backups are a platform-owned, opt-in `backup` service: a nightly `pg_dump` into an encrypted restic repository and an encrypted `rclone sync` of media to a target with a protection the server cannot delete, plus the configuration directory. A weekly automatic verify restores the latest dump into a temporary database and checks it. Backups are never rewritten; Purges and account deletions are recorded in the Erasure log, which every restore applies again. `tart upgrade <version>` takes a tagged backup, checks the configuration with the new image, and runs forward-only migrations while the services are stopped; rollback is a restore of that backup. A public health endpoint feeds an external monitor of the Operator's choice, a token-protected endpoint gives the details, and the `worker` emails the Operator when a check fails. Logs are structured, kept about 14 days, and never carry emails, codes, tokens, or Notice content.

The Operator produces a Data dump with `tart dump`: a zip of the current public archive (NDJSON per record kind, GeoJSON of Locations, a redirects table, a manifest, licence and README) that holds exactly what public pages show, validated against a published JSON Schema, with an optional package of public renditions. Publishing it is the Operator's choice. The Operator compliance checklist, grouped by phase and delivered as an Operator guide, lists the legal and operational duties the software cannot perform, with an Italy annex and legal-review flags.

## User Stories

**Operator: backups and restore**

1. As an Operator, I want to turn on backups by configuring a target and secrets in the environment, so that I don't write my own backup scripts.
2. As an Operator, I want the health details to say that backups are not configured, as a warning rather than a failure, so that I am reminded without the Instance appearing down.
3. As an Operator, I want a nightly backup of the database, media, and configuration directory to a separate location, so that losing the server does not lose the archive.
4. As an Operator, I want backups encrypted before they leave the server, so that the backup provider cannot read the archive's personal data.
5. As an Operator, I want daily, weekly, and monthly snapshots kept for six months, so that I can go back past a problem I noticed late.
6. As an Operator, I want a weekly automatic restore test with an alert when it fails, so that I know my backups can actually be restored.
7. As an Operator, I want a restore to apply again every Purge and account deletion made since the restored dump, so that restoring never brings back data the law required me to erase.
8. As an Operator, I want my backup target to keep snapshots the server cannot delete, so that a compromised server cannot destroy the backups.
9. As an Operator, I want to restore the archive onto a new server, so that I can move host or hand the Instance over to another Operator.

**Operator: upgrades**

10. As an Operator, I want to pin the platform version in `.env` and upgrade with one command, so that upgrades are deliberate and repeatable.
11. As an Operator, I want every upgrade to take a backup first and to check my configuration against the new version before stopping anything, so that a failed upgrade leaves me a way back.
12. As an Operator, I want the services to refuse to start on a database that doesn't match the code, so that a half-done upgrade never runs.
13. As an Operator, I want release notes with an "Operator actions" section, and majors reserved for releases that need my action, so that I know when to read carefully.
14. As an Operator, I want to watch releases myself rather than have the Instance call home, so that my Instance contacts no one I did not choose.

**Operator: monitoring**

15. As an Operator, I want a public health endpoint that says only ok or fail, so that an external monitor can watch it without seeing anything private.
16. As an Operator, I want a protected endpoint listing each check with its value and threshold, so that I can see what is wrong.
17. As an Operator, I want an email when a check fails, at most once per check per day, so that I hear about problems without being flooded.
18. As an Operator, I want to list and retry failed jobs from the CLI without personal data shown in clear, so that I can recover from an email outage.
19. As an Operator, I want logs rotated after about 14 days and free of emails, codes, tokens, and Notice content, so that logs help with incidents without becoming a store of personal data.

**Operator: data dump**

20. As an Operator, I want to produce a Data dump of the public archive with one command, so that I can deposit it with a preservation service.
21. As an Operator, I want to decide whether, where, and how often to publish it, so that publication fits my Instance's means and policy.
22. As an Operator, I want an optional media package of public renditions with a per-file licence manifest, so that I can publish images only where their licences allow it.

**Reuser and researcher**

23. As a researcher, I want the dump to contain every public record with its full physical history, Attributions, citations, and Uncertain dates with their precision, so that I can study the archive offline.
24. As a reuser, I want the dump to state its Data licence and attribution, and that this licence covers neither the files nor the depicted Artworks, so that I reuse it lawfully.
25. As a GIS user, I want a GeoJSON file of Locations with their Artworks, so that I can open the archive in my tools.
26. As a reuser, I want a redirects table for merged and retired ids, so that my references to old ids keep resolving.
27. As a developer, I want a versioned JSON Schema for the dump, so that I can validate it and build tools on it.

**Contributor and data subject**

28. As a Submitter, I want my User name absent from the dump, so that a published dump cannot outlive my account deletion with my identity.
29. As a person whose content was withdrawn or purged, I want the dump to contain only what public pages show, and the Operator to replace a published dump after a Withdrawal or Purge, so that a dump does not keep exposing what was hidden.

**Moderator**

30. As a Moderator, I want to know that Moderation notes are personal data subject to access requests, so that I keep them factual.

**Prospective Operator**

31. As someone starting an Instance, I want a checklist of legal and operational duties by phase, with what is national and what needs legal review, so that I know what to do before going live.
32. As a publicly controlled body, I want to be warned up front that the MVP does not support my duties, so that I seek legal advice before launch.

## Implementation Decisions

### Scope and dependencies

- This spec owns the release channel, `tart upgrade`, the startup revision guard's behaviour for Operators, the `backup` service and `tart backup`, the Erasure log's replay on restore, health checks and alerting, log rules, failed-job handling, the Data dump, the Operator compliance checklist, and the Operator documentation that carries them.
- It does not own what writes to the Erasure log or what a Purge leaves behind: Purge and account deletion are specified by [Rights and legal actions](rights-and-legal-actions.md); this spec only requires that each writes an Erasure log entry and replays them on restore ([ADR 0020](../adr/0020-backups-replay-erasures-and-forward-only-upgrades.md)).
- It does not own a User's GDPR access or portability export (Rights and legal actions), nor the Instance configuration loader and `tart config check` (Foundations), nor `tart tiles update` (Discovery).
- The CI checks (missing message keys, OpenAPI drift, the dependency licence allow-list of [ADR 0011](../adr/0011-provisional-software-license.md), the asset manifest of [ADR 0016](../adr/0016-licence-policy-for-map-assets-and-data.md)) are specified as acceptance criteria in [Foundations](foundations.md); this spec adds image publishing on tags.

### Modules

| Module | Interface (what callers see) | Lives in |
|---|---|---|
| Release pipeline | On a SemVer tag, build and publish the generic `api` and `frontend` images to GHCR | maintainer's CI |
| Backup | `tart backup run`, `tart backup verify`, `tart backup restore`; the nightly and weekly schedule; reports last success times to Health | `backup` Compose service (profile), Operator CLI |
| Erasure log | Append a content-free entry (kind, target id, date); replay all entries against a restored database | backend (written by Purge and account deletion, read by restore) |
| Upgrade | `tart upgrade <version>`: the ordered steps of [Upgrades](#4-upgrades) | Operator CLI |
| Revision guard | At startup, compare the database's Alembic revision with the code's head; refuse to start on a mismatch | `api`, `worker` |
| Health | Run the checks; serve `GET /api/health` and the token-protected `GET /api/health/details` | backend (`api`) |
| Alerting | Email the Operator when a check turns `fail`, at most once per check per day; ping `BACKUP_PING_URL` after backup and verify | `worker`, `backup` |
| Jobs admin | `tart jobs failed`, `tart jobs retry <id\|--all>`; delete completed jobs after 30 days | Operator CLI, `worker` |
| Data dump | `tart dump [--with-media]`: write the dump package (and optionally the media package) to the data volume | Operator CLI |
| Operator documentation | Runbook, `.env.example`, and the compliance guide `docs/operator/compliance.md` | platform repository |

Backup and Data dump read the database and storage through the same storage adapter as the application, so filesystem and S3 storage take the same path. The domain modules that perform Purge and account deletion depend only on the Erasure log's append interface.

### 1. Deployment and releases

- **Topology and sizing** are as in [Foundations](foundations.md#topology-and-stack) ([ADR 0004](../adr/0004-mvp-tech-stack.md)): a Docker Compose stack with `caddy`, `frontend`, `api`, `worker`, and `db`, plus the optional `backup` service as a Compose profile. Reference sizing is 4 GB RAM minimum, 8 GB recommended ([#13](https://github.com/spippoli/tart/issues/13)).
- **Images.** Generic prebuilt images on GHCR, published by the maintainer's CI on tags: `api` (which also runs `worker` and the Operator CLI) and `frontend`. No Instance-specific image is built.
- **Versioning.** SemVer on a single stable channel:
  - **patch**: fixes, and rebuilds for relevant base-image CVEs;
  - **minor**: features, with compatible migrations;
  - **major**: anything needing Operator action (a `config_version` bump, a manual step, a PostgreSQL major upgrade).
- **Pinning.** Compose reads `TART_VERSION` from `.env`. The `latest` tag is never used.
- **Release notes** always have an "Operator actions" section. Minor releases can be skipped; majors are applied in order.
- **No phone-home.** The Instance never checks for updates. Operators watch GitHub releases or their Atom feed (checklist item 19).
- **Host.** Host OS security updates are the Operator's: the runbook explains them and the checklist lists them (item 13).

### 2. Backups

**Ownership.** Backups are platform-owned and opt-in: an optional `backup` Compose service (profile) and `tart backup run|verify|restore`, configured through the environment (repository, encryption secrets, schedule). Until backups are configured, `/api/health/details` reports the backup check as a `not_configured` **warning**, not a failure. Provider snapshots of the server are an optional extra, mentioned in the runbook. Rome turns backups on at launch.

**Tools.**
- Database: `pg_dump` in custom format into a restic repository.
- Media: `rclone sync --backup-dir` through an rclone `crypt` remote, to the same target. Objects deleted from storage move to `deleted/YYYY-MM-DD` and are emptied after **30 days**. The path is the same for filesystem and S3 storage, which works because objects are immutable with unique keys.

**Scope.**

| In the backup | Left out |
|---|---|
| Database (restic snapshot) | PMTiles extract and overlays: regenerated by `tart tiles update` and the committed overlay method ([#38](https://github.com/spippoli/tart/issues/38)) |
| Media (encrypted rclone copy) | Caddy state |
| Configuration directory (in the restic snapshot beside the dump) | `.env`: kept off the server with the backup secrets; the runbook ships `.env.example` |

The small tile manifest in the data volume may be included ([#38](https://github.com/spippoli/tart/issues/38)).

**Schedule.**
- One nightly job, at a time set in the environment: the database dump first, then media, so that every object the dump references is already in storage.
- An on-demand backup before each upgrade ([Upgrades](#4-upgrades)).
- No WAL archiving or point-in-time recovery: the recovery point objective is 24 hours.

**Retention.**
- Database: restic `forget` keeps 7 daily, 4 weekly, and 6 monthly snapshots; a weekly `prune`; a weekly `restic check --read-data-subset`.
- The retention defaults can be overridden in the environment (infrastructure, not TOML, per [ADR 0009](../adr/0009-instance-configuration-as-validated-files.md)).
- Media: see the 30-day `deleted/` window above.

**Target.** The general runbook rule: the backup target must have a protection the server cannot delete (for example provider-side snapshots the server's credentials cannot remove), in a different location from the server. Single-provider risk is accepted for the MVP; an occasional second copy downloaded by the Operator is optional good practice. Rome's target is in [Instance configuration](#instance-configuration).

**Secrets.** The restic password, the rclone crypt key, the target credentials, and `.env` are kept **off the server** as well: in the Operator's password manager and with a second person (checklist item 12).

### 3. Restore and the Erasure log

- Backups are never rewritten to honour a Purge or an account deletion ([ADR 0020](../adr/0020-backups-replay-erasures-and-forward-only-upgrades.md)).
- Every Purge and every account deletion writes a content-free entry to the **Erasure log**: kind, target id, date. A Purge therefore leaves this tombstone; the rest of what a Purge leaves behind is specified by [Rights and legal actions](rights-and-legal-actions.md#8-purge).
- `tart backup restore` restores the chosen dump, then applies again the Erasure log of the most recent dump. Media erasures leave the backup within 30 days through `--backup-dir`.
- The processing inventory states that erased data may stay in encrypted backups for up to six months ([Processing inventory](#8-processing-inventory)).
- **Verify (automatic, weekly).** `tart backup verify` restores the latest dump into a temporary database in the `db` container and checks that:
  1. the Alembic revision equals the code's head;
  2. the record counts per kind equal those stored as snapshot metadata at backup time;
  3. a sample of media keys exists in the backup copy.

  It then drops the temporary database. A failure raises an alert ([Monitoring](#5-monitoring)).
- **Drill (manual).** A full restore on a clean machine before launch and then yearly (checklist items 15 and 20).
- **Handover.** A move to a new server, or a handover between Operators of the same Instance, uses backup and restore, not the Data dump ([#47](https://github.com/spippoli/tart/issues/47)).

### 4. Upgrades

**`tart upgrade <version>`** runs these steps in order:

1. a backup tagged `pre-upgrade-<from>-<to>`;
2. `tart config check --database` with the new image;
3. pull the images;
4. stop `api`, `worker`, and `frontend`;
5. run the Alembic migrations in a one-shot container;
6. start the services;
7. wait for a green health check.

If a step fails, the command stops and prints the rollback instructions. Because the configuration is checked before anything stops, an incompatible configuration aborts the upgrade with the service still running.

- **No migrations at startup.** `api` and `worker` refuse to start when the database revision differs from the code's head, in the same fail-fast style as `config_version` ([ADR 0020](../adr/0020-backups-replay-erasures-and-forward-only-upgrades.md); [Foundations](foundations.md#topology-and-stack)).
- **Downtime.** Brief downtime is accepted: no expand/contract migrations and no blue-green deployment.
- **Rollback.** Migrations run forward only; there are no `downgrade` scripts. A rollback restores the `pre-upgrade` backup (including the Erasure log replay) and sets the previous `TART_VERSION`. Contributions made after the upgrade are lost, so a rollback only makes sense right after an upgrade.
- **PostgreSQL major upgrades** are a dump and restore described in a major release's notes, never automatic.
- **`config_version`** ([ADR 0009](../adr/0009-instance-configuration-as-validated-files.md), confirmed): bumped only by a change that breaks existing configuration directories (a renamed or removed key, or a new required key without a default), and therefore only in a major release. A new optional key with a default does not bump it. Migration is manual: the release notes give a before/after TOML example for each change. There is no `tart config migrate` in the MVP.

### 5. Monitoring

**Health endpoints.**
- `GET /api/health` is public and returns only `ok` or `fail`, with a matching HTTP status. It exposes no check names, values, or personal data.
- `GET /api/health/details` is protected by a token set in the environment and returns each check with its value and threshold.

**Checks and default thresholds** (each threshold can be overridden in the environment):

| Check | Healthy when |
|---|---|
| Database | Reachable |
| Storage | Reachable: a probe object can be written and read |
| `worker` heartbeat | Younger than 2 minutes |
| Job queue | Oldest queued job younger than 15 minutes |
| Email | Permanently failed emails in the last 24 hours equal 0 |
| Disk | Free disk above 20% |
| Backup | Last successful backup younger than 26 hours; `not_configured` warning when backups are not configured |
| Verify | Last successful verify younger than 8 days |

**Alerting.**
- The primary channel is an **external monitor** of the Operator's choice polling `/api/health` (for example Uptime Kuma on another machine, or a free hosted service). The monitor sees no personal data; it is named in the checklist (item 14).
- Optional dead-man's switch: `BACKUP_PING_URL` (environment) receives a generic `GET` at the end of each backup and each verify, compatible with Healthchecks.io or a self-hosted equivalent.
- As reinforcement, the `worker` emails `OPERATOR_ALERT_EMAIL` (environment) when a check turns `fail`, at most once per check per day.

**Logs.**
- `api`, `worker`, and `frontend` write structured JSON to stdout. Docker's `json-file` driver rotates them per service, configured in the Compose file and sized for about **14 days**.
- Application logs carry the User id and never emails, sign-in codes, tokens, or Notice content.
- Caddy access logs stay on (abuse and incident handling); their IP addresses are rotated out after about 14 days.
- Both kinds of log are listed in the processing inventory.

**Jobs.**
- Procrastinate retries with backoff. A job that exhausts its attempts stays `failed`; a failed email job counts towards the Email check.
- `tart jobs failed` lists failed jobs without personal data in clear; `tart jobs retry <id|--all>` retries one or all.
- Completed jobs are deleted after 30 days.

### 6. Data dump

A **Data dump** is an Operator-produced export of the current state of the public archive under the Instance's Data licence. It is distinct from the private, encrypted backup ([ADR 0020](../adr/0020-backups-replay-erasures-and-forward-only-upgrades.md)) and from a User's GDPR export ([Rights and legal actions](rights-and-legal-actions.md#10-data-exports)).

**Content.** The current state of every approved, public Archive record (Artwork, Artist, Location, Site, Area, Series, Source, Documentation item) with the full physical history: History events, Attributions, Crew memberships, citations, Uncertain dates with their precision, and the submitted and approved dates of Claims.

**Exclusion rule.** The dump holds exactly what public pages show, and nothing else. In particular it excludes:
- **Revisions and User names**: once published, a dump escapes later Redactions and account deletions, so the audit trail stays on the Instance's `/revisions` pages, where Withdrawal and Redaction still work;
- pending, draft, rejected, and retracted Submissions, the Submission log, and Moderation notes;
- withdrawn records and Documentation items, and a withdrawn Artist's Attributions and Crew memberships;
- Purged content;
- Users, Notices, the legal action log, and the Erasure log.

Creator credits appear as shown publicly, so anonymised ones stay anonymised.

**Redirects.** A `redirects` table maps merged and duplicate-retired ids to the surviving id, with the date, so that external references keep resolving ([ADR 0018](../adr/0018-merge-as-reconciling-multi-record-submission.md)). The content of retired records is not included.

**Media.**
- Documentation item metadata is always included: kind, file licence, Creator credit, Rights basis, third-party origin URL, and public rendition URL. Text Documentation items are included with their licence.
- `tart dump --with-media` also writes a separate media package of **public renditions only** (never originals; resolution-capped; no EXIF) with a per-file licence manifest listing each file's licence, Creator credit, and origin URL. The Operator decides whether to publish it.

**Format.** A `.zip` containing:

| File | Content |
|---|---|
| `manifest.json` | Dump schema version, TART version, archive name, Content language, Data licence, generation time, counts per kind |
| One NDJSON file per record kind | The records of that kind |
| `redirects.ndjson` | Retired id → surviving id, with the date |
| `locations.geojson` | A FeatureCollection of Locations with their Artworks as properties, for GIS tools |
| `LICENSE` | See below |
| `README` | See below |

- Stable ids; references by id; GeoJSON geometries; Uncertain dates as modelled (value plus precision).
- Vocabulary values are exported as stable keys with labels in the enabled UI languages.
- A **JSON Schema**, versioned with SemVer, is published with the platform. Every dump validates against it.

**Completeness and re-import.** The format is committed to being complete for public data, so that a future importer could rebuild the archive into a new Instance (with no Users and an initial import Revision). There is no importer in the MVP; bulk import stays out of scope.

**Licence and notices.** The package is under the Instance's Data licence.
- `LICENSE`: the licence name, version, official URL, and full legal text, generated from the configured `licenses.data`, including the ODbL notice when applicable.
- `README`, in the Content language and in English, with:
  - the attribution text: `licenses.data_attribution`, one string in the Content language quoted as is in both README languages, or by default the archive name and `operator.name`; the platform always follows it with the Instance URL and the dump date ([Instance configuration keys and contacts](https://github.com/spippoli/tart/issues/85)). It is a courtesy request when the licence is CC0;
  - a statement that the Data licence covers neither Documentation item files (each has its own licence in the manifest) nor the depicted Artworks (there is no freedom of panorama in Italy);
  - a **non-binding request** that reusers drop content withdrawn after the dump date and prefer the latest dump. It is a request, not a condition, because CC and ODbL licences forbid additional restrictions;
  - "Powered by TART" with the TART version, granting no software licence ([ADR 0011](../adr/0011-provisional-software-license.md)).

**Production and publication.** `tart dump` writes the package to the data volume. Whether, where (for example Zenodo, the Internet Archive, or the Operator's own site), and how often to publish is the Operator's choice. There is no periodic dump job, and the Instance neither hosts nor links to dumps. After a Withdrawal or Purge, the Operator replaces any published dump and publishes only the latest one (checklist item 23).

### 7. Operator CLI additions

These join the [Foundations Operator CLI](foundations.md#5-operator-cli):

| Command | Behaviour |
|---|---|
| `tart backup run` | Run a backup now (database dump, then media, then configuration directory) |
| `tart backup verify` | Restore the latest dump into a temporary database and check revision, counts, and a media sample |
| `tart backup restore` | Restore a chosen dump, then replay the Erasure log of the most recent dump |
| `tart upgrade <version>` | The seven steps of [Upgrades](#4-upgrades) |
| `tart jobs failed` | List failed jobs without personal data in clear |
| `tart jobs retry <id\|--all>` | Retry one or all failed jobs |
| `tart dump [--with-media]` | Write the Data dump, and optionally the media package, to the data volume |

### 8. Processing inventory

The platform's processing inventory is specified in [Rights and legal actions](rights-and-legal-actions.md#11-processing-inventory). This spec adds these entries:

| Category | Purpose | Retention |
|---|---|---|
| Application logs (User id; never emails, codes, tokens, or Notice content) | Operation, incident handling | About 14 days (log rotation) |
| Caddy access logs (IP addresses) | Abuse and incident handling | IP addresses rotated out after about 14 days |
| Backups (encrypted copies of the database, media, and configuration) | Recovery | Up to six months; erased data may remain until the snapshot holding it expires, and is erased again on restore |

### 9. Operator compliance checklist

**Form.** The checklist is this section. Implementation delivers it as an Operator guide, `docs/operator/compliance.md`, in the platform repository, written in English like all project documentation. There is no CLI command for it: what software can verify, `tart config check` already checks (terms, privacy policy, DSA contact, map attribution); the remaining items happen outside the software.

**Structure.** Items are grouped by phase: before launch, at launch, ongoing, on event. Each item states who acts (Operator or Moderator), where it lives (configuration, CLI, host, or an external document), and its legal or ADR basis. The core covers the EU; an **Italy annex** (🇮🇹) is the only national annex in the MVP. Items marked ⚖️ need legal review.

**Opening warning.** An Operator that is 25% or more publicly controlled (a city, a public museum, or a university) is never an SME and may owe the full online-platform duties. The MVP does not support them, so such an Operator must get legal advice before launch. ⚖️

**Before launch**

| # | Item | Who | Where | Basis |
|---|---|---|---|---|
| 1 | Read the public-control warning above. ⚖️ | Operator | — | [#46](https://github.com/spippoli/tart/issues/46) |
| 2 | Name the Operator: the legal or natural person acting as DSA provider and GDPR controller. A legal entity (for example an association) is recommended over an individual, because approved content may fall outside the DSA Art. 6 hosting exemption. | Operator | External document | DSA, GDPR; [#46](https://github.com/spippoli/tart/issues/46) |
| 3 | Write terms of use that describe moderation, the Notice reasons list, and redress by email reply. | Operator | Configuration (Markdown) | DSA Art. 14; [ADR 0013](../adr/0013-hide-not-delete-for-legal-removals.md) |
| 4 | Write the privacy notice and the record of processing activities, starting from the platform's processing inventory. Name every external recipient, including an external tile provider when the map style uses one. | Operator | Configuration (Markdown) and external document | GDPR Art. 13, 30; [#38](https://github.com/spippoli/tart/issues/38) |
| 5 | Sign data processing agreements with the hosting, storage, and SMTP providers. | Operator | External document | GDPR Art. 28 |
| 6 | Set up points of contact for authorities and for users, with their languages (`contacts.dsa`, `contacts.dsa_languages`), plus a privacy contact (`contacts.privacy`); replies to legal emails reach `contacts.dsa`. | Operator | Configuration | DSA Art. 11–12 |
| 7 | Choose `licenses.data`, `licenses.files` (default first), `community.min_age` (🇮🇹 14), and the map attribution list; when the basemap uses OpenStreetMap data, include `© OpenStreetMap` → `https://www.openstreetmap.org/copyright`. | Operator | Configuration | [ADR 0009](../adr/0009-instance-configuration-as-validated-files.md), [0012](../adr/0012-per-file-licence-with-rights-basis.md), [0016](../adr/0016-licence-policy-for-map-assets-and-data.md) |
| 8 | Grant at least one Moderator through the CLI and name who handles escalation. | Operator | CLI | [#43](https://github.com/spippoli/tart/issues/43), [#46](https://github.com/spippoli/tart/issues/46) |
| 9 | Tell Moderators that Moderation notes are personal data subject to access requests, so they must stay factual. | Operator, Moderators | Operator guide | GDPR Art. 15; [#43](https://github.com/spippoli/tart/issues/43) |
| 10 | Read the Art. 6 position: approved records may not be shielded by the hosting exemption. ⚖️ | Operator | — | DSA Art. 6; [#19](https://github.com/spippoli/tart/issues/19) |
| 11 | Brand: "Powered by TART" is optional; never call TART "Open Source"; the archive's name stays distinct from TART. | Operator | Configuration, public texts | [ADR 0011](../adr/0011-provisional-software-license.md) |
| 12 | Keep the backup secrets (restic password, rclone crypt key, target credentials) and `.env` off the server: in a password manager and with a second person. | Operator | External | [#45](https://github.com/spippoli/tart/issues/45) |
| 13 | Enable host OS security updates. | Operator | Host | [#45](https://github.com/spippoli/tart/issues/45) |
| 14 | Set up an external monitor polling `/api/health`; it sees no personal data. | Operator | External service | [#45](https://github.com/spippoli/tart/issues/45) |

**At launch**

| # | Item | Who | Where | Basis |
|---|---|---|---|---|
| 15 | Get a clean `tart config check --database` run and a tested backup restore: a full restore drill on a clean machine. | Operator | CLI, host | [#45](https://github.com/spippoli/tart/issues/45), [#46](https://github.com/spippoli/tart/issues/46) |
| 16 | 🇮🇹 Notify AGCOM of the point of contact (`dsa@agcom.it`). ⚖️ | Operator | External | [#46](https://github.com/spippoli/tart/issues/46) |

**Ongoing**

| # | Item | Who | Where | Basis |
|---|---|---|---|---|
| 17 | 🇮🇹 File the yearly AGCOM contribution declaration, even when nothing is due. ⚖️ | Operator | External | [#46](https://github.com/spippoli/tart/issues/46) |
| 18 | Periodically review the Notice log and decision times. The recommended target is a decision within 7 days; it is guidance, not a configuration value. | Operator | Moderation area | [#46](https://github.com/spippoli/tart/issues/46) |
| 19 | Watch GitHub releases or their Atom feed; read each release's "Operator actions"; apply majors in order. | Operator | External | [#45](https://github.com/spippoli/tart/issues/45) |
| 20 | Repeat the full restore drill on a clean machine yearly. | Operator | Host | [#45](https://github.com/spippoli/tart/issues/45) |
| 21 | Publish a new version of the terms whenever they change. | Operator | Configuration | [#46](https://github.com/spippoli/tart/issues/46); [ADR 0012](../adr/0012-per-file-licence-with-rights-basis.md) |
| 22 | Switch `self_approval` to `false` once at least two Moderators are active. | Operator | Configuration | [#43](https://github.com/spippoli/tart/issues/43) |

**On event**

| # | Item | Who | Where | Basis |
|---|---|---|---|---|
| 23 | **After a Withdrawal or Purge**: replace any published Data dump, and publish only the latest one. | Operator | CLI, external | [#47](https://github.com/spippoli/tart/issues/47) |
| 24 | **A Notice a Moderator cannot judge**: escalate Moderator → Operator → legal counsel. Whoever decides for the Operator is granted the Moderator role and decides in the Moderation area; there is no other path. Meanwhile, "when in doubt, withdraw", because a Withdrawal is reversible by Reinstatement. | Moderator, Operator | Moderation area | [#46](https://github.com/spippoli/tart/issues/46), [#93](https://github.com/spippoli/tart/issues/93); [ADR 0013](../adr/0013-hide-not-delete-for-legal-removals.md) |
| 25 | **Authority order**: the Operator answers alone, with a Purge where the order requires one. | Operator | CLI, external | DSA Art. 9–10 |
| 26 | **Threat to life or safety**: inform the police. | Operator | External | DSA Art. 18 |
| 27 | **GDPR request**: access and portability are produced through the CLI; erasure is self-service account deletion or a Purge; the answer is due within one month. | Operator | CLI | GDPR Art. 12; [ADR 0013](../adr/0013-hide-not-delete-for-legal-removals.md) |
| 28 | **Data breach**: assess it; notify the supervisory authority (🇮🇹 Garante) within 72 hours where there is a risk, and the data subjects where the risk is high. | Operator | External | GDPR Art. 33–34 |

Drafting the terms of use, privacy notice, and other legal texts stays out of scope; the platform provides the processing inventory as a starting point, not a template.

### 10. Operator documentation

The platform repository ships, for Operators:
- the **runbook**: installation, backups (including the target rule and optional provider snapshots), restore, upgrades and rollback, host OS updates, monitoring setup, and `.env.example`;
- the **compliance guide** `docs/operator/compliance.md` ([Operator compliance checklist](#9-operator-compliance-checklist));
- the requirement to include the OpenStreetMap attribution when the basemap uses OSM data ([ADR 0016](../adr/0016-licence-policy-for-map-assets-and-data.md));
- the tile refresh suggestion: run `tart tiles update` about every six months and after any boundary change ([#38](https://github.com/spippoli/tart/issues/38)).

Operator documentation never calls TART "Open Source" ([ADR 0011](../adr/0011-provisional-software-license.md)).

## Testing Decisions

A good test drives a module through its external interface (a CLI command, an HTTP endpoint, a produced file) and asserts observable outcomes, never internal calls. Fixtures use fictional records, marked as fictional, with no claims about real artworks or artists.

- **Backup and restore (integration, against PostgreSQL and a local restic repository and rclone target)**: `tart backup run` then `tart backup restore` reproduces the database, media, and configuration; the database dump is taken before the media sync; a Purge and an account deletion made after an older dump are applied again when that older dump is restored; a media object deleted from storage appears under `deleted/YYYY-MM-DD` and leaves after 30 days (controlled clock).
- **Verify (integration)**: passes on a good backup; fails, and reports to Health, on a revision mismatch, on a count mismatch, and on a missing media key; always drops the temporary database.
- **Revision guard (integration)**: `api` and `worker` refuse to start when the database revision differs from the code's head.
- **Upgrade (integration, scripted against a Compose stack)**: the step order; an invalid configuration for the new image stops the upgrade before any service stops; a failing migration stops the command and prints rollback instructions; a pre-upgrade backup tag exists.
- **Health (unit and integration, controlled clock)**: each check at, below, and above its threshold; threshold overrides from the environment; `not_configured` is a warning; the public endpoint returns only `ok`/`fail` with the matching status; the details endpoint refuses requests without the token.
- **Alerting (integration)**: an Operator alert email when a check turns `fail`, no second one for the same check within a day; `BACKUP_PING_URL` receives a `GET` after backup and verify.
- **Logs (unit)**: log records produced during sign-in, Notice intake, and email sending contain the User id where relevant and no email address, sign-in code, token, or Notice content.
- **Jobs (integration)**: a job that exhausts its retries is `failed` and counted by the Email check when it is an email; `tart jobs failed` output shows no personal data in clear; `tart jobs retry` re-enqueues; completed jobs older than 30 days are deleted.
- **Data dump (integration)**: from a fixture archive with every record kind, withdrawn, merged, duplicate-retired, purged, pending, and redacted cases, and a deleted account: the dump validates against the JSON Schema; every public field is present; nothing in the exclusion rule is present; `redirects.ndjson` covers merged and retired ids; `locations.geojson` is valid GeoJSON; `LICENSE` matches the configured `licenses.data` for each allowed value; the README carries the `licenses.data_attribution` text, or the default when it is absent, (and its default); `--with-media` contains only public renditions without EXIF and a manifest entry per file.

## Acceptance criteria

**Releases and upgrades**
1. Tagged releases publish `api` and `frontend` images to GHCR with SemVer tags; no `latest` tag is referenced by the Compose file, which reads `TART_VERSION` from `.env`.
2. Every release's notes contain an "Operator actions" section.
3. The Instance makes no network request to check for updates.
4. `tart upgrade <version>` performs, in order: a backup tagged `pre-upgrade-<from>-<to>`, `config check --database` with the new image, image pull, stopping `api`, `worker`, and `frontend`, migrations in a one-shot container, restart, and a wait for a green health check; on any failure it stops and prints rollback instructions.
5. A configuration that fails the new image's check aborts the upgrade before any service is stopped.
6. `api` and `worker` refuse to start when the database revision differs from the code's Alembic head; no service runs migrations at startup.
7. The codebase contains no Alembic `downgrade` implementations.

**Backups and restore**
8. Without backup configuration, the backup check in `/api/health/details` is a `not_configured` warning and `/api/health` is not `fail` because of it.
9. With backups configured, a nightly job at the configured time dumps the database into restic, then syncs media through rclone `crypt`, and includes the configuration directory; PMTiles, overlays, Caddy state, and `.env` are not in the backup.
10. Objects deleted from storage are kept in the media backup under `deleted/YYYY-MM-DD` for 30 days, then removed, for both filesystem and S3 storage.
11. Database snapshots are kept 7 daily, 4 weekly, 6 monthly by default, overridable in the environment; `prune` and `restic check --read-data-subset` run weekly.
12. Every Purge and account deletion appends an Erasure log entry with kind, target id, and date, and no content.
13. After `tart backup restore` of any dump, every erasure in the Erasure log of the most recent dump is applied again.
14. `tart backup verify` runs weekly, restores into a temporary database, checks revision, per-kind counts, and a media sample, drops the temporary database, and raises an alert on failure.

**Monitoring**
15. `GET /api/health` returns only `ok` or `fail` with a matching HTTP status and no other information.
16. `GET /api/health/details` without the configured token is refused; with it, it lists each check of [Monitoring](#5-monitoring) with value and threshold, using the default thresholds unless the environment overrides them.
17. When a check turns `fail`, the `worker` emails `OPERATOR_ALERT_EMAIL`, at most once per check per day.
18. When `BACKUP_PING_URL` is set, it receives a `GET` at the end of each backup and each verify.
19. Application logs are structured JSON on stdout, rotated by the Compose file's `json-file` settings for about 14 days, and never contain email addresses, sign-in codes, tokens, or Notice content.
20. A job that exhausts its retries stays `failed`; `tart jobs failed` lists failed jobs without personal data in clear; `tart jobs retry <id|--all>` retries them; completed jobs are deleted after 30 days.

**Data dump**
21. `tart dump` writes a `.zip` to the data volume containing `manifest.json`, one NDJSON file per record kind, `redirects.ndjson`, `locations.geojson`, `LICENSE`, and `README`, and nothing is published or linked by the Instance.
22. The dump validates against the published, SemVer-versioned JSON Schema, and every field shown on public Archive record pages is present in it, except Revisions and User names.
23. The dump contains none of: Revisions, User names, Users, non-approved or retracted Submissions, the Submission log, Moderation notes, withdrawn or Purged content (including a withdrawn Artist's Attributions and Crew memberships), Notices, the legal action log, the Erasure log.
24. Creator credits appear as on public pages; anonymised credits stay anonymised.
25. Merged and duplicate-retired ids appear in `redirects.ndjson` with the surviving id and date, without their content.
26. Uncertain dates are exported as value plus precision; vocabulary values as stable keys with labels in every enabled UI language; geometries as GeoJSON.
27. `LICENSE` contains the configured Data licence's name, version, URL, and full text, with the ODbL notice when applicable; `README` is in the Content language and English and contains the attribution text, the statement that the Data licence covers neither the files nor the depicted Artworks, the non-binding request about later withdrawals, and "Powered by TART" with the version and no software licence grant.
28. `tart dump --with-media` additionally produces a media package of public renditions only (no originals, capped resolution, no EXIF) with a manifest giving each file's licence, Creator credit, and origin URL.

**Documentation and compliance**
29. The platform repository contains `docs/operator/compliance.md` with every item of the [Operator compliance checklist](#9-operator-compliance-checklist), grouped by phase, each with who acts, where it lives, and its basis, with the Italy annex marked 🇮🇹 and legal-review items marked ⚖️, opening with the public-control warning.
30. The runbook and `.env.example` cover backups, restore, upgrades, rollback, monitoring, and host updates.
31. No Operator documentation, dump README, or release note calls TART "Open Source".

**Accessibility and i18n**
32. This spec adds no user-facing page. The Operator alert email's strings come from the backend message catalogue under the missing-key check ([ADR 0008](../adr/0008-single-content-language-and-prefixed-ui-languages.md)); dates in emails use the Instance time zone.

## Instance configuration

The [Foundations](foundations.md#1-instance-configuration) spec owns `instance.toml` and the file layout; this spec reads the following.

| Setting | Key | Use here | Rome |
|---|---|---|---|
| Configuration shape version | `config_version` | Checked by `tart upgrade` with the new image; bumped only in majors | `1` |
| Data licence | `licenses.data` | Dump `LICENSE` and manifest | `CC-BY-SA-4.0` |
| Data attribution (optional, one string in the Content language) | `licenses.data_attribution` | Dump README attribution text; default: archive name and Operator name; the Instance URL and dump date always follow | Not decided |
| Operator name (required) | `operator.name` | Default attribution | Not decided |
| Archive name (Content language) | `identity.name` | Dump manifest, default attribution | Not decided ([Foundations open item 1](foundations.md#open-items)) |
| Content language | `languages.content` | Dump manifest and README language | `it` |
| Enabled UI languages | `languages.ui` | Vocabulary labels in the dump | `it`, `en` |
| Public image rendition cap | `media.public_rendition_max_px` | Resolution cap of the media package | Not decided |

**Environment** (infrastructure and secrets, [ADR 0009](../adr/0009-instance-configuration-as-validated-files.md)):

| Setting | Name | Rome |
|---|---|---|
| Platform version | `TART_VERSION` | Set per release |
| Backup repository, target credentials, encryption secrets | Not fixed | Hetzner Storage Box BX11 (1 TB) over SFTP, in a different location from the VPS, with Storage Box automatic snapshots (daily, kept 30 days) that the server's credentials cannot delete; outside the €20 ceiling, price to check at purchase |
| Backup schedule | Not fixed | Not decided |
| Retention overrides | Not fixed | Defaults (7/4/6) |
| Health details token | Not fixed | Secret |
| Health threshold overrides | Not fixed | Defaults |
| Operator alert address | `OPERATOR_ALERT_EMAIL` | Not decided |
| Dead-man's switch | `BACKUP_PING_URL` | Optional; not decided |

Rome turns backups on at launch.

**Platform constants, not configuration**: the backup order (database, then media); the 30-day `deleted/` window for media; weekly verify, `prune`, and `check`; at most one alert email per check per day; completed jobs deleted after 30 days; log retention of about 14 days; the SemVer policy.

## Out of Scope

- Point-in-time recovery and WAL archiving (RPO is 24 hours).
- Rewriting or selectively deleting backups for a Purge or account deletion.
- Alembic `downgrade` scripts; automatic PostgreSQL major upgrades.
- Zero-downtime upgrades (expand/contract migrations, blue-green deployment).
- `tart config migrate` or any automatic configuration migration.
- Update checks that contact the maintainer or any third party.
- Hosting, linking, or periodically producing Data dumps from the Instance.
- A dump importer and bulk import ([spec index](index.md#out-of-scope-for-the-mvp)).
- Revisions, User names, or originals in any public dump.
- A CLI command for the compliance checklist.
- Drafting the terms of use, privacy notice, record of processing, data processing agreements, trademark policy, or CLA.
- National annexes other than Italy.
- Full online-platform duties for publicly controlled Operators ([#46](https://github.com/spippoli/tart/issues/46)).
- Professional legal review.

## Further Notes

Not normative.

### Open items

The inputs leave these questions unsettled. Implementers must not fill them by assumption; each needs a decision (a resolution comment or an ADR) before the affected ticket is built.

**Rome values**
1. **Rome Operator.** Whether Rome's Operator is an individual, an existing association, or a new entity is not decided ([#46](https://github.com/spippoli/tart/issues/46)). It determines who acts as DSA provider and GDPR controller, and the "Operator" in the default `data_attribution`.
2. **Rome's operational values.** The Storage Box location, the backup schedule time, the Operator alert address, and whether a dead-man's switch is used are not decided ([#45](https://github.com/spippoli/tart/issues/45)).

**Backups and restore**
3. **Erasures after the last backup.** A Purge or account deletion made after the most recent nightly dump is not in any backed-up Erasure log; a restore after losing the database would bring that content back. Whether the runbook requires a backup right after each Purge (or `tart backup run` is triggered by it) is not decided.
4. **Scope of `tart backup restore`.** The decision describes restoring "the chosen dump" and replaying the Erasure log. Whether the command also restores media and the configuration directory, or those are manual runbook steps, is not decided; nor is how media erasures are replayed on restored objects.
5. **Verify sample size.** "A sample of media keys" is not quantified.
6. **Backup target as a processor.** Checklist item 5 names hosting, storage, and SMTP providers. Whether the backup target provider (Rome: a Hetzner Storage Box) and the external monitor need their own entry in the processing inventory or a data processing agreement, given that backups are encrypted and the monitor sees no personal data, is not decided. ⚖️
7. **Environment variable names.** Only `TART_VERSION`, `BACKUP_PING_URL`, and `OPERATOR_ALERT_EMAIL` are named. The names of the backup repository, secrets, schedule, retention overrides, health token, and threshold overrides are left to implementation and must be documented in `.env.example`.
8. **Changing storage adapter.** No procedure is decided for moving an existing Instance from filesystem to S3 storage (or back), nor whether `tart backup restore` can restore media into a different adapter.

**Upgrades**
9. **How `tart upgrade` reaches Docker.** The Operator CLI runs from the `api` image, but `tart upgrade` pulls images and stops and starts Compose services. Whether it runs as a host-side wrapper, with access to the Docker socket, or otherwise is not decided.
10. **CVE rebuilds.** Patch releases include "rebuilds for relevant base-image CVEs"; how the maintainer detects them and what counts as relevant is not decided.

**Monitoring**
11. **What drives the public status.** `/api/health` returns `ok`/`fail` and is the primary alerting channel, but the decision does not state explicitly whether every check (including disk, email failures, backup age, and verify age) turns it to `fail`, or only some.
12. **Language of the Operator alert email.** The Operator is not a User and has no preferred UI language; whether alerts use the Instance's default UI language is not decided.
13. **Log sizing.** "About 14 days" is a target; the `json-file` size and file count, and the mechanism that rotates IP addresses out of Caddy logs, are left to implementation.

**Data dump**
14. **Nested or separate files.** "One NDJSON file per record kind" covers the eight Archive record kinds; whether History events, Attributions, Crew memberships, and citations are nested in their records or exported as their own files is not decided.
15. **Operator name.** Answered by [Instance configuration keys and contacts](https://github.com/spippoli/tart/issues/85): `operator.name` is a required key; the default attribution is the archive name and the Operator name.
16. **README language.** The README is in the Content language and English. The Content language need not be a platform UI language with a message catalogue; how the Content-language README text is produced in that case is not decided.
17. **Shape of `data_attribution`.** Answered by [Instance configuration keys and contacts](https://github.com/spippoli/tart/issues/85): one string in the Content language; the platform appends the Instance URL and the dump date.
18. **Timeline names.** If public record pages name the Submitter of each History event ([Archive records open item 13](archive-records.md#open-items)), "every public field is present" and "no User names" conflict; the exclusion of User names is taken to win, but no decision says so.
19. **Coarsened positions.** If deliberate position obfuscation is decided ([Archive records open item 15](archive-records.md#open-items)), the dump must carry the public position only; no decision states it yet.
20. **Package naming and location.** The dump's file name and its path in the data volume are not decided.

**Checklist**
21. **Numbering.** The checklist above merges the 20 items of [#46](https://github.com/spippoli/tart/issues/46) with the items handed on by [#38](https://github.com/spippoli/tart/issues/38), [#43](https://github.com/spippoli/tart/issues/43), [#45](https://github.com/spippoli/tart/issues/45), and [#47](https://github.com/spippoli/tart/issues/47), so its numbers differ from #46's. Configuring backups and the Operator alert address are runbook steps, not checklist items, because #45 names only the drill, secrets, releases, host updates, and monitor as checklist items; whether the checklist should also list them is not decided.
22. **Operator acting on Notices.** Answered by [Operator as decider and Moderator self-review](https://github.com/spippoli/tart/issues/93): the Operator has no CLI command or UI for Notices; whoever decides for it is granted the Moderator role (checklist item 24).

### Notes

- [Backups, upgrades and monitoring](https://github.com/spippoli/tart/issues/45) already amended ADR 0004 and `foundations.md` (migrations run from `tart upgrade`) and answered [Rights and legal actions open item 20](rights-and-legal-actions.md#open-items) (backups); it partly answers item 18 (a Purge leaves a content-free Erasure log entry).
- It also answers [Notifications open item 14](notifications.md#open-items): a permanently failed email counts towards the Email health check, surfaces through the external monitor and the Operator alert email, and is listed by `tart jobs failed`. The Notifications spec is not edited by this PR.
- A User's GDPR export (Rights and legal actions) and the Data dump are distinct: the export is personal and private, the dump public and impersonal ([#8](https://github.com/spippoli/tart/issues/8)).
- The ODbL "offer the method to recreate" duty for overlays is met by the committed Overpass query in the configuration repository ([#38](https://github.com/spippoli/tart/issues/38)); tiles and overlays stay out of backups because they can be regenerated.
- [Tech stack decision](https://github.com/spippoli/tart/issues/13) flagged per-container memory as unmeasured; the `backup` service and `tart backup verify` (a temporary database in the `db` container) add to it, which matters for the 4 GB minimum.
