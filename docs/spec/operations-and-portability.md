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
| [0021](../adr/0021-release-automation-and-versioning.md) | One platform version; semantic-release on a manual workflow; images built before the tag; a breaking commit means Operator action and becomes the "Operator actions" notes; `0.x` until launch; exact-version multi-architecture images; production and development Compose files; commitlint and required checks |

**Glossary terms applied**: Instance, Operator, Instance configuration, Data licence, Data dump, Licensor, Content language, UI language, User, Moderator, Moderation note, Submission, Submission log, Archive record, Revision, Artwork, Artist, Location, Site, Area, Series, Source, Documentation item, Creator credit, Rights basis, History event, Claim, Attribution, Crew membership, Uncertain date, Merge, Duplicate retirement, Withdrawal, Redaction, Reinstatement, Purge, Erasure log, Notice.

**Decision tickets incorporated**: [Backups, upgrades and monitoring](https://github.com/spippoli/tart/issues/45), [Operator compliance checklist](https://github.com/spippoli/tart/issues/46), and [Public data dump](https://github.com/spippoli/tart/issues/47) (the core of this spec), and, for the parts that reach operations, [Tech stack decision](https://github.com/spippoli/tart/issues/13) (topology, sizing), [Licensing Decision Record (provisional)](https://github.com/spippoli/tart/issues/12) (CI licence allow-list, brand), [Licence policy for map assets and basemap data](https://github.com/spippoli/tart/issues/35) (CI allow-list, Operator documentation), [Basemap tile pipeline per Instance](https://github.com/spippoli/tart/issues/38) (tiles out of backups, tile cadence, external tile provider), and [Moderation roles and permissions](https://github.com/spippoli/tart/issues/43) (checklist items on `self_approval` and Moderation notes). Background research: [Research: archive data and contributor content licensing, GDPR](https://github.com/spippoli/tart/issues/8) (a public dump for preservation, distinct from portability), [Research: media pipeline and storage within budget](https://github.com/spippoli/tart/issues/10) (off-site media backups), [Research: Digital Services Act duties for an archive Instance](https://github.com/spippoli/tart/issues/19) (the checklist's legal basis), [Instance configuration keys and contacts](https://github.com/spippoli/tart/issues/85) (`operator.name`, the shape of `data_attribution`, `tart config check --database`), [Operator as decider and Moderator self-review](https://github.com/spippoli/tart/issues/93) (the Operator acts on Notices as a Moderator), [Redaction, current-value removal and Purge](https://github.com/spippoli/tart/issues/95) (Creator credit anonymisations in the Erasure log, Redactions of current values and the Data dump), [Public provenance, file rights and position coarsening](https://github.com/spippoli/tart/issues/91) (no User names anywhere public outside `/revisions`, Documentation item dates, public positions only), [Data dump layout and checklist numbering](https://github.com/spippoli/tart/issues/101) (separate files for linked entities, README language, package name and path, checklist numbering and the backup item), [Security constants and abuse protection](https://github.com/spippoli/tart/issues/84) (checklist items 30 and 31: abusive crawling, Suspension), [Notice handling details](https://github.com/spippoli/tart/issues/94) (checklist item 3: legal review of the platform's legal emails), [Rome Instance values](https://github.com/spippoli/tart/issues/86) (the Rome Operator, backup location and schedule, dead-man's switch), [Backup, restore and upgrade mechanics](https://github.com/spippoli/tart/issues/100) (Erasure log snapshots, restore scope, verify sample, storage change, host-side `tart` wrapper, CVE rebuilds, public health status, alert language, log retention, the backup target as a processor).

**Depends on**: every earlier feature spec, as listed above.

## Problem Statement

An Instance is usually run by a small volunteer group on one modest server. The archive's whole promise is that nothing is lost: a painted-over work stays a record, and so must the database that holds it survive a broken disk, a bad upgrade, a compromised server, or an Operator who walks away. At the same time, real erasures (a Purge, an account deletion) must not come back from a backup, and an old copy of personal data must not linger without limit. Upgrades must be safe for someone who is not a professional administrator: one command, a backup first, a clear way back. When something breaks (email stops, the `worker` dies, backups stop running) the Operator must hear about it before contributors do, without the platform phoning home or exposing personal data to a monitoring service.

Beyond the Instance itself, an archive meant for preservation must be able to outlive it: researchers and other projects need the public data in an open, documented format under the Instance's Data licence, without the dump leaking what the Instance has hidden or erased, and without implying that the Data licence covers photographs or the depicted works. Finally, running an Instance carries legal duties (DSA, GDPR, and in Italy AGCOM) that the software cannot discharge: the Operator needs a concrete checklist of what to do before launch, at launch, routinely, and when something happens.

## Solution

The platform ships generic, versioned images and a Compose stack. Backups are a platform-owned, opt-in `backup` service: a nightly `pg_dump` into an encrypted restic repository and an encrypted `rclone sync` of media to a target with a protection the server cannot delete, plus the configuration directory. A weekly automatic verify restores the latest dump into a temporary database and checks it. Backups are never rewritten; Purges and account deletions are recorded in the Erasure log, which every restore applies again. `tart upgrade <version>` takes a tagged backup, checks the configuration with the new image, and runs forward-only migrations while the services are stopped; rollback is a restore of that backup. A public health endpoint feeds an external monitor of the Operator's choice, a token-protected endpoint gives the details, and the `worker` emails the Operator when a check fails. Logs are structured, kept about 14 days, and never carry emails, codes, tokens, or Notice content.

The Operator produces a Data dump with `tart dump`: a zip of the current public archive (NDJSON per record kind and per linked entity, GeoJSON of Locations, a redirects table, a manifest, licence and README) that holds exactly what public pages show, validated against a published JSON Schema, with an optional package of public renditions. Publishing it is the Operator's choice. The Operator compliance checklist, grouped by phase and delivered as an Operator guide, lists the legal and operational duties the software cannot perform, with an Italy annex and legal-review flags.

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
- The CI checks (missing message keys, OpenAPI drift, the dependency licence allow-list of [ADR 0011](../adr/0011-provisional-software-license.md), the asset manifest of [ADR 0016](../adr/0016-licence-policy-for-map-assets-and-data.md)) are specified as acceptance criteria in [Foundations](foundations.md); this spec adds the release pipeline ([ADR 0021](../adr/0021-release-automation-and-versioning.md)).

### Modules

| Module | Interface (what callers see) | Lives in |
|---|---|---|
| Release pipeline | On a manual run, compute the next SemVer version from the commits, build and publish the generic `api` and `frontend` images to GHCR, then tag and publish the GitHub Release with its notes and Operator files | maintainer's CI |
| Backup | `tart backup run`, `tart backup verify`, `tart backup restore`, `tart backup erasures`; the nightly, weekly, and 15-minute schedule; reports last success times to Health | `backup` Compose service (profile), Operator CLI |
| Erasure log | Append a content-free entry (kind, target id, date); export all entries for the `erasures` snapshot; replay entries against a restored database and storage | backend (written by Purge, account deletion, and Creator credit anonymisation, read by restore) |
| Host wrapper | `tart <command>` on the host: passes Operator CLI commands to `docker compose run --rm api tart <command>`; implements `tart upgrade` and stops and starts services around `tart backup restore` | POSIX shell script shipped with each release, beside the Compose file |
| Upgrade | `tart upgrade <version>`: the ordered steps of [Upgrades](#4-upgrades) | host wrapper |
| Revision guard | At startup, compare the database's Alembic revision with the code's head; refuse to start on a mismatch | `api`, `worker` |
| Health | Run the checks; serve `GET /api/health` and the token-protected `GET /api/health/details` | backend (`api`) |
| Alerting | Email the Operator when a check turns `fail`, at most once per check per day; ping `BACKUP_PING_URL` after backup and verify | `worker`, `backup` |
| Jobs admin | `tart jobs failed`, `tart jobs retry <id\|--all>`; delete completed jobs after 30 days | Operator CLI, `worker` |
| Data dump | `tart dump [--with-media]`: write the dump package (and optionally the media package) to `dumps/` in the data volume | Operator CLI |
| Operator documentation | Runbook, `.env.example`, and the compliance guide `docs/operator/compliance.md` | platform repository |

Backup and Data dump read the database and storage through the same storage adapter as the application, so filesystem and S3 storage take the same path. The domain modules that perform Purge and account deletion depend only on the Erasure log's append interface.

### 1. Deployment and releases

- **Topology and sizing** are as in [Foundations](foundations.md#topology-and-stack) ([ADR 0004](../adr/0004-mvp-tech-stack.md)): a Docker Compose stack with `caddy`, `frontend`, `api`, `worker`, and `db`, plus the optional `backup` service as a Compose profile. Reference sizing is 4 GB RAM minimum, 8 GB recommended ([#13](https://github.com/spippoli/tart/issues/13)).
- **Images.** Generic prebuilt images on GHCR, published by the maintainer's CI: `ghcr.io/spippoli/tart-api` (which also runs `worker` and the Operator CLI) and `ghcr.io/spippoli/tart-frontend`, for `linux/amd64` and `linux/arm64`. Each is tagged with the exact version only (`0.3.0`) and carries the OCI labels `version`, `revision`, `source`, and `licenses`. No Instance-specific image is built.
- **Versioning.** SemVer on a single stable channel, one version for the whole platform ([ADR 0021](../adr/0021-release-automation-and-versioning.md)):
  - **patch**: fixes, and rebuilds for relevant base-image CVEs (below);
  - **minor**: features, with compatible migrations;
  - **major**: anything needing Operator action (a `config_version` bump, a manual step, a PostgreSQL major upgrade).

  The bump is computed from the Conventional Commits since the last release: `fix`, `perf`, and `build(deps)` give a patch, `feat` a minor, and a breaking commit (`!` or `BREAKING CHANGE:`) a major. A commit is breaking only when the Operator must act, and its footer states the action. Until the first Instance launches, versions stay at `0.x` and a breaking commit gives a minor; `1.0.0` is cut deliberately at launch.
- **Releasing.** The maintainer starts the release workflow on `main` by hand, by convention when an implementation wave is complete. It computes the next version, builds and pushes the images, and only then creates the `vX.Y.Z` tag and the GitHub Release, so an announced release always has its images.
- **Pinning.** `deploy/compose.yaml`, the production file, references the images with `${TART_VERSION:?}` read from `.env` and has no `build:`; development adds `deploy/compose.dev.yaml`. The `latest` tag is never used, and no floating tag (`0.3`, `0`) is published.
- **Release notes** are generated, and always open with an "Operator actions" section: the breaking footers, or a statement that only `tart upgrade <version>` is needed. Features and fixes follow. Minor releases can be skipped; majors are applied in order. Each release attaches the Operator files as separate assets: `compose.yaml`, `Caddyfile`, `.env.example` (named `env.example`, since GitHub asset names cannot start with a dot), and the `tart` host wrapper.
- **CVE rebuilds.** A weekly CI job scans the images of the latest release with Trivy (Apache-2.0, a CI tool that is not distributed); Renovate or Dependabot keeps the base-image digests current in the repository. A CVE is relevant when it is High or Critical, sits in a package present in the image (operating system, Python, or Node), and has a fix available. A relevant CVE triggers a patch release with the same code on the updated base (the digest update is committed as `build(deps): …`, and the maintainer starts the release outside the wave rhythm), whose "Operator actions" section says that only the upgrade is needed. Lower severities, and CVEs without a fix, wait for the next regular release. There is no response-time commitment: rebuilds are the maintainer's reasonable effort, and the Operator documentation says so.
- **Host wrapper.** The Operator CLI runs from the `api` image, but some commands must pull images and stop and start Compose services. Each release therefore ships a small POSIX shell script, `tart`, placed beside the Compose file on the host. It passes every Operator CLI command to `docker compose run --rm api tart <command>`, implements `tart upgrade` itself, and stops and restarts `api`, `worker`, and `frontend` around `tart backup restore`. The Docker socket is never mounted into any container. Host requirements are Docker with the Compose plugin, a POSIX shell, and systemd-journald (for [log retention](#5-monitoring)).
- **No phone-home.** The Instance never checks for updates. Operators watch GitHub releases or their Atom feed (checklist item 20).
- **Host.** Host OS security updates are the Operator's: the runbook explains them and the checklist lists them (item 14).

### 2. Backups

**Ownership.** Backups are platform-owned and opt-in: an optional `backup` Compose service (profile) and `tart backup run|verify|restore`, configured through the environment (repository, encryption secrets, schedule). Until backups are configured, `/api/health/details` reports the backup check as a `not_configured` **warning**, not a failure; turning them on is checklist item 12. Provider snapshots of the server are an optional extra, mentioned in the runbook. Rome turns backups on at launch.

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
- **Erasure log snapshot.** Every 15 minutes, `tart backup erasures` exports the whole Erasure log (content-free and small) into a restic snapshot tagged `erasures`, only when it has entries newer than the last such snapshot. An erasure made after the nightly dump therefore reaches the backup within 15 minutes ([ADR 0020](../adr/0020-backups-replay-erasures-and-forward-only-upgrades.md), amended). `erasures` snapshots follow the same retention as database snapshots.
- No WAL archiving or point-in-time recovery: the recovery point objective is 24 hours.

**Retention.**
- Database: restic `forget` keeps 7 daily, 4 weekly, and 6 monthly snapshots; a weekly `prune`; a weekly `restic check --read-data-subset`.
- The retention defaults can be overridden in the environment (infrastructure, not TOML, per [ADR 0009](../adr/0009-instance-configuration-as-validated-files.md)).
- Media: see the 30-day `deleted/` window above.

**Target.** The general runbook rule: the backup target must have a protection the server cannot delete (for example provider-side snapshots the server's credentials cannot remove), in a different location from the server. Single-provider risk is accepted for the MVP; an occasional second copy downloaded by the Operator is optional good practice. Rome's target is in [Instance configuration](#instance-configuration).

**Processors** ⚖️. Encryption is a security measure, not anonymisation: the Operator holds the keys, so the backups remain personal data. The backup target provider is therefore a processor (GDPR Art. 28). It has its own entry in the processing inventory and needs a data processing agreement (checklist item 5); for Rome, Hetzner's agreement covering the VPS and Object Storage also covers the Storage Box, which is named in it. The external monitor and the dead-man's switch receive only `ok`/`fail` or a generic `GET`, and no personal data of the Instance, so they are not processors and need neither an inventory entry nor an agreement; they stay named in the checklist (item 15). The Operator documentation warns that this changes if a monitor receives more than `/api/health`, for example logs. The Operator alert email carries no personal data and goes through the SMTP provider, which is already a processor.

**Secrets.** The restic password, the rclone crypt key, the target credentials, and `.env` are kept **off the server** as well: in the Operator's password manager and with a second person (checklist item 13).

### 3. Restore and the Erasure log

- Backups are never rewritten to honour a Purge or an account deletion ([ADR 0020](../adr/0020-backups-replay-erasures-and-forward-only-upgrades.md)).
- Every Purge, every account deletion, and every Creator credit anonymisation writes a content-free entry to the **Erasure log**: kind, target id, date. A Purge therefore leaves this tombstone; the rest of what a Purge leaves behind is specified by [Rights and legal actions](rights-and-legal-actions.md#8-purge).
- **`tart backup restore [--snapshot <id>] [--database-only]`** runs only while `api`, `worker`, and `frontend` are stopped (the host wrapper stops them; run inside the container with them running, it refuses and prints how to stop them). In order:
  1. **Database**: restore the chosen snapshot, by default the latest.
  2. **Media**: `rclone copy` from the backup copy into the storage currently configured, adding only missing objects. Keys are immutable and unique, so nothing is overwritten; `deleted/` is not restored.
  3. **Erasures**: apply again the union of the entries in the restored dump and in the latest `erasures` snapshot. Each entry reruns the same erasure as the Purge, account deletion, or Creator credit anonymisation that wrote it, on the database **and** in storage, so media copied back in step 2 are erased again.
  4. **Configuration**: extract the backed-up configuration directory to `restore/config-<YYYYMMDDTHHMMSSZ>/` in the data volume. It never replaces the live directory, which usually also lives in a git repository; the Operator compares and copies it by hand.

  `--database-only` skips steps 2 and 4, for a rollback after an upgrade, when media are intact. Because the `erasures` snapshot holds the whole log, restoring an older dump still applies every later erasure. Media erasures leave the backup within 30 days through `--backup-dir`.
- The processing inventory states that erased data may stay in encrypted backups for up to six months ([Processing inventory](#8-processing-inventory)).
- **Verify (automatic, weekly).** `tart backup verify` restores the latest dump into a temporary database in the `db` container and checks that:
  1. the Alembic revision equals the code's head;
  2. the record counts per kind equal those stored as snapshot metadata at backup time;
  3. a sample of media keys exists in the backup copy: 50 keys chosen at random among the objects the restored dump references (all of them when fewer), each present with the size recorded in the database, and one of them downloaded and decrypted through the `crypt` remote, to prove the rclone key still works. The sample size defaults to 50 and can be overridden in the environment. One error fails the verify, and the report lists the missing keys.

  It then drops the temporary database. A failure raises an alert ([Monitoring](#5-monitoring)).
- **Drill (manual).** A full restore on a clean machine before launch and then yearly (checklist items 16 and 21).
- **Handover.** A move to a new server, or a handover between Operators of the same Instance, uses backup and restore, not the Data dump ([#47](https://github.com/spippoli/tart/issues/47)).
- **Changing storage adapter.** There is no dedicated command. Because restore copies media into the storage currently configured, the runbook's "change of storage" procedure is: stop `api`, `worker`, and `frontend`; `tart backup run`; change the storage environment variables; a full `tart backup restore` of that snapshot; `tart backup verify`; restart the services. The old storage stays untouched as the rollback until the Operator deletes it by hand. Without backups configured, the runbook gives a manual `rclone copy` between the two storages instead, with the database unchanged, since object keys are the same in every adapter.

### 4. Upgrades

**`tart upgrade <version>`**, implemented by the [host wrapper](#1-deployment-and-releases), runs these steps in order:

1. a backup tagged `pre-upgrade-<from>-<to>`;
2. `tart config check --database` with the new image;
3. pull the images;
4. stop `api`, `worker`, and `frontend`;
5. run the Alembic migrations in a one-shot container;
6. start the services;
7. wait for the readiness checks (database, storage, `worker` heartbeat), read from `/api/health/details`. It does not wait for every check: an old verify must not hold back a successful upgrade.

The wrapper writes the new `TART_VERSION` to `.env` only after step 2 passes. If a step fails, the command stops, puts back the previous `TART_VERSION`, and prints the rollback instructions. Because the configuration is checked before anything stops, an incompatible configuration aborts the upgrade with the service still running.

- **No migrations at startup.** `api` and `worker` refuse to start when the database revision differs from the code's head, in the same fail-fast style as `config_version` ([ADR 0020](../adr/0020-backups-replay-erasures-and-forward-only-upgrades.md); [Foundations](foundations.md#topology-and-stack)).
- **Downtime.** Brief downtime is accepted: no expand/contract migrations and no blue-green deployment.
- **Rollback.** Migrations run forward only; there are no `downgrade` scripts. A rollback restores the `pre-upgrade` backup (including the Erasure log replay) and sets the previous `TART_VERSION`. Contributions made after the upgrade are lost, so a rollback only makes sense right after an upgrade.
- **PostgreSQL major upgrades** are a dump and restore described in a major release's notes, never automatic.
- **`config_version`** ([ADR 0009](../adr/0009-instance-configuration-as-validated-files.md), confirmed): bumped only by a change that breaks existing configuration directories (a renamed or removed key, or a new required key without a default), and therefore only in a major release. A new optional key with a default does not bump it. Migration is manual: the release notes give a before/after TOML example for each change. There is no `tart config migrate` in the MVP.

### 5. Monitoring

**Health endpoints.**
- `GET /api/health` is public and returns only `ok` or `fail`, with a matching HTTP status (200 or 503). It exposes no check names, values, or personal data. **Any** check in `fail` turns it to `fail`; a warning (today only the backup check's `not_configured`) does not. The cause is read on the details endpoint.
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
- The primary channel is an **external monitor** of the Operator's choice polling `/api/health` (for example Uptime Kuma on another machine, or a free hosted service). The monitor sees no personal data; it is named in the checklist (item 15).
- Optional dead-man's switch: `BACKUP_PING_URL` (environment) receives a generic `GET` at the end of each backup and each verify, compatible with Healthchecks.io or a self-hosted equivalent.
- As reinforcement, the `worker` emails `OPERATOR_ALERT_EMAIL` (environment) when a check turns `fail`, at most once per check per day. The Operator is not a User, so the email uses the Instance's default UI language (the first entry of `languages.ui`), from the backend message catalogue. The check key (`disk`, `backup`, `verify`…), its value, and its threshold also appear untranslated, exactly as in `/api/health/details`, so that the email can be matched against logs and the English documentation.
- No Docker healthcheck restarts a container on `/api/health`: restarting does not fix a full disk.

**Logs.**
- `api`, `worker`, and `frontend` write structured JSON to stdout.
- **Retention is bounded in time**: no application log line and no Caddy access log line older than **14 days** survives. Rotation by size alone does not meet this, because on a quiet Instance a size limit holds months of lines; Docker's `json-file` driver alone is therefore not enough, and no container can clean Docker's logs without the Docker socket. Every service of the Compose stack therefore logs through Docker's `journald` driver into the host's journal, which the Operator configures (checklist item 14) with `MaxFileSec=1day` and `MaxRetentionSec=13day`: each journal file spans at most a day and is deleted once its newest line is 13 days old, so no line outlives 14 days. `docker compose logs` keeps working. The host therefore needs systemd-journald.
- **Size cap** for disk safety: the journal is capped at 200 MB (`SystemMaxUse=200M`), the whole stack's share in place of a cap per service, which journald cannot set. Under load, retention can be shorter, which is acceptable.
- Application logs carry the User id and never emails, sign-in codes, tokens, or Notice content.
- Caddy access logs stay on (abuse and incident handling) with full IP addresses, which leave with the 14-day retention above; there is no masking at write time.
- Both kinds of log are listed in the processing inventory.

**Jobs.**
- Procrastinate retries with backoff. A job that exhausts its attempts stays `failed`; a failed email job counts towards the Email check.
- `tart jobs failed` lists failed jobs without personal data in clear; `tart jobs retry <id|--all>` retries one or all.
- Completed jobs are deleted after 30 days.

### 6. Data dump

A **Data dump** is an Operator-produced export of the current state of the public archive under the Instance's Data licence. It is distinct from the private, encrypted backup ([ADR 0020](../adr/0020-backups-replay-erasures-and-forward-only-upgrades.md)) and from a User's GDPR export ([Rights and legal actions](rights-and-legal-actions.md#10-data-exports)).

**Content.** The current state of every approved, public Archive record (Artwork, Artist, Location, Site, Area, Series, Source, Documentation item) with the full physical history: History events, Attributions, Crew memberships, citations, Uncertain dates with their precision, and the submitted and approved dates of History events and Documentation items, as their public pages show them. Location geometries are the public ones: the archive stores no other ([Public provenance, file rights and position coarsening](https://github.com/spippoli/tart/issues/91)).

**Exclusion rule.** The dump holds exactly what public pages show, and nothing else. In particular it excludes:
- **Revisions and User names** (Submitters and Moderators alike; no public page outside `/revisions` names a User, so the Timeline adds none): once published, a dump escapes later Redactions and account deletions, so the audit trail stays on the Instance's `/revisions` pages, where Withdrawal and Redaction still work;
- pending, draft, rejected, and retracted Submissions, the Submission log, and Moderation notes;
- withdrawn records and Documentation items, and a withdrawn Artist's Attributions and Crew memberships;
- current values hidden by a Redaction;
- Purged content;
- Users, Notices, the legal action log, and the Erasure log.

Creator credits appear as shown publicly, so anonymised ones stay anonymised.

**Redirects.** A `redirects` table maps merged and duplicate-retired ids to the surviving id, with the date, so that external references keep resolving ([ADR 0018](../adr/0018-merge-as-reconciling-multi-record-submission.md)). The content of retired records is not included.

**Media.**
- Documentation item metadata is always included: kind, file licence, Creator credit, Rights basis, third-party origin URL, and public rendition URL. Text Documentation items are included with their licence.
- `tart dump --with-media` also writes a separate media package of **public renditions only** (never originals; resolution-capped; no EXIF) with a per-file licence manifest listing each file's licence, Creator credit, and origin URL. The Operator decides whether to publish it.

**Format.** A `.zip` named `data-dump-<YYYYMMDDTHHMMSSZ>.zip` (generation time in UTC) containing:

| File | Content |
|---|---|
| `manifest.json` | Dump schema version, TART version, archive name, Content language, Data licence, generation time, counts per kind |
| One NDJSON file per record kind | The records of that kind: `artworks`, `artists`, `locations`, `sites`, `areas`, `series`, `sources`, `documentation_items` |
| `history_events.ndjson` | History events, each with its own id and the id of its Artwork |
| `attributions.ndjson` | Attributions, each with its own id, its Artwork and Artist ids, and its Alias |
| `crew_memberships.ndjson` | Crew memberships, each with its own id and the ids of the crew and the member |
| `citations.ndjson` | One row per citation: the citing subject (a Claim or a record, by kind and id) and the cited Source or Documentation item (by kind and id), for Claim citations and record-level citations alike |
| `redirects.ndjson` | Retired id → surviving id, with the date |
| `locations.geojson` | A FeatureCollection of Locations with their Artworks as properties, for GIS tools |
| `LICENSE` | See below |
| `README` | See below |

- Linked entities are their own files, never nested in their records: Attributions and Crew memberships join two records, and flat files load as tables ([#101](https://github.com/spippoli/tart/issues/101)).
- Stable ids; references by id; GeoJSON geometries; Uncertain dates as modelled (value plus precision).
- Vocabulary values are exported as stable keys with labels in the enabled UI languages.
- A **JSON Schema**, versioned with SemVer, is published with the platform. Every dump validates against it.

**Completeness and re-import.** The format is committed to being complete for public data, so that a future importer could rebuild the archive into a new Instance (with no Users and an initial import Revision). There is no importer in the MVP; bulk import stays out of scope.

**Licence and notices.** The package is under the Instance's Data licence.
- `LICENSE`: the licence name, version, official URL, and full legal text, generated from the configured `licenses.data`, including the ODbL notice when applicable.
- `README`, always in English, and also in the Content language when the platform has a message catalogue for it. Its fixed text comes from the platform catalogue, never from an Operator translation, so its legal statements are always reviewed text. When the Content language has no catalogue, the README is in English only and says that no translation is available; the attribution text is still quoted as is ([#101](https://github.com/spippoli/tart/issues/101)). It contains:
  - the attribution text: `licenses.data_attribution`, one string in the Content language quoted as is in both README languages, or by default the archive name and `operator.name`; the platform always follows it with the Instance URL and the dump date ([Instance configuration keys and contacts](https://github.com/spippoli/tart/issues/85)). It is a courtesy request when the licence is CC0;
  - a statement that the Data licence covers neither Documentation item files (each has its own licence in the manifest) nor the depicted Artworks (there is no freedom of panorama in Italy);
  - a **non-binding request** that reusers drop content withdrawn after the dump date and prefer the latest dump. It is a request, not a condition, because CC and ODbL licences forbid additional restrictions;
  - "Powered by TART" with the TART version, granting no software licence ([ADR 0011](../adr/0011-provisional-software-license.md)).

**Production and publication.** `tart dump` writes the package to `dumps/` in the data volume, a directory Caddy never serves, and prints its path; `--with-media` writes `media-<YYYYMMDDTHHMMSSZ>.zip` beside it with the same timestamp. The timestamp tells which dump is published, so that the right one is replaced. Old packages stay until the Operator deletes them; there is no automatic clean-up and no output option ([#101](https://github.com/spippoli/tart/issues/101)). Whether, where (for example Zenodo, the Internet Archive, or the Operator's own site), and how often to publish is the Operator's choice. There is no periodic dump job, and the Instance neither hosts nor links to dumps. After a Withdrawal or Purge, the Operator replaces any published dump and publishes only the latest one (checklist item 24).

### 7. Operator CLI additions

These join the [Foundations Operator CLI](foundations.md#5-operator-cli). On the host, every command is run through the [host wrapper](#1-deployment-and-releases):

| Command | Behaviour |
|---|---|
| `tart backup run` | Run a backup now (database dump, then media, then configuration directory) |
| `tart backup verify` | Restore the latest dump into a temporary database and check revision, counts, and a media sample |
| `tart backup restore [--snapshot <id>] [--database-only]` | With the services stopped: restore the database, copy missing media back, apply again the erasures of the dump and of the latest `erasures` snapshot, and extract the configuration to `restore/` ([Restore](#3-restore-and-the-erasure-log)) |
| `tart backup erasures` | Export the Erasure log to a restic snapshot tagged `erasures` when it has new entries; run every 15 minutes by the `backup` service |
| `tart upgrade <version>` | The seven steps of [Upgrades](#4-upgrades), run by the host wrapper |
| `tart jobs failed` | List failed jobs without personal data in clear |
| `tart jobs retry <id\|--all>` | Retry one or all failed jobs |
| `tart dump [--with-media]` | Write the Data dump, and optionally the media package, to `dumps/` in the data volume, and print each path |

### 8. Processing inventory

The platform's processing inventory is specified in [Rights and legal actions](rights-and-legal-actions.md#11-processing-inventory). This spec adds these entries:

| Category | Purpose | Retention |
|---|---|---|
| Application logs (User id; never emails, codes, tokens, or Notice content) | Operation, incident handling | Up to 14 days |
| Caddy access logs (IP addresses) | Abuse and incident handling | Up to 14 days |
| Backups (encrypted copies of the database, media, and configuration), held by the backup target provider as processor | Recovery | Up to six months; erased data may remain until the snapshot holding it expires, and is erased again on restore |

The external monitor and the dead-man's switch receive no personal data and are not listed ([Backups](#2-backups)).

### 9. Operator compliance checklist

**Form.** The checklist is this section. Implementation delivers it as an Operator guide, `docs/operator/compliance.md`, in the platform repository, written in English like all project documentation. There is no CLI command for it: what software can verify, `tart config check` already checks (terms, privacy policy, DSA contact, map attribution); the remaining items happen outside the software.

**Structure.** The numbers below are the only canonical ones: the Operator guide uses them as they are, and a change to the checklist renumbers it and updates every cross-reference ([#101](https://github.com/spippoli/tart/issues/101)). Items are grouped by phase: before launch, at launch, ongoing, on event. Each item states who acts (Operator or Moderator), where it lives (configuration, CLI, host, or an external document), and its legal or ADR basis. The core covers the EU; an **Italy annex** (🇮🇹) is the only national annex in the MVP. Items marked ⚖️ need legal review.

**Opening warning.** An Operator that is 25% or more publicly controlled (a city, a public museum, or a university) is never an SME and may owe the full online-platform duties. The MVP does not support them, so such an Operator must get legal advice before launch. ⚖️

**Before launch**

| # | Item | Who | Where | Basis |
|---|---|---|---|---|
| 1 | Read the public-control warning above. ⚖️ | Operator | — | [#46](https://github.com/spippoli/tart/issues/46) |
| 2 | Name the Operator: the legal or natural person acting as DSA provider and GDPR controller. A legal entity (for example an association) is recommended over an individual, because approved content may fall outside the DSA Art. 6 hosting exemption. | Operator | External document | DSA, GDPR; [#46](https://github.com/spippoli/tart/issues/46) |
| 3 | Write terms of use that describe moderation, the Notice reasons list, and redress by email reply or in court. Have the platform's legal email texts (statements of reasons, Notice decisions, the redress block) reviewed together with the terms. ⚖️ | Operator | Configuration (Markdown) | DSA Art. 14; [ADR 0013](../adr/0013-hide-not-delete-for-legal-removals.md) |
| 4 | Write the privacy notice and the record of processing activities, starting from the platform's processing inventory. Name every external recipient, including an external tile provider when the map style uses one. | Operator | Configuration (Markdown) and external document | GDPR Art. 13, 30; [#38](https://github.com/spippoli/tart/issues/38) |
| 5 | Sign data processing agreements with the hosting, storage, backup target, and SMTP providers. ⚖️ | Operator | External document | GDPR Art. 28 |
| 6 | Set up points of contact for authorities and for users, with their languages (`contacts.dsa`, `contacts.dsa_languages`), plus a privacy contact (`contacts.privacy`); replies to legal emails reach `contacts.dsa`. | Operator | Configuration | DSA Art. 11–12 |
| 7 | Choose `licenses.data`, `licenses.files` (default first), `community.min_age` (🇮🇹 14), and the map attribution list; when the basemap uses OpenStreetMap data, include `© OpenStreetMap` → `https://www.openstreetmap.org/copyright`. | Operator | Configuration | [ADR 0009](../adr/0009-instance-configuration-as-validated-files.md), [0012](../adr/0012-per-file-licence-with-rights-basis.md), [0016](../adr/0016-licence-policy-for-map-assets-and-data.md) |
| 8 | Grant at least one Moderator through the CLI and name who handles escalation. | Operator | CLI | [#43](https://github.com/spippoli/tart/issues/43), [#46](https://github.com/spippoli/tart/issues/46) |
| 9 | Tell Moderators that Moderation notes are personal data subject to access requests, so they must stay factual. | Operator, Moderators | Operator guide | GDPR Art. 15; [#43](https://github.com/spippoli/tart/issues/43) |
| 10 | Read the Art. 6 position: approved records may not be shielded by the hosting exemption. ⚖️ | Operator | — | DSA Art. 6; [#19](https://github.com/spippoli/tart/issues/19) |
| 11 | Brand: "Powered by TART" is optional; never call TART "Open Source"; the archive's name stays distinct from TART. | Operator | Configuration, public texts | [ADR 0011](../adr/0011-provisional-software-license.md) |
| 12 | Turn on backups to a target with a protection the server cannot delete, in a different location from the server, and set `OPERATOR_ALERT_EMAIL`. | Operator | Environment, external service | [#45](https://github.com/spippoli/tart/issues/45), [#101](https://github.com/spippoli/tart/issues/101) |
| 13 | Keep the backup secrets (restic password, rclone crypt key, target credentials) and `.env` off the server: in a password manager and with a second person. | Operator | External | [#45](https://github.com/spippoli/tart/issues/45) |
| 14 | Enable host OS security updates, and set the host journal for the Instance's logs: `MaxFileSec=1day`, `MaxRetentionSec=13day`, `SystemMaxUse=200M` ([Monitoring](#5-monitoring)). | Operator | Host | [#45](https://github.com/spippoli/tart/issues/45) |
| 15 | Set up an external monitor polling `/api/health`; it sees no personal data, so it is not a processor as long as it receives nothing more. | Operator | External service | [#45](https://github.com/spippoli/tart/issues/45) |

**At launch**

| # | Item | Who | Where | Basis |
|---|---|---|---|---|
| 16 | Get a clean `tart config check --database` run and a tested backup restore: a full restore drill on a clean machine. | Operator | CLI, host | [#45](https://github.com/spippoli/tart/issues/45), [#46](https://github.com/spippoli/tart/issues/46) |
| 17 | 🇮🇹 Notify AGCOM of the point of contact (`dsa@agcom.it`). ⚖️ | Operator | External | [#46](https://github.com/spippoli/tart/issues/46) |

**Ongoing**

| # | Item | Who | Where | Basis |
|---|---|---|---|---|
| 18 | 🇮🇹 File the yearly AGCOM contribution declaration, even when nothing is due. ⚖️ | Operator | External | [#46](https://github.com/spippoli/tart/issues/46) |
| 19 | Periodically review the Notice log and decision times. The recommended target is a decision within 7 days; it is guidance, not a configuration value. | Operator | Moderation area | [#46](https://github.com/spippoli/tart/issues/46) |
| 20 | Watch GitHub releases or their Atom feed; read each release's "Operator actions"; apply majors in order. | Operator | External | [#45](https://github.com/spippoli/tart/issues/45) |
| 21 | Repeat the full restore drill on a clean machine yearly. | Operator | Host | [#45](https://github.com/spippoli/tart/issues/45) |
| 22 | Publish a new version of the terms whenever they change. | Operator | Configuration | [#46](https://github.com/spippoli/tart/issues/46); [ADR 0012](../adr/0012-per-file-licence-with-rights-basis.md) |
| 23 | Switch `self_approval` to `false` once at least two Moderators are active. | Operator | Configuration | [#43](https://github.com/spippoli/tart/issues/43) |

**On event**

| # | Item | Who | Where | Basis |
|---|---|---|---|---|
| 24 | **After a Withdrawal, a Redaction of a current value, or a Purge**: replace any published Data dump, and publish only the latest one. | Operator | CLI, external | [#47](https://github.com/spippoli/tart/issues/47) |
| 25 | **A Notice a Moderator cannot judge**: escalate Moderator → Operator → legal counsel. Whoever decides for the Operator is granted the Moderator role and decides in the Moderation area; there is no other path. Meanwhile, "when in doubt, withdraw", because a Withdrawal is reversible by Reinstatement. | Moderator, Operator | Moderation area | [#46](https://github.com/spippoli/tart/issues/46), [#93](https://github.com/spippoli/tart/issues/93); [ADR 0013](../adr/0013-hide-not-delete-for-legal-removals.md) |
| 26 | **Authority order**: the Operator answers alone, with a Purge where the order requires one (`tart purge <legal-action-id> --ground authority-order`); the Purge's statement of reasons informs the affected Submitters (Art. 9(5)). | Operator | CLI, external | DSA Art. 9–10; [#95](https://github.com/spippoli/tart/issues/95) |
| 27 | **Threat to life or safety**: inform the police. | Operator | External | DSA Art. 18 |
| 28 | **GDPR request**: access and portability are produced through the CLI; erasure is self-service account deletion or a Purge; the answer is due within one month. | Operator | CLI | GDPR Art. 12; [ADR 0013](../adr/0013-hide-not-delete-for-legal-removals.md) |
| 29 | **Data breach**: assess it; notify the supervisory authority (🇮🇹 Garante) within 72 hours where there is a risk, and the data subjects where the risk is high. | Operator | External | GDPR Art. 33–34 |
| 30 | **Abusive crawling** that slows the Instance: add a rate limit or a proxy in front (a Caddy rate-limit plugin in a custom image, or an external service), keeping Caddy as the source of the client IP; the platform limits no public reads. | Operator | Host | [Security constants and abuse protection](https://github.com/spippoli/tart/issues/84) |
| 31 | **A User who keeps abusing the Instance** (on a Moderator's request or the Operator's own finding): suspend with `tart users suspend <email> --reason <text>`, answer a contest sent to the DSA contact, and lift it with `tart users unsuspend <email>` when it no longer holds. | Operator | CLI | [Security constants and abuse protection](https://github.com/spippoli/tart/issues/84) |

Drafting the terms of use, privacy notice, and other legal texts stays out of scope; the platform provides the processing inventory as a starting point, not a template.

### 10. Operator documentation

The platform repository ships, for Operators:
- the **runbook**: installation (including the host wrapper), backups (including the target rule and optional provider snapshots), restore, the change of storage procedure, upgrades and rollback, host OS updates and the journal settings, monitoring setup, and `.env.example`;
- the **compliance guide** `docs/operator/compliance.md` ([Operator compliance checklist](#9-operator-compliance-checklist));
- the requirement to include the OpenStreetMap attribution when the basemap uses OSM data ([ADR 0016](../adr/0016-licence-policy-for-map-assets-and-data.md));
- the tile refresh suggestion: run `tart tiles update` about every six months and after any boundary change ([#38](https://github.com/spippoli/tart/issues/38)).

Operator documentation never calls TART "Open Source" ([ADR 0011](../adr/0011-provisional-software-license.md)).

## Testing Decisions

A good test drives a module through its external interface (a CLI command, an HTTP endpoint, a produced file) and asserts observable outcomes, never internal calls. Fixtures use fictional records, marked as fictional, with no claims about real artworks or artists.

- **Backup and restore (integration, against PostgreSQL and a local restic repository and rclone target)**: `tart backup run` then `tart backup restore` reproduces the database, media, and configuration; the database dump is taken before the media sync; a Purge and an account deletion made after an older dump are applied again when that older dump is restored; a Purge made after the latest nightly dump and captured by an `erasures` snapshot is applied again after a restore of that dump, including on media copied back; restore refuses to run while `api` is up; the configuration is extracted to `restore/` and the live directory is unchanged; `--database-only` touches neither media nor configuration; a restore into a different storage adapter (filesystem to S3) yields the same objects; a media object deleted from storage appears under `deleted/YYYY-MM-DD` and leaves after 30 days (controlled clock).
- **Verify (integration)**: passes on a good backup; fails, and reports to Health, on a revision mismatch, on a count mismatch, on a missing media key, on a size mismatch, and on a wrong crypt key; always drops the temporary database.
- **Revision guard (integration)**: `api` and `worker` refuse to start when the database revision differs from the code's head.
- **Upgrade (integration, scripted against a Compose stack)**: the step order; an invalid configuration for the new image stops the upgrade before any service stops; a failing migration stops the command, puts back the previous `TART_VERSION`, and prints rollback instructions; a pre-upgrade backup tag exists; the wait ends on the readiness checks even when the verify check is `fail`; no container mounts the Docker socket.
- **Health (unit and integration, controlled clock)**: each check at, below, and above its threshold; threshold overrides from the environment; `not_configured` is a warning; the public endpoint returns only `ok`/`fail` with the matching status, `fail` for any failing check and `ok` with only a warning; the details endpoint refuses requests without the token.
- **Alerting (integration)**: an Operator alert email when a check turns `fail`, no second one for the same check within a day; `BACKUP_PING_URL` receives a `GET` after backup and verify.
- **Logs (unit)**: log records produced during sign-in, Notice intake, and email sending contain the User id where relevant and no email address, sign-in code, token, or Notice content.
- **Log retention (static, over the shipped files)**: every service of the production Compose file logs through the `journald` driver, Caddy's access log is on, and the journal settings shipped with the Operator files are `MaxFileSec=1day`, `MaxRetentionSec=13day`, and `SystemMaxUse=200M`. The journal's own time-based deletion is systemd's, not exercised by the platform's tests.
- **Jobs (integration)**: a job that exhausts its retries is `failed` and counted by the Email check when it is an email; `tart jobs failed` output shows no personal data in clear; `tart jobs retry` re-enqueues; completed jobs older than 30 days are deleted.
- **Release pipeline (scripted, against throwaway Git repositories)**: the semantic-release configuration in dry-run mode over fixture commit histories gives the expected next version for each bump rule, including `0.x` and `build(deps)`; the notes template renders "Operator actions" with and without breaking footers; commitlint rejects an invalid message and accepts each allowed type. How the whole workflow is exercised before the first real release (a fork, or a test tag prefix) is left to implementation.
- **Data dump (integration)**: from a fixture archive with every record kind, withdrawn, merged, duplicate-retired, purged, pending, and redacted cases, and a deleted account: the dump validates against the JSON Schema; every public field is present; nothing in the exclusion rule is present; `redirects.ndjson` covers merged and retired ids; History events, Attributions, Crew memberships, and citations are in their own files, referenced by id; the README is in English and in the Content language, or in English only with the no-translation note when a fixture Content language has no catalogue; the package lands under `dumps/` with the timestamped name, and `/dumps/` is not served; `locations.geojson` is valid GeoJSON; `LICENSE` matches the configured `licenses.data` for each allowed value; the README carries the `licenses.data_attribution` text, or the default when it is absent, (and its default); `--with-media` contains only public renditions without EXIF and a manifest entry per file.

## Acceptance criteria

**Releases and upgrades**
1. A release publishes `tart-api` and `tart-frontend` images to GHCR for `linux/amd64` and `linux/arm64`, tagged with the exact SemVer version only; no `latest` tag is referenced by the production Compose file, which reads `TART_VERSION` from `.env`.
2. Every release's notes open with an "Operator actions" section, listing each breaking commit's footer, or stating that only the upgrade is needed when there is none.
3. The Instance makes no network request to check for updates.
4. `tart upgrade <version>`, run by the host wrapper, performs, in order: a backup tagged `pre-upgrade-<from>-<to>`, `config check --database` with the new image, image pull, stopping `api`, `worker`, and `frontend`, migrations in a one-shot container, restart, and a wait for the readiness checks (database, storage, `worker` heartbeat); it writes the new `TART_VERSION` only after the configuration check; on any failure it stops, puts back the previous `TART_VERSION`, and prints rollback instructions. No container mounts the Docker socket.
5. A configuration that fails the new image's check aborts the upgrade before any service is stopped.
6. `api` and `worker` refuse to start when the database revision differs from the code's Alembic head; no service runs migrations at startup.
7. The codebase contains no Alembic `downgrade` implementations.

**Backups and restore**
8. Without backup configuration, the backup check in `/api/health/details` is a `not_configured` warning and `/api/health` is not `fail` because of it.
9. With backups configured, a nightly job at the configured time dumps the database into restic, then syncs media through rclone `crypt`, and includes the configuration directory; PMTiles, overlays, Caddy state, and `.env` are not in the backup.
10. Objects deleted from storage are kept in the media backup under `deleted/YYYY-MM-DD` for 30 days, then removed, for both filesystem and S3 storage.
11. Database snapshots are kept 7 daily, 4 weekly, 6 monthly by default, overridable in the environment; `prune` and `restic check --read-data-subset` run weekly.
12. Every Purge, account deletion, and Creator credit anonymisation appends an Erasure log entry with kind, target id, and date, and no content.
13. Every 15 minutes, when the Erasure log has new entries, it is exported to a restic snapshot tagged `erasures`. `tart backup restore` refuses to run while `api`, `worker`, or `frontend` is up; it restores the database, copies missing media back into the configured storage, applies again every erasure in the restored dump and in the latest `erasures` snapshot on the database and in storage, and extracts the configuration to `restore/` without replacing the live directory; `--database-only` skips media and configuration.
14. `tart backup verify` runs weekly, restores into a temporary database, checks revision, per-kind counts, and a media sample (50 random referenced keys by default, each with its recorded size, and one decrypted download), drops the temporary database, and raises an alert on failure.

**Monitoring**
15. `GET /api/health` returns only `ok` or `fail` with a matching HTTP status and no other information; it is `fail` whenever any check is `fail`, and a warning does not change it.
16. `GET /api/health/details` without the configured token is refused; with it, it lists each check of [Monitoring](#5-monitoring) with value and threshold, using the default thresholds unless the environment overrides them.
17. When a check turns `fail`, the `worker` emails `OPERATOR_ALERT_EMAIL`, at most once per check per day, in the Instance's default UI language, with the check key, value, and threshold untranslated.
18. When `BACKUP_PING_URL` is set, it receives a `GET` at the end of each backup and each verify.
19. Application logs are structured JSON on stdout and never contain email addresses, sign-in codes, tokens, or Notice content. Every service logs through Docker's `journald` driver, Caddy's access log is on, and the documented journal settings keep no line older than 14 days and at most 200 MB.
20. A job that exhausts its retries stays `failed`; `tart jobs failed` lists failed jobs without personal data in clear; `tart jobs retry <id|--all>` retries them; completed jobs are deleted after 30 days.

**Data dump**
21. `tart dump` writes `dumps/data-dump-<YYYYMMDDTHHMMSSZ>.zip` to the data volume, which Caddy does not serve, and prints its path; the zip contains `manifest.json`, one NDJSON file per record kind, `history_events.ndjson`, `attributions.ndjson`, `crew_memberships.ndjson`, `citations.ndjson`, `redirects.ndjson`, `locations.geojson`, `LICENSE`, and `README`, and nothing is published or linked by the Instance.
22. The dump validates against the published, SemVer-versioned JSON Schema, and every field shown on public Archive record pages is present in it, except Revisions and User names.
23. The dump contains none of: Revisions, User names, Users, non-approved or retracted Submissions, the Submission log, Moderation notes, withdrawn or Purged content (including a withdrawn Artist's Attributions and Crew memberships), Notices, the legal action log, the Erasure log.
24. Creator credits appear as on public pages; anonymised credits stay anonymised.
25. Merged and duplicate-retired ids appear in `redirects.ndjson` with the surviving id and date, without their content.
26. Uncertain dates are exported as value plus precision; vocabulary values as stable keys with labels in every enabled UI language; geometries as GeoJSON.
27. `LICENSE` contains the configured Data licence's name, version, URL, and full text, with the ODbL notice when applicable; `README` is in English, and also in the Content language when the platform has a catalogue for it (otherwise it says no translation is available), and contains the attribution text, the statement that the Data licence covers neither the files nor the depicted Artworks, the non-binding request about later withdrawals, and "Powered by TART" with the version and no software licence grant.
28. `tart dump --with-media` additionally produces `dumps/media-<YYYYMMDDTHHMMSSZ>.zip`, with the dump's timestamp: a media package of public renditions only (no originals, capped resolution, no EXIF) with a manifest giving each file's licence, Creator credit, and origin URL.

**Documentation and compliance**
29. The platform repository contains `docs/operator/compliance.md` with every item of the [Operator compliance checklist](#9-operator-compliance-checklist), grouped by phase, each with who acts, where it lives, and its basis, with the Italy annex marked 🇮🇹 and legal-review items marked ⚖️, opening with the public-control warning.
30. The runbook and `.env.example` cover the host wrapper, backups, restore, the change of storage procedure, upgrades, rollback, monitoring, and host updates; the release notes and Operator documentation state that CVE rebuilds carry no response-time commitment.
31. No Operator documentation, dump README, or release note calls TART "Open Source".

**Accessibility and i18n**
32. This spec adds no user-facing page. The Operator alert email's strings come from the backend message catalogue under the missing-key check ([ADR 0008](../adr/0008-single-content-language-and-prefixed-ui-languages.md)); dates in emails use the Instance time zone.

**Release pipeline** ([ADR 0021](../adr/0021-release-automation-and-versioning.md))
33. The release version is computed from the commits since the last tag: `fix`, `perf`, or `build(deps)` gives a patch, `feat` a minor, a breaking commit a major; while the major is `0`, a breaking commit gives a minor.
34. The images are pushed before the tag and the GitHub Release are created; when the image build fails, no tag and no release exist.
35. The released images carry the version in both project files and in the `version` OCI label; the repository's project files are unchanged and `main` receives no commit from the release.
36. Each GitHub Release attaches `compose.yaml`, `Caddyfile`, and `.env.example` (as `env.example`) as separate assets.
37. A pull request with a commit whose message is not a valid Conventional Commit fails the `commitlint` check, and the `main` ruleset requires the `backend`, `frontend`, `images`, and `commitlint` checks.

## Instance configuration

The [Foundations](foundations.md#1-instance-configuration) spec owns `instance.toml` and the file layout; this spec reads the following.

| Setting | Key | Use here | Rome |
|---|---|---|---|
| Configuration shape version | `config_version` | Checked by `tart upgrade` with the new image; bumped only in majors | `1` |
| Data licence | `licenses.data` | Dump `LICENSE` and manifest | `CC-BY-SA-4.0` |
| Data attribution (optional, one string in the Content language) | `licenses.data_attribution` | Dump README attribution text; default: archive name and Operator name; the Instance URL and dump date always follow | Not set: the default applies |
| Operator name (required) | `operator.name` | Default attribution | Launch value: the legal name of Rome's association ([Foundations](foundations.md#romes-launch-values)) |
| Archive name (Content language) | `identity.name` | Dump manifest, default attribution | "Archivio dell'arte urbana di Roma" |
| Content language | `languages.content` | Dump manifest and README language | `it` |
| Enabled UI languages | `languages.ui` | Vocabulary labels in the dump | `it`, `en` |
| Public image rendition cap | `media.public_rendition_max_px` | Resolution cap of the media package | `2048` |

**Environment** (infrastructure and secrets, [ADR 0009](../adr/0009-instance-configuration-as-validated-files.md)):

| Setting | Name | Rome |
|---|---|---|
| Platform version | `TART_VERSION` | Set per release |
| Backup repository, target credentials, encryption secrets | Not fixed | Hetzner Storage Box BX11 (1 TB) over SFTP in Helsinki (`HEL1`), while the VPS and Object Storage are in Nuremberg (`nbg1`), so another country from the server; with Storage Box automatic snapshots (daily, kept 30 days) that the server's credentials cannot delete; outside the €20 ceiling, price to check at purchase |
| Backup schedule | Not fixed | Nightly backup at 03:30 Europe/Rome, after the 02:00–03:00 window that daylight-saving changes skip or repeat; weekly verify on Sundays at 05:00 |
| Retention overrides | Not fixed | Defaults (7/4/6) |
| Verify sample size | Not fixed | Default (50) |
| Health details token | Not fixed | Secret |
| Health threshold overrides | Not fixed | Defaults |
| Operator alert address | `OPERATOR_ALERT_EMAIL` | Launch value: a role address read by at least two people, not public ([Foundations](foundations.md#romes-launch-values)) |
| Dead-man's switch | `BACKUP_PING_URL` | Used: a Healthchecks.io check on the free plan, because the alert email cannot fire when the server itself is down; the URL is a launch value |

Rome turns backups on at launch.

**Platform constants, not configuration**: the backup order (database, then media); the 30-day `deleted/` window for media; the 15-minute `erasures` snapshot; weekly verify, `prune`, and `check`; any failing check turns `/api/health` to `fail`; at most one alert email per check per day, in the default UI language; completed jobs deleted after 30 days; log retention of at most 14 days and a 200 MB journal; the SemVer policy and the CVE relevance rule (High or Critical, with a fix).

## Out of Scope

- Point-in-time recovery and WAL archiving (RPO is 24 hours).
- Rewriting or selectively deleting backups for a Purge or account deletion.
- Alembic `downgrade` scripts; automatic PostgreSQL major upgrades.
- Zero-downtime upgrades (expand/contract migrations, blue-green deployment).
- `tart config migrate` or any automatic configuration migration.
- A `tart storage migrate` command: changing storage adapter is a runbook procedure built on backup and restore.
- Mounting the Docker socket into any container.
- A response-time commitment for CVE rebuilds.
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
1. **Rome Operator.** Answered by [Rome Instance values](https://github.com/spippoli/tart/issues/86): an association, existing or newly founded, not an individual; which one is a launch value, and a lawyer reviews its legal form and statute ⚖️ ([Foundations](foundations.md#romes-launch-values)).
2. **Rome's operational values.** Answered by [Rome Instance values](https://github.com/spippoli/tart/issues/86): see [Instance configuration](#instance-configuration). Whether Healthchecks.io belongs in the processing inventory stays with open item 6.

**Backups and restore**
3. **Erasures after the last backup.** Answered by [Backup, restore and upgrade mechanics](https://github.com/spippoli/tart/issues/100): every 15 minutes, `tart backup erasures` exports the Erasure log to an `erasures` restic snapshot, and restore applies the union of the dump's entries and that snapshot's ([Schedule](#2-backups), [Restore](#3-restore-and-the-erasure-log)).
4. **Scope of `tart backup restore`.** Answered by [Backup, restore and upgrade mechanics](https://github.com/spippoli/tart/issues/100): database, then missing media copied back, then erasures applied again on the database and in storage, then the configuration extracted to `restore/` without replacing the live one; `--database-only` for rollbacks ([Restore](#3-restore-and-the-erasure-log)).
5. **Verify sample size.** Answered by [Backup, restore and upgrade mechanics](https://github.com/spippoli/tart/issues/100): 50 random referenced keys by default, with size checked, and one decrypted download.
6. **Backup target as a processor.** Answered by [Backup, restore and upgrade mechanics](https://github.com/spippoli/tart/issues/100): the backup target provider is a processor, with an inventory entry and a data processing agreement (checklist item 5); the external monitor and the dead-man's switch are not ([Backups](#2-backups)). ⚖️
7. **Environment variable names.** Only `TART_VERSION`, `BACKUP_PING_URL`, and `OPERATOR_ALERT_EMAIL` are named. The names of the backup repository, secrets, schedule, retention overrides, verify sample size, health token, and threshold overrides are left to implementation and must be documented in `.env.example`. [Backup, restore and upgrade mechanics](https://github.com/spippoli/tart/issues/100) confirms this as implementation detail.
8. **Changing storage adapter.** Answered by [Backup, restore and upgrade mechanics](https://github.com/spippoli/tart/issues/100): no dedicated command; a runbook procedure of backup, environment change, full restore, and verify, since restore copies media into the storage currently configured ([Restore](#3-restore-and-the-erasure-log)).

**Upgrades**
9. **How `tart upgrade` reaches Docker.** Answered by [Backup, restore and upgrade mechanics](https://github.com/spippoli/tart/issues/100): a POSIX host wrapper shipped with each release; the Docker socket is never mounted into a container ([Deployment and releases](#1-deployment-and-releases)).
10. **CVE rebuilds.** Answered by [Backup, restore and upgrade mechanics](https://github.com/spippoli/tart/issues/100): a weekly Trivy scan in CI; High or Critical with a fix available triggers a patch release; no response-time commitment ([Deployment and releases](#1-deployment-and-releases)).

**Monitoring**
11. **What drives the public status.** Answered by [Backup, restore and upgrade mechanics](https://github.com/spippoli/tart/issues/100): any check in `fail` turns it to `fail`, a warning does not; `tart upgrade` waits only for the readiness checks ([Monitoring](#5-monitoring)).
12. **Language of the Operator alert email.** Answered by [Backup, restore and upgrade mechanics](https://github.com/spippoli/tart/issues/100): the Instance's default UI language, with the check key, value, and threshold untranslated ([Monitoring](#5-monitoring)).
13. **Log sizing.** Answered by [Backup, restore and upgrade mechanics](https://github.com/spippoli/tart/issues/100): at most 14 days, bounded in time and not only by size, and 50 MB per service; the mechanism stays implementation, checked by an acceptance criterion ([Monitoring](#5-monitoring)). Amended by [#177](https://github.com/spippoli/tart/issues/177): Docker's `journald` driver with the host journal at `MaxFileSec=1day`, `MaxRetentionSec=13day`, and a 200 MB cap for the whole stack, since no container can rotate Docker's logs by time and journald has no cap per service.

**Data dump**
14. **Nested or separate files.** Answered by [Data dump layout and checklist numbering](https://github.com/spippoli/tart/issues/101): separate NDJSON files with their own ids, referenced by id ([Data dump](#6-data-dump)).
15. **Operator name.** Answered by [Instance configuration keys and contacts](https://github.com/spippoli/tart/issues/85): `operator.name` is a required key; the default attribution is the archive name and the Operator name.
16. **README language.** Answered by [Data dump layout and checklist numbering](https://github.com/spippoli/tart/issues/101): always English, plus the Content language only when the platform has a catalogue for it; otherwise English only, with a no-translation note.
17. **Shape of `data_attribution`.** Answered by [Instance configuration keys and contacts](https://github.com/spippoli/tart/issues/85): one string in the Content language; the platform appends the Instance URL and the dump date.
18. **Timeline names.** Answered by [Public provenance, file rights and position coarsening](https://github.com/spippoli/tart/issues/91): the Timeline names no Submitter, so the dump's "no User names" rule meets no conflict.
19. **Coarsened positions.** Answered by [Public provenance, file rights and position coarsening](https://github.com/spippoli/tart/issues/91): there is no deliberate coarsening; the archive stores only the public geometry, which the dump carries.
20. **Package naming and location.** Answered by [Data dump layout and checklist numbering](https://github.com/spippoli/tart/issues/101): `dumps/data-dump-<YYYYMMDDTHHMMSSZ>.zip` and `dumps/media-<…>.zip` in the data volume, never served, with no automatic clean-up.

**Checklist**
21. **Numbering.** Answered by [Data dump layout and checklist numbering](https://github.com/spippoli/tart/issues/101): this spec's numbers are the only canonical ones, and #46's are historical only. Turning on backups and setting `OPERATOR_ALERT_EMAIL` is now checklist item 12, before launch, because item 16's restore drill presumes backups exist.
22. **Operator acting on Notices.** Answered by [Operator as decider and Moderator self-review](https://github.com/spippoli/tart/issues/93): the Operator has no CLI command or UI for Notices; whoever decides for it is granted the Moderator role (checklist item 25).

### Notes

- [Backups, upgrades and monitoring](https://github.com/spippoli/tart/issues/45) already amended ADR 0004 and `foundations.md` (migrations run from `tart upgrade`) and answered [Rights and legal actions open item 20](rights-and-legal-actions.md#open-items) (backups); it partly answers item 18 (a Purge leaves a content-free Erasure log entry).
- It also answers [Notifications open item 14](notifications.md#open-items): a permanently failed email counts towards the Email health check, surfaces through the external monitor and the Operator alert email, and is listed by `tart jobs failed`. The Notifications spec is not edited by this PR.
- A User's GDPR export (Rights and legal actions) and the Data dump are distinct: the export is personal and private, the dump public and impersonal ([#8](https://github.com/spippoli/tart/issues/8)).
- The ODbL "offer the method to recreate" duty for overlays is met by the committed Overpass query in the configuration repository ([#38](https://github.com/spippoli/tart/issues/38)); tiles and overlays stay out of backups because they can be regenerated.
- [Tech stack decision](https://github.com/spippoli/tart/issues/13) flagged per-container memory as unmeasured; the `backup` service and `tart backup verify` (a temporary database in the `db` container) add to it, which matters for the 4 GB minimum.
