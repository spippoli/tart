---
status: accepted (provisional, pending professional legal review)
---

# Licensing Decision Record: PolyForm Noncommercial 1.0.0, provisionally

TART's software is licensed under the [PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0) (`LICENSE`), provisionally, until professional legal review confirms or replaces it. It is the only established license we found that keeps the non-commercial limit permanently, allows deployment, modification, forks, and redistribution, and expressly treats non-profit organisations as permitted users regardless of how they are funded. Because no candidate is Open Source, TART is described as **source-available**, never "Open Source". The license covers only the software: the TART brand, Instance archive data, contributor content, and the artworks themselves are separate concerns (README §7). Research input: [Research: non-commercial source-available licenses](https://github.com/spippoli/tart/issues/7), full findings on the `research/source-available-licenses` branch (`docs/research/source-available-licenses.md`).

## 1. Selected license

PolyForm Noncommercial 1.0.0, unmodified, with the line `Required Notice: Copyright 2026 spippoli (https://github.com/spippoli/tart)`. It covers the whole repository, including documentation (README, ADRs, glossary), except future TART brand assets such as the logo, which the trademark policy governs (section 7).

The **licensor** is the project maintainer, as an individual, who also holds the TART name and logo provisionally. Transferring both to an entity (association or foundation) once one exists is anticipated.

## 2. Why

- **Permanent limit**: PolyForm Noncommercial, Prosperity, CC BY-NC, and Commons Clause keep the limit forever. The Business Source License converts to a GPL-compatible license within four years, and production use needs a custom Additional Use Grant.
- **Community safe harbor**: PolyForm Noncommercial names charitable, educational, public research, and government organisations as permitted "regardless of the source of funding". Prosperity has the same safe harbor but adds a 30-day commercial trial we don't want.
- **Paid assistance**: Commons Clause's text names consulting and support as forbidden "Sell" activity, which contradicts README §6.
- **Fit for software**: Creative Commons recommends against CC licenses for software.
- **Standard text**: the brief prefers an established license to a custom one. The gaps below are documented instead of patched with custom terms.

## 3. Permitted uses

Within the license's "any noncommercial purpose": running an Instance; modifying and extending the software; forking; deploying for another city or country; operating a community archive; redistributing copies, modified or not, with the license terms and the `Required Notice:` line. Personal research, study, testing, and hobby use. Use by the organisation types named in the Noncommercial Organizations clause.

## 4. Prohibited uses

Any commercial purpose, including selling TART or modified versions, offering TART as a commercial SaaS or hosted product, charging users for access as a commercial service, and otherwise exploiting TART commercially. The license allows no sublicensing at all.

## 5. Local community deployments

An Instance run by a community, an association, a public body, or individuals for a non-commercial archive is a permitted use. The license imposes no obligation to publish changes: a fork may run publicly without sharing its source. The data and contributor-content licences of each Instance are Instance configuration (`data_license`, `contribution_license`, ADR 0009), not the software license.

## 6. Commercial use

The license doesn't define "commercial". The project states its intent in this **non-binding interpretation note**. It doesn't modify the license.

- **Consistent with the mission**: recovering infrastructure costs (hosting, storage, domains, backups); donations and membership fees that fund an Instance; a contractor paid by a non-commercial organisation to deploy, maintain, or extend *that organisation's* Instance.
- **Not consistent**: offering hosted TART Instances as a paid product; selling TART, modified versions, or access to an Instance; using TART as the basis of a commercial product.

The licensor states that it will not take action against uses consistent with the mission as described here. Whether this statement binds the licensor is a legal-review point.

## 7. The TART name and logo

No software license grants or requires brand use, so the name and logo are governed by a **separate trademark policy**. This record fixes its principles; drafting the policy text is outside this effort.

- **"Powered by TART"** is rendered by the platform by default (ADR 0009) and may be used by any non-commercial deployment, modified or not. It is permitted, not mandatory: a deployment or fork may remove it.
- Using "TART" or the TART logo as a deployment's primary identity needs the holder's permission.
- No deployment or fork may present itself as the official TART project or claim its endorsement.

## 8. Contributions and third-party dependencies

**Contributions.** Contributors sign a **Contributor License Agreement based on an established template** (Contributor Agreements / Project Harmony family). It grants the licensor a broad license with the right to relicense, restricted to licenses consistent with the non-commercial mission. Contributors keep their copyright. This keeps the license provisional in practice: without the CLA, relicensing would need every contributor's consent. Until the CLA is in place, external code contributions are not accepted.

**Dependencies.** The CI licence allow-list (ADR 0004) enforces three tiers:

| Tier | Licences | Allowed as |
|---|---|---|
| Permissive | MIT, BSD, Apache-2.0, ISC, PSF, Zlib | any dependency |
| Weak copyleft | LGPL, MPL-2.0 | unmodified libraries, dynamically linked |
| Strong copyleft | GPL, AGPL | separate, unmodified programs in their own container only; never linked into or bundled with TART code |

Concrete applications:

- **PostGIS (GPL-2.0+)**: the Compose stack uses the upstream `postgis/postgis` image unmodified. TART neither builds nor redistributes an image containing PostGIS, and talks to it only over SQL.
- **HEIC**: `pi-heif` (decode-only; its binary wheels leave out the GPL x265 encoder) replaces `pillow-heif` (ADR 0004 amended). It still bundles libheif and libde265 (LGPL), and HEVC decoding may be patent-encumbered. If review rules it out, HEIC uploads are dropped and contributors convert to JPEG.
- **Non-code assets and map data** (fonts, map style design, icons, OpenStreetMap data) follow a separate policy, not these tiers (ADR 0016).
- **Already excluded**: PyMuPDF (AGPL) and libvips (ADR 0004), Zitadel (ADR 0005), Garage (no self-hosted S3 server in the reference stack).

## 9. Professional legal review

Recommended before the license is final, and before the Rome Instance launches:

1. How Italian and EU law interpret the undefined "noncommercial", and whether an Italian translation is needed.
2. Whether Italian *associazioni culturali*, APS/ETS, and informal groups fall within the Noncommercial Organizations safe harbor.
3. Whether cost-recovery fees and paid deployment or maintenance contractors are commercial use.
4. The legal weight of the interpretation note and the licensor's statement (section 6).
5. The GPL boundary for PostGIS when the upstream image is used unmodified.
6. LGPL obligations for libheif and libde265, and HEVC patent exposure.
7. The CLA text, its signing mechanism, and the enforceability of the mission restriction on relicensing.
8. An individual as licensor and brand holder, and the later transfer to an entity.
9. The trademark policy text and whether to register "TART".
10. Enforceability of the license's "Acceptance" clause under Italian contract law.

## Considered Options

- **Business Source License 1.1**: the forced conversion ends the non-commercial limit, and the Additional Use Grant is custom text.
- **Prosperity 3.0.0**: same safe harbors, but a 30-day commercial trial.
- **Apache-2.0 + Commons Clause**: forbids paid consulting in its text, and the combination confuses readers about whether it is Apache-licensed.
- **CC BY-NC 4.0**: not designed for software.
- **PolyForm Shield / Small Business**: allow some commercial SaaS.
- **A custom license**: rejected by the brief unless no standard text fits. The remaining gaps (contractors, cost recovery) are handled by the interpretation note and legal review instead.
- **DCO instead of a CLA**: lighter, but it would lock the provisional license in place.

## Consequences

- The repository is no longer "all rights reserved": anyone may use it for non-commercial purposes now.
- A fork's improvements need not flow back; none of the candidates requires it.
- A contribution policy (`CONTRIBUTING.md` with the CLA) must exist before outside pull requests are merged.
