# TART MVP specification — index

This is the entry point of the TART MVP specification: the hand-off from design to implementation by AI agents. It lists the feature specs, the order to build them in, Rome's configuration, and where each design decision ended up. The structure and assembly procedure were decided in [Spec format and assembly](https://github.com/spippoli/tart/issues/48).

## Overview

TART is a collaborative, moderated platform for documenting and preserving the history of urban art. Each deployment (an **Instance**) runs one local archive; the first is Rome ("Rome Urban Art Archive — Powered by TART"). The software is source-available for non-commercial use, provisionally under PolyForm Noncommercial 1.0.0 ([ADR 0011](../adr/0011-provisional-software-license.md)).

**Destination.** An MVP product specification ready for implementation by AI agents, with Rome as the first Instance, configured from files. It covers the domain model, information architecture, journeys A–E, the platform/Instance boundary, i18n, tech stack, map cartography style, content-rights rules, and a provisional Licensing Decision Record.

**MVP scope.** Journeys A–E of the brief (`README.md` §11):

| Journey | Covered by |
|---|---|
| A — Discover urban art | Archive records, Discovery |
| B — Document a new artwork | Contribution and moderation |
| C — Contribute to an existing artwork | Contribution and moderation |
| D — Document an artwork's disappearance | Archive records (physical history), Contribution and moderation |
| E — Moderate contributions | Contribution and moderation, Notifications |

Journey F (creating a new Instance through a UI) is out of scope: an Instance is configured from files ([ADR 0009](../adr/0009-instance-configuration-as-validated-files.md)). Artist pages are full and Artist edits are moderated. Documentation media are images, PDFs, text, and links; the archive starts empty, with no import.

## Sources of truth

The spec does not restate these; every feature spec cites them.

- **Invariants**: the "Architectural invariants", "Language rules", and "Implementation principles" in [`CLAUDE.md`](../../CLAUDE.md) apply to every feature spec and override any reading of a spec that contradicts them.
- **Vocabulary**: [`GLOSSARY.md`](../../GLOSSARY.md). Terms in **bold** in the specs are glossary terms and carry exactly that meaning.
- **Hard-to-reverse decisions**: the ADRs in [`docs/adr/`](../adr/).
- **Product brief**: [`README.md`](../../README.md). Where a decision deliberately narrows the brief (for example, single Content language, [ADR 0008](../adr/0008-single-content-language-and-prefixed-ui-languages.md)), the decision wins.

Rule of thumb: hard to reverse → ADR; vocabulary → glossary; everything else → feature spec. Resolution comments on the closed tickets remain as history; the feature spec is the normative source.

## Feature specs

Each feature spec is a file in `docs/spec/` with a thin tracking issue whose child issues are the implementation tickets (produced with `to-tickets`). It follows the `to-spec` template — Problem Statement, Solution, User Stories, Implementation Decisions, Testing Decisions, Out of Scope, Further Notes — plus **References** (ADRs and glossary terms applied), **Acceptance criteria** (verifiable behaviour, including the WCAG 2.2 AA and i18n requirements that apply), and **Instance configuration** (the keys the feature reads, with Rome's value). Every section except Further Notes is normative.

### Delivery order

Build in this order; each spec depends only on the ones above it.

| # | Feature spec | File | Contents | Compile ticket | Tracking issue |
|---|---|---|---|---|---|
| 1 | Foundations | [`foundations.md`](foundations.md) | Instance configuration, auth and sessions, storage and media pipeline, i18n shell, Operator CLI | [Compile Foundations spec](https://github.com/spippoli/tart/issues/50) | [Foundations spec](https://github.com/spippoli/tart/issues/62) |
| 2 | Archive records | [`archive-records.md`](archive-records.md) | Artwork, Artist, Location, Site, Area, Series, Source, Documentation item; physical history; public record pages | [Compile Archive records spec](https://github.com/spippoli/tart/issues/51) | [Archive records spec](https://github.com/spippoli/tart/issues/63) |
| 3 | Discovery | [`discovery.md`](discovery.md) | Map, list, search and filters, map cartography style, basemap pipeline | [Compile Discovery spec](https://github.com/spippoli/tart/issues/52) | [Discovery spec](https://github.com/spippoli/tart/issues/80) |
| 4 | Contribution and moderation | [`contribution-and-moderation.md`](contribution-and-moderation.md) | Submission form, lifecycle, duplicates and Merge, roles | [Compile Contribution and moderation spec](https://github.com/spippoli/tart/issues/53) | [Contribution and moderation spec](https://github.com/spippoli/tart/issues/73) |
| 5 | Rights and legal actions | [`rights-and-legal-actions.md`](rights-and-legal-actions.md) | Per-file licences, Notices, Withdrawal, Redaction, Reinstatement, Purge, account deletion | [Compile Rights and legal actions spec](https://github.com/spippoli/tart/issues/54) | [Rights and legal actions spec](https://github.com/spippoli/tart/issues/74) |
| 6 | Notifications | [`notifications.md`](notifications.md) | Email notifications | [Compile Notifications spec](https://github.com/spippoli/tart/issues/55) | [Notifications spec](https://github.com/spippoli/tart/issues/75) |
| 7 | Operations and portability | [`operations-and-portability.md`](operations-and-portability.md) | Backups, upgrades, monitoring, public data dump, Operator compliance checklist | [Compile Operations and portability spec](https://github.com/spippoli/tart/issues/56) | [Operations and portability spec](https://github.com/spippoli/tart/issues/81) |

All seven feature specs are compiled. Each still lists open items in its Further Notes; the decision tickets that settle them amend the spec in their own PR and block its tracking issue, so a tracking issue with no open blocker is ready for `to-tickets`.

## Rome configuration summary

Rome is the reference Instance. Its configuration is a secret-free directory of files (`instance.toml`, vocabulary files, Markdown texts, logo, map style, GeoJSON boundary); secrets and infrastructure live in environment variables ([ADR 0009](../adr/0009-instance-configuration-as-validated-files.md)). Each feature spec's **Instance configuration** section is normative for the exact keys; this table only summarises the values decided so far.

| Area | Rome | Decided in |
|---|---|---|
| Identity | Archive name "Rome Urban Art Archive" (brief §4); "Powered by TART" in the footer, rendered by the platform, not a key | [ADR 0009](../adr/0009-instance-configuration-as-validated-files.md), [ADR 0011](../adr/0011-provisional-software-license.md) |
| Geography | Country `IT`, time zone `Europe/Rome`; a GeoJSON boundary rejects Locations outside it | [ADR 0009](../adr/0009-instance-configuration-as-validated-files.md) |
| Content language | `it` | [ADR 0008](../adr/0008-single-content-language-and-prefixed-ui-languages.md) |
| UI languages | `it` (default), `en`; both URL-prefixed | [ADR 0008](../adr/0008-single-content-language-and-prefixed-ui-languages.md) |
| Open vocabularies | Expression type, Surface type, Decision message reasons; starting from the brief's §9 list | [ADR 0009](../adr/0009-instance-configuration-as-validated-files.md) |
| Areas | Archive data (e.g. the rioni), entered through Submissions; none at launch | [ADR 0009](../adr/0009-instance-configuration-as-validated-files.md) |
| Registration | `open` | [ADR 0009](../adr/0009-instance-configuration-as-validated-files.md) |
| Minimum age | 14, self-declared | [ADR 0012](../adr/0012-per-file-licence-with-rights-basis.md) |
| Data licence | `CC-BY-SA-4.0` | [ADR 0012](../adr/0012-per-file-licence-with-rights-basis.md) |
| File licence allowlist | `CC-BY-4.0`, `CC-BY-SA-4.0`, `CC0-1.0`; default `CC-BY-SA-4.0` | [ADR 0012](../adr/0012-per-file-licence-with-rights-basis.md) |
| Operational | `draft_expiry_days = 90`, `max_upload_mb = 25` | [ADR 0009](../adr/0009-instance-configuration-as-validated-files.md) |
| Map | Tinted-plan style ([ADR 0017](../adr/0017-map-cartography-style.md)) as two Instance-owned files, `map/style.light.json` and `map/style.dark.json`; walls and archaeology overlay from OpenStreetMap, committed as GeoJSON with its Overpass query; attribution `© OpenStreetMap` → `https://www.openstreetmap.org/copyright` | [ADR 0009](../adr/0009-instance-configuration-as-validated-files.md), [ADR 0016](../adr/0016-licence-policy-for-map-assets-and-data.md), [ADR 0017](../adr/0017-map-cartography-style.md) |
| Basemap tiles | Local Protomaps extract (boundary + 2 km) made by `tart tiles update`, refreshed manually | [ADR 0009](../adr/0009-instance-configuration-as-validated-files.md), [Basemap tile pipeline per Instance](https://github.com/spippoli/tart/issues/38) |
| Moderation | `self_approval = true` at launch; switched to `false` once at least two Moderators are active (Operator checklist) | [ADR 0009](../adr/0009-instance-configuration-as-validated-files.md), [Moderation roles and permissions](https://github.com/spippoli/tart/issues/43) |
| Hosting | Docker Compose on a Hetzner CX33 with Hetzner Object Storage through the S3 adapter; budget at most €20/month excluding VAT and off-site backups | [ADR 0004](../adr/0004-mvp-tech-stack.md) |
| Authentication | Built-in passwordless (email code + passkeys); not configurable | [ADR 0005](../adr/0005-passwordless-in-app-auth.md) |
| Backups | On at launch: nightly `pg_dump` in restic and encrypted `rclone sync` of media to a Hetzner Storage Box | [ADR 0020](../adr/0020-backups-replay-erasures-and-forward-only-upgrades.md) |

**Not yet decided** (settled by [Rome Instance values](https://github.com/spippoli/tart/issues/86)): the archive name in Italian, short description and place name, the exact boundary polygon and default view, logo, favicon, and accent colour (a light and a dark value), contact points, the public image rendition cap, Surface types, Decision message reasons, Notice reasons, Rome's labels for Expression types, the Rome Operator, and the backup location, schedule, and Operator alert address.

## Traceability

Each decision ticket of the map [Wayfinder: TART MVP specification](https://github.com/spippoli/tart/issues/2) and the feature specs that incorporate it. *Background* means a research ticket whose findings informed an ADR or decision but which no spec incorporates directly. Open tickets are listed so a reader can see what each spec still waits on.

### Closed

| Ticket | Recorded in | Feeds |
|---|---|---|
| [Core domain model and glossary](https://github.com/spippoli/tart/issues/3) | Glossary, ADRs 0001–0003 | Archive records; Contribution and moderation |
| [Uncertainty and provenance model](https://github.com/spippoli/tart/issues/4) | Glossary, ADR 0006 | Archive records; Contribution and moderation (validation) |
| [Submission and moderation lifecycle](https://github.com/spippoli/tart/issues/5) | Glossary, ADRs 0002, 0007 | Contribution and moderation; Foundations (draft expiry) |
| [Platform vs instance configuration boundary](https://github.com/spippoli/tart/issues/6) | Glossary, ADR 0009 | Foundations; Spec index (Rome configuration) |
| [Research: non-commercial source-available licenses](https://github.com/spippoli/tart/issues/7) | — | Background (ADR 0011) |
| [Research: archive data and contributor content licensing, GDPR](https://github.com/spippoli/tart/issues/8) | — | Background (ADRs 0012–0013) |
| [Research: frontend framework for TS + MapLibre + i18n with FastAPI](https://github.com/spippoli/tart/issues/9) | — | Background (ADR 0004) |
| [Research: media pipeline and storage within budget](https://github.com/spippoli/tart/issues/10) | — | Background (ADR 0004); Foundations (media pipeline) |
| [Research: self-hostable authentication for FastAPI](https://github.com/spippoli/tart/issues/11) | — | Background (ADR 0005) |
| [Licensing Decision Record (provisional)](https://github.com/spippoli/tart/issues/12) | ADR 0011, `LICENSE` | Spec index (overview); Operations and portability (CI licence allow-list) |
| [Tech stack decision](https://github.com/spippoli/tart/issues/13) | ADRs 0004–0005 | Foundations; Operations and portability (topology, sizing) |
| [Content rights and GDPR product rules](https://github.com/spippoli/tart/issues/14) | Glossary, ADRs 0012–0013 | Rights and legal actions; Contribution and moderation (upload rights fields); Notifications (statements of reasons) |
| [Information architecture and page inventory](https://github.com/spippoli/tart/issues/15) | ADR 0010 | Foundations (shell, navigation, sign-in, account, About pages); Archive records (record pages); Discovery (Explore and Archive views); Contribution and moderation (hub, Submission page, queue); Rights and legal actions (report entry point) |
| [i18n strategy: UI vs multilingual content](https://github.com/spippoli/tart/issues/16) | Glossary, ADRs 0008, 0004 | Foundations |
| [Status, uncertainty and condition presentation rules](https://github.com/spippoli/tart/issues/17) | ADR 0015 | Archive records; Discovery (map signs); Contribution and moderation (proposal preview) |
| [Research: Digital Services Act duties for an archive Instance](https://github.com/spippoli/tart/issues/19) | — | Background (ADR 0013); Rights and legal actions; Operations and portability (compliance checklist) |
| [Artist records, personal data, and artist claims](https://github.com/spippoli/tart/issues/20) | ADR 0014 | Archive records; Rights and legal actions |
| [Submission form flow](https://github.com/spippoli/tart/issues/27) | Glossary (`condition recorded`) | Contribution and moderation |
| [Research: map cartography style inputs](https://github.com/spippoli/tart/issues/34) | — | Background (ADRs 0016–0017); Discovery |
| [Licence policy for map assets and basemap data](https://github.com/spippoli/tart/issues/35) | ADR 0016 | Discovery; Rights and legal actions (ODbL boundary); Operations and portability (CI allow-list, Operator documentation) |
| [Map cartography style](https://github.com/spippoli/tart/issues/36) | ADR 0017 | Discovery |
| [Spec format and assembly](https://github.com/spippoli/tart/issues/48) | This index | Spec index |
| [Map style ownership: Instance theme vs style file](https://github.com/spippoli/tart/issues/37) | ADR 0009 (amended) | Discovery; Foundations (map configuration, accent) |
| [Basemap tile pipeline per Instance](https://github.com/spippoli/tart/issues/38) | ADR 0009 (amended) | Discovery; Foundations (Operator CLI); Operations and portability (tiles out of backups) |
| [Map behaviour: clustering, geometries, overlays, stratigraphy](https://github.com/spippoli/tart/issues/39) | ADR 0019 | Discovery |
| [List alternative and map/list sync](https://github.com/spippoli/tart/issues/40) | — | Discovery; Contribution and moderation (Location step) |
| [Search and filters](https://github.com/spippoli/tart/issues/41) | — | Discovery |
| [Duplicate detection and Merge](https://github.com/spippoli/tart/issues/42) | Glossary, ADR 0018 | Contribution and moderation |
| [Moderation roles and permissions](https://github.com/spippoli/tart/issues/43) | Glossary, ADR 0009 (amended) | Contribution and moderation; Rights and legal actions; Foundations (role CLI, `self_approval`, Invitations) |
| [Notifications](https://github.com/spippoli/tart/issues/44) | Glossary, ADR 0008 (amended) | Notifications; Foundations (email language) |
| [Backups, upgrades and monitoring](https://github.com/spippoli/tart/issues/45) | Glossary, ADR 0020 | Operations and portability; Foundations (migrations); Rights and legal actions (Erasure log) |
| [Operator compliance checklist](https://github.com/spippoli/tart/issues/46) | — | Operations and portability |
| [Public data dump](https://github.com/spippoli/tart/issues/47) | Glossary | Operations and portability |
| [Compile spec index](https://github.com/spippoli/tart/issues/49) | This index | Spec index |
| [Compile Foundations spec](https://github.com/spippoli/tart/issues/50) | `foundations.md` | Foundations |
| [Compile Archive records spec](https://github.com/spippoli/tart/issues/51) | `archive-records.md` | Archive records |
| [Compile Discovery spec](https://github.com/spippoli/tart/issues/52) | `discovery.md` | Discovery |
| [Compile Contribution and moderation spec](https://github.com/spippoli/tart/issues/53) | `contribution-and-moderation.md` | Contribution and moderation |
| [Compile Rights and legal actions spec](https://github.com/spippoli/tart/issues/54) | `rights-and-legal-actions.md` | Rights and legal actions |
| [Compile Notifications spec](https://github.com/spippoli/tart/issues/55) | `notifications.md` | Notifications |
| [Compile Operations and portability spec](https://github.com/spippoli/tart/issues/56) | `operations-and-portability.md` | Operations and portability |
| [Spec index and Foundations housekeeping](https://github.com/spippoli/tart/issues/82) | This index, `foundations.md` | Spec index; Foundations |
| [Apply decided answers across feature specs](https://github.com/spippoli/tart/issues/83) | ADR 0002 (amended), `archive-records.md`, `contribution-and-moderation.md`, `rights-and-legal-actions.md`, `notifications.md` | Contribution and moderation; Archive records; Rights and legal actions; Notifications |
| [Media types, renditions and caching](https://github.com/spippoli/tart/issues/88) | `foundations.md` | Foundations |

### Open

These tickets settle the open items listed in the feature specs' Further Notes.

| Ticket | Feeds |
|---|---|
| [Security constants and abuse protection](https://github.com/spippoli/tart/issues/84) | Foundations; Contribution and moderation; Notifications |
| [Instance configuration keys and contacts](https://github.com/spippoli/tart/issues/85) | Foundations; Contribution and moderation; Rights and legal actions; Notifications; Operations and portability |
| [Rome Instance values](https://github.com/spippoli/tart/issues/86) | Spec index; Foundations; Discovery; Notifications; Operations and portability |
| [Accounts: registration, email change, deletion and export](https://github.com/spippoli/tart/issues/87) | Foundations; Rights and legal actions; Notifications |
| [History event types and Uncertain-date ordering](https://github.com/spippoli/tart/issues/89) | Archive records; Discovery; Contribution and moderation |
| [Record descriptive fields, text alternatives and slugs](https://github.com/spippoli/tart/issues/90) | Archive records; Contribution and moderation |
| [Public provenance, file rights and position coarsening](https://github.com/spippoli/tart/issues/91) | Archive records; Rights and legal actions; Operations and portability |
| [Withdrawal effects and views of hidden content](https://github.com/spippoli/tart/issues/92) | Archive records; Rights and legal actions; Discovery |
| [Operator as decider and Moderator self-review](https://github.com/spippoli/tart/issues/93) | Contribution and moderation; Rights and legal actions; Notifications; Operations and portability |
| [Notice handling details](https://github.com/spippoli/tart/issues/94) | Rights and legal actions; Notifications |
| [Redaction, current-value removal and Purge](https://github.com/spippoli/tart/issues/95) | Rights and legal actions |
| [Submission lifecycle edge cases](https://github.com/spippoli/tart/issues/96) | Contribution and moderation |
| [Editor steps not yet prototyped](https://github.com/spippoli/tart/issues/97) | Contribution and moderation |
| [Map rendering details, style endpoint and theme](https://github.com/spippoli/tart/issues/98) | Discovery; Foundations |
| [Search and filter details](https://github.com/spippoli/tart/issues/99) | Discovery |
| [Backup, restore and upgrade mechanics](https://github.com/spippoli/tart/issues/100) | Operations and portability |
| [Data dump layout and checklist numbering](https://github.com/spippoli/tart/issues/101) | Operations and portability |

When a ticket closes, its resolution comment ends with a `Feeds:` line; move it from Open to Closed here in the PR that amends the spec it feeds.

## Out of scope for the MVP

The full list lives on the map [Wayfinder: TART MVP specification](https://github.com/spippoli/tart/issues/2). In short: Instance configuration UI (Journey F); UI design tokens and a full design system (the map cartography style is in scope); in-app role management; in-app notification centre; custom metadata fields; video and audio documentation; bulk import; SEO metadata beyond the URL scheme of [ADR 0010](../adr/0010-public-url-scheme.md); drafting the Terms of Service, privacy policy, trademark policy, and CLA; professional legal review; an accessibility verification procedure.
