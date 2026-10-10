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

| # | Feature spec | File | Contents | Compile ticket |
|---|---|---|---|---|
| 1 | Foundations | `foundations.md` | Instance configuration, auth and sessions, storage and media pipeline, i18n shell, Operator CLI | [Compile Foundations spec](https://github.com/spippoli/tart/issues/50) |
| 2 | Archive records | [`archive-records.md`](archive-records.md) | Artwork, Artist, Location, Site, Area, Series, Source, Documentation item; physical history; public record pages | [Compile Archive records spec](https://github.com/spippoli/tart/issues/51) |
| 3 | Discovery | `discovery.md` | Map, list, search and filters, map cartography style, basemap pipeline | [Compile Discovery spec](https://github.com/spippoli/tart/issues/52) |
| 4 | Contribution and moderation | `contribution-and-moderation.md` | Submission form, lifecycle, duplicates and Merge, roles | [Compile Contribution and moderation spec](https://github.com/spippoli/tart/issues/53) |
| 5 | Rights and legal actions | `rights-and-legal-actions.md` | Per-file licences, Notices, Withdrawal, Redaction, Reinstatement, Purge, account deletion | [Compile Rights and legal actions spec](https://github.com/spippoli/tart/issues/54) |
| 6 | Notifications | `notifications.md` | Email notifications | [Compile Notifications spec](https://github.com/spippoli/tart/issues/55) |
| 7 | Operations and portability | `operations-and-portability.md` | Backups, upgrades, monitoring, public data dump, Operator compliance checklist | [Compile Operations and portability spec](https://github.com/spippoli/tart/issues/56) |

A feature spec is compiled as soon as the decision tickets it needs are closed; the compile ticket's blockers in the tracker show which specs are ready. A file listed here that does not exist yet has not been compiled.

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
| Map | Tinted-plan style ([ADR 0017](../adr/0017-map-cartography-style.md)); walls and archaeology overlay from OpenStreetMap; attribution `© OpenStreetMap` → `https://www.openstreetmap.org/copyright` | [ADR 0016](../adr/0016-licence-policy-for-map-assets-and-data.md), [ADR 0017](../adr/0017-map-cartography-style.md) |
| Hosting | Docker Compose on a Hetzner CX33 with Hetzner Object Storage through the S3 adapter; budget at most €20/month excluding VAT and off-site backups | [ADR 0004](../adr/0004-mvp-tech-stack.md) |
| Authentication | Built-in passwordless (email code + passkeys); not configurable | [ADR 0005](../adr/0005-passwordless-in-app-auth.md) |

**Not yet decided** (owned by the feature spec that compiles it): the exact boundary polygon and default view, logo and accent colour, contact points, the public image rendition cap, Notice reasons, the map style ownership model ([Map style ownership: Instance theme vs style file](https://github.com/spippoli/tart/issues/37)), and the tile pipeline ([Basemap tile pipeline per Instance](https://github.com/spippoli/tart/issues/38)).

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

### Open

| Ticket | Feeds |
|---|---|
| [Map style ownership: Instance theme vs style file](https://github.com/spippoli/tart/issues/37) | Discovery |
| [Basemap tile pipeline per Instance](https://github.com/spippoli/tart/issues/38) | Discovery |
| [Map behaviour: clustering, geometries, overlays, stratigraphy](https://github.com/spippoli/tart/issues/39) | Discovery |
| [List alternative and map/list sync](https://github.com/spippoli/tart/issues/40) | Discovery |
| [Search and filters](https://github.com/spippoli/tart/issues/41) | Discovery |
| [Duplicate detection and Merge](https://github.com/spippoli/tart/issues/42) | Contribution and moderation |
| [Moderation roles and permissions](https://github.com/spippoli/tart/issues/43) | Contribution and moderation; Rights and legal actions |
| [Notifications](https://github.com/spippoli/tart/issues/44) | Notifications |
| [Backups, upgrades and monitoring](https://github.com/spippoli/tart/issues/45) | Operations and portability |
| [Operator compliance checklist](https://github.com/spippoli/tart/issues/46) | Operations and portability |
| [Public data dump](https://github.com/spippoli/tart/issues/47) | Operations and portability |

Still unticketed: performance and limits (upload limits, rate limiting of Submissions and Notices, spam and abuse protection under `open` registration), expected to feed Foundations and/or Contribution and moderation.

When a ticket closes, its resolution comment ends with a `Feeds:` line; move it from Open to Closed here in the same PR that compiles the spec it feeds.

## Out of scope for the MVP

The full list lives on the map [Wayfinder: TART MVP specification](https://github.com/spippoli/tart/issues/2). In short: Instance configuration UI (Journey F); UI design tokens and a full design system (the map cartography style is in scope); in-app role management; in-app notification centre; custom metadata fields; video and audio documentation; bulk import; SEO metadata beyond the URL scheme of [ADR 0010](../adr/0010-public-url-scheme.md); drafting the Terms of Service, privacy policy, trademark policy, and CLA; professional legal review; an accessibility verification procedure.
