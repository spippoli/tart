# Research: non-commercial source-available licenses

- **Ticket**: [#7](https://github.com/spippoli/tart/issues/7) (parent map [#2](https://github.com/spippoli/tart/issues/2)); feeds the Licensing Decision Record ticket [#12](https://github.com/spippoli/tart/issues/12).
- **Date of research**: 2026-10-08.
- **Status**: research only. This document records what the license texts say and where they need interpretation. It does **not** select a license and it makes **no legal conclusions**. Every point marked **[Legal review]** needs professional legal advice, ideally from a lawyer familiar with Italian and EU copyright and contract law. The candidate licenses were drafted with US law in mind.

## Question

How do PolyForm Noncommercial, the Business Source License, and other established source-available or non-commercial licenses treat each criterion in README §6? The criteria are independent local deployments, modification and forks, redistribution, hosted/SaaS use, the definition of commercial use, community organizations, infrastructure costs, contributor clarity, enforceability, the "Powered by TART" model, trademark interaction, and third-party dependency compatibility.

## Licenses examined and primary sources

| Short name | Version | Primary source (text read for this note) |
| --- | --- | --- |
| PolyForm Noncommercial | 1.0.0 | <https://polyformproject.org/licenses/noncommercial/1.0.0> · canonical text in <https://github.com/polyformproject/polyform-licenses/blob/1.0.0/PolyForm-Noncommercial-1.0.0.md> |
| PolyForm Shield | 1.0.0 | <https://github.com/polyformproject/polyform-licenses/blob/1.0.0/PolyForm-Shield-1.0.0.md> |
| PolyForm Small Business | 1.0.0 | <https://github.com/polyformproject/polyform-licenses/blob/1.0.0/PolyForm-Small-Business-1.0.0.md> |
| Business Source License (BUSL) | 1.1 | <https://mariadb.com/bsl11/> · SPDX copy <https://github.com/spdx/license-list-data/blob/main/text/BUSL-1.1.txt> · steward FAQ <https://mariadb.com/bsl-faq-adopting/> |
| Commons Clause | 1.0 | <https://commonsclause.com/> (text and steward FAQ) |
| Prosperity Public License | 3.0.0 (latest listed) | <https://prosperitylicense.com/versions/3.0.0> |
| CC BY-NC | 4.0 | <https://creativecommons.org/licenses/by-nc/4.0/legalcode.en> · CC FAQ <https://creativecommons.org/faq/> |
| Elastic License (ELv2), for contrast | 2.0 | SPDX copy <https://github.com/spdx/license-list-data/blob/main/text/Elastic-2.0.txt> (official URL <https://www.elastic.co/licensing/elastic-license>) |
| Open Source Definition | — | <https://opensource.org/osd> |

ELv2 is not a non-commercial license. It is included only because it shows a different restriction model, a ban on hosted services, which TART might be tempted to borrow.

## Cross-cutting facts

1. **None of these licenses is Open Source.** OSD criterion 6 says a license "must not restrict anyone from making use of the program in a specific field of endeavor. For example, it may not restrict the program from being used in a business" ([OSD](https://opensource.org/osd)). The stewards say so themselves: MariaDB, "The BSL is not an Open Source license and we do not claim it to be one" ([BSL FAQ](https://mariadb.com/bsl-faq-adopting/)); BUSL's own Notice, "is not an Open Source license"; and Commons Clause answers "Is this 'Open Source'? No." ([commonsclause.com](https://commonsclause.com/)). Whichever is chosen, TART must be described as "source-available" or "freely available for non-commercial use".
2. **None of them is copyleft for network use.** None requires someone who runs a modified copy as a website to publish their changes. PolyForm, Prosperity and BUSL impose notice obligations only on people who *distribute copies*. So a non-commercial fork can stay closed-source while it runs publicly. If TART wants improvements to flow back, no candidate gives it that by default. Combining with the AGPL raises its own issues (see Dependencies).
3. **None of them governs the TART name and logo.** All are copyright (and sometimes patent) licenses. Brand control needs a separate trademark policy (README §7).
4. **"Commercial" is mostly undefined.** Only CC BY-NC (a definition), Commons Clause (a definition of "Sell") and BUSL (by a different mechanism, "production use") give a test. PolyForm Noncommercial and Prosperity give safe harbors, not a definition.

## Per-license summary

### PolyForm Noncommercial 1.0.0

- **Grant**: copyright license "for any permitted purpose". Separate grants to distribute copies and to "make changes and new works based on the software for any permitted purpose". Also includes a patent license.
- **Permitted purpose**: "Any noncommercial purpose is a permitted purpose." This is followed by two safe harbors:
  - *Personal Uses*: "research, experiment, and testing for the benefit of public knowledge, personal study, private entertainment, hobby projects, amateur pursuits, or religious observance, without any anticipated commercial application".
  - *Noncommercial Organizations*: "Use by any charitable organization, educational institution, public research organization, public safety or health organization, environmental protection organization, or government institution is use for a permitted purpose regardless of the source of funding or obligations resulting from the funding."
- **"Commercial"/"noncommercial" is not defined.**
- **Notices**: anyone receiving a copy must get the terms (or their URL) plus any `Required Notice:` lines.
- **No Other Rights**: no sublicensing or transfer; "These terms do not imply any other licenses."
- **Violations**: a 32-day cure period after the first written notice, after which licenses end.
- Steward: PolyForm Project, "a group of experienced licensing lawyers and technologists" ([README](https://github.com/polyformproject/polyform-licenses/blob/1.0.0/README.md)). Modified versions must drop the PolyForm name.

### PolyForm Shield 1.0.0 and PolyForm Small Business 1.0.0

- **Shield**: "Any purpose is a permitted purpose, except for providing any product that competes with the software or any product the licensor or any of its affiliates provides using the software." Competition explicitly includes products provided "free of charge". It is a **noncompete**, not a non-commercial license: a for-profit company could sell services built on TART as long as it does not compete with TART or with the licensor's own products.
- **Small Business**: use is permitted if "your company has fewer than 100 total individuals working as employees and independent contractors, and less than 1,000,000 USD (2019) total revenue in the prior tax year". It is **size-based**: a small for-profit company could run commercial hosted TART.
- Both therefore allow some uses that §6 wants to prohibit (commercial SaaS by non-competitors or small firms).

### Business Source License 1.1

- **Grant**: "copy, modify, create derivative works, redistribute, and make non-production use of the Licensed Work." Production use is allowed only within an optional **Additional Use Grant** written by the licensor.
- **Time limit**: on the Change Date, or four years after a version's first public distribution if that comes sooner, the version converts to the **Change License**. Licensor covenant: the Change License must be "GPL Version 2.0 or any later version, or a license that is compatible with GPL Version 2.0 or a later version".
- **Commercial model**: non-compliant use means "you must purchase a commercial license from the Licensor". The license assumes the licensor sells such licenses.
- **Trademarks**: "This License does not grant you any right in any trademark or logo of Licensor".
- **Termination**: any violation "will automatically terminate your rights ... for the current and all other versions".
- **Licensor covenants**: the licensor may change only the parameters (Additional Use Grant, Change Date, Change License) and must not "modify this License in any other way". The name "Business Source License" is a MariaDB trademark.
- The FAQ does not define "production use" ([BSL FAQ](https://mariadb.com/bsl-faq-adopting/)).

### Commons Clause 1.0

- A rider on a base license such as Apache 2.0: "the License does not grant to you ... the right to Sell the Software".
- "Sell" means "to provide to third parties, for a fee or other consideration (including without limitation fees for hosting or consulting/ support services related to the Software), a product or service whose value derives, entirely or substantially, from the functionality of the Software."
- The steward's FAQ says the opposite of the clause text on consulting ("You may even provide consulting services"). It also says selling a product that just makes the software "available via SaaS" would be restricted.
- Everything else (modification, redistribution, non-paid hosting) is governed by the base license.

### Prosperity Public License 3.0.0

- "This license allows you to use and share this software for noncommercial purposes for free and to try this software for commercial purposes for thirty days."
- It has the same *Personal Uses* and *Noncommercial Organizations* safe harbors as PolyForm Noncommercial, word for word apart from phrasing ("doesn't count as use for a commercial purpose").
- **Contributions Back**: contributing changes to the contributor under a standard permissive license "doesn't count as use for a commercial purpose".
- **Reliability**: "The contributor can't revoke this license."
- The copyright grant is broad ("do everything with this software that would otherwise infringe their copyright"). It is limited by the agreement's rules.
- It includes a **30-day commercial trial per company**, which is a deliberate allowance for commercial use.

### CC BY-NC 4.0

- **NonCommercial**: "not primarily intended for or directed towards commercial advantage or monetary compensation."
- **Grant**: "reproduce and Share the Licensed Material ... for NonCommercial purposes only" and "produce, reproduce, and Share Adapted Material for NonCommercial purposes only". "Share" includes making material available to the public "from a place and at a time individually chosen by them".
- "Patent and trademark rights are not licensed under this Public License."
- **Creative Commons itself says**: "We recommend against using Creative Commons licenses for software ... CC licenses do not contain specific terms about the distribution of source code ... Many software licenses also address patent rights" ([CC FAQ](https://creativecommons.org/faq/)).
- Relevant to TART as a candidate for **archive data and content**, not for the code (a separate ticket's concern).

### Elastic License 2.0 (contrast only)

- "You may not provide the software to third parties as a hosted or managed service, where the service provides users with access to any substantial set of the features or functionality of the software."
- The restriction applies **regardless of payment**. Read literally, it could catch a community archive serving the public. **[Legal review]** if anything like it is considered.

## Comparison against README §6 criteria

Legend: ✅ the text expressly allows it · ⚠️ allowed only conditionally, or depends on interpretation · ❌ the text prohibits it or does not grant it · — the text does not address it.

| Criterion | PolyForm NC | PolyForm Shield | PolyForm Small Biz | BUSL 1.1 | Commons Clause (+Apache 2.0) | Prosperity 3.0.0 | CC BY-NC 4.0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Deploy independent local instance | ⚠️ yes for noncommercial purposes | ✅ unless it competes | ⚠️ yes if under the size thresholds | ❌ production use needs an Additional Use Grant | ✅ unless "Sell" | ⚠️ yes for noncommercial purposes | ⚠️ not designed for software |
| Modify and fork | ✅ for permitted purposes | ✅ (noncompete) | ✅ (size) | ✅ "modify, create derivative works" | ✅ base license | ✅ broad grant | ✅ Adapted Material, NC |
| Redistribute | ✅ with notices; no sublicensing | ✅ with notices | ✅ with notices | ✅ but the same BUSL applies to all copies and derivatives | ✅ base license, plus the clause | ✅ with notices | ✅ NC only |
| Hosted/SaaS | — no specific clause; it is a "use" that needs a permitted purpose | ❌ if competing (even free) | ✅ for small firms, including paid | ❌ without an Additional Use Grant | ❌ paid hosting "whose value derives ... substantially" from the software | — as PolyForm NC | — ("Share" may cover public availability) |
| Defines commercial use | ❌ undefined; safe harbors only | n/a (competition test) | n/a (size test) | n/a ("production use", undefined) | ✅ "Sell" defined | ❌ undefined; safe harbors only | ✅ "primarily intended for ... commercial advantage or monetary compensation" |
| Community organizations | ⚠️ listed types only (charitable, educational, etc.) | ✅ | ⚠️ size test | ⚠️ via the Additional Use Grant | ✅ unless selling | ⚠️ same list as PolyForm NC | ⚠️ "primarily intended" test |
| Infrastructure costs | — | — | — | — | ⚠️ cost recovery as a "fee" to third parties? | — | ⚠️ the "monetary compensation" wording |
| Contributor clarity | — no inbound terms | — | — | — | — | ⚠️ "Contributions Back" safe harbor | — |
| Enforceability features | 32-day cure; acceptance clause | same | same | automatic termination of all versions | base license + clause | irrevocable; 30-day cure for notices | 30-day reinstatement (§6(b)) |
| Powered by TART | — no attribution in the running UI | — | — | — | — (Apache NOTICE file only) | — | ⚠️ attribution when "Sharing" |
| Trademark | — "do not imply any other licenses" | — | — | ✅ expressly excluded | ✅ Apache 2.0 §6 excludes | — | ✅ expressly excluded |
| Permanence of the non-commercial limit | ✅ permanent | permanent noncompete | permanent | ❌ converts to a GPL-compatible license within 4 years | ✅ permanent | ✅ permanent | ✅ permanent |

## Criterion-by-criterion notes and interpretation points

### 1. Independent local deployments
- PolyForm NC and Prosperity allow them when the purpose is noncommercial. A community running a public archive with no revenue looks like the core case. **[Legal review]** It is unclear whether running a public website counts as a "personal use" or falls under the general "noncommercial purpose" clause, which has no definition.
- BUSL without an Additional Use Grant does **not** allow a production archive at all. TART would have to write an Additional Use Grant (for example, "production use for non-commercial purposes"). That is custom licensing text, which README §6 warns against. **[Legal review]**

### 2. Modification and forks
- All the candidates allow modification. PolyForm NC limits changes to "any permitted purpose", so a fork can only be used for noncommercial purposes.
- No candidate requires forks to share their source when hosted (see the cross-cutting facts).

### 3. Redistribution
- PolyForm (all variants): recipients must receive the terms and `Required Notice:` lines. No sublicensing. Each recipient is licensed under the same terms.
- BUSL: "All copies of the original and modified Licensed Work, and derivative works ... are subject to this License."
- Commons Clause: "Any license notice or attribution required by the License must also include this Commons Clause License Condition notice."

### 4. Hosted/SaaS
- §6 wants to bar *commercial* SaaS and commercial hosted instances while allowing community hosting.
- PolyForm NC and Prosperity reach that only indirectly: running SaaS for a commercial purpose is not a permitted purpose. **[Legal review]** It is unclear whether a paid, cost-covering hosting service run by a nonprofit for other communities is "commercial".
- Commons Clause targets paid hosting explicitly. Its "fee or other consideration" wording could catch cost-recovery arrangements between communities.
- ELv2's model (ban all hosted service to third parties) would conflict with community hosting.

### 5. Definition of commercial use
- PolyForm NC and Prosperity deliberately avoid a definition. They rely on the ordinary meaning plus safe harbors. This keeps the text short but leaves edge cases open.
- CC BY-NC uses a "primarily intended for or directed towards" test.
- Commons Clause uses a value-derivation test ("entirely or substantially").
- **[Legal review]** How Italian or EU courts would read an undefined "noncommercial" term in an English-language US-drafted license, and whether a translated text is needed.

### 6. Community organizations
- The PolyForm NC and Prosperity safe harbors list "charitable organization, educational institution, public research organization, public safety or health organization, environmental protection organization, or government institution". Cultural or heritage associations are **not listed**.
- **[Legal review]** Whether an Italian *associazione culturale*, APS or ETS (Third Sector entity), or an informal unregistered group counts as a "charitable organization". If not, their use falls back to the undefined "noncommercial purpose" test.
- The safe harbor applies "regardless of the source of funding". This helps grant-funded or municipally-funded archives.

### 7. Infrastructure costs
- No candidate mentions hosting or cost recovery.
- Paying a provider for hosting is the licensee *spending* money, which does not obviously make the use commercial.
- The open point is the reverse: an instance *charging* members or partner communities to cover costs. **[Legal review]** This applies under PolyForm NC and Prosperity (undefined term), CC BY-NC ("monetary compensation") and Commons Clause ("fee or other consideration").
- **Professional technical assistance (§6)**: under PolyForm NC and Prosperity, a paid contractor deploying TART for a community is arguably using the software for a commercial purpose. Commons Clause's text names "consulting/ support services" as restricted "Sell" activity, while its FAQ says consulting is allowed. **[Legal review]** in both cases. If needed, the LDR could look at an explicit permission or exception, but that moves toward custom terms.

### 8. Contributor clarity
- None of the candidates contains inbound contribution terms. Prosperity's "Contributions Back" clause only says that contributing is not commercial use. It does not grant the project rights.
- **Implication**: if outside contributions are accepted under the same non-commercial license (inbound = outbound), the project may not be able to relicense later, for example to an Open Source license, a BUSL-style Change License, or a different non-commercial license, without every contributor's consent. A CLA or DCO policy is a separate decision. **[Legal review]** for CLA drafting.
- BUSL assumes a single licensor that sells commercial licenses and sets the Change License. That fits a company better than a community project with many copyright holders.

### 9. Enforceability and practical interpretation
- PolyForm and Prosperity use "Acceptance"/"Agreement" clauses, which treat the terms as both contract and license conditions. **[Legal review]** How this works under Italian contract law (for example, rules on standard terms and acceptance formalities) and whether an Italian translation is needed.
- Cure periods: PolyForm 32 days; Prosperity 30 days (notices only) and "can't revoke"; CC 30 days (§6(b)); BUSL terminates automatically with no cure.
- Practical enforcement needs a licensor with standing, meaning a copyright holder. This links to contributor clarity and to who the "licensor" of TART is (individual, association, foundation). **[Legal review]**

### 10. "Powered by TART" model
- No candidate requires attribution to be shown in a running web application's UI. PolyForm notices travel with *copies*. Apache 2.0's NOTICE file (under Commons Clause) does too.
- CC BY-NC requires attribution when "Sharing", which might be read as covering public availability. CC itself discourages its use for software.
- So the "Powered by TART" line can't come from the software license alone. It would have to be a trademark-policy permission (allowing the mark) and/or a community norm. Making it **mandatory** through a license would mean adding terms, which moves toward a custom license. **[Legal review]**

### 11. Trademark interaction
- BUSL, CC BY-NC and Apache 2.0 (the Commons Clause base) expressly exclude trademark rights. PolyForm and Prosperity grant no trademark rights ("do not imply any other licenses"; Prosperity is silent).
- In every case, the TART name and logo would be governed by a separate trademark policy. That policy can allow "Powered by TART" while forbidding impersonation of the official project, as README §7 asks.
- Registering "TART" is a separate, open question. Note that the license names themselves are trademarks too: "Business Source License" (MariaDB) and "POLYFORM" (US application 88400646). Modifying those texts means dropping the names.

### 12. Third-party dependency compatibility
The decided ecosystem (map #2) and the upstream licenses as declared in each repository:

| Component | License (upstream) | Source |
| --- | --- | --- |
| FastAPI | MIT | <https://github.com/fastapi/fastapi> |
| PostgreSQL | PostgreSQL License (permissive) | <https://www.postgresql.org/about/licence/> |
| PostGIS | GPL-2.0-or-later (some bundled files MIT) | <https://github.com/postgis/postgis/blob/master/LICENSE.TXT> |
| MapLibre GL JS | BSD-3-Clause | <https://github.com/maplibre/maplibre-gl-js/blob/main/LICENSE.txt> |
| PMTiles (reference implementations) | BSD-3-Clause; spec public domain/CC0 | <https://github.com/protomaps/PMTiles/blob/main/LICENSE> |

- Permissive dependencies (MIT, BSD, PostgreSQL) can generally be combined with a non-commercial license for TART's own code, as long as their notices are kept. Their own terms continue to apply to them. The project cannot re-license third-party code as non-commercial.
- **GPL is the friction point.** GPLv2 §6 ("You may not impose any further restrictions on the recipients' exercise of the rights granted herein", <https://www.gnu.org/licenses/old-licenses/gpl-2.0.html>) and GPLv3 §10 (<https://www.gnu.org/licenses/gpl-3.0.html>) do not allow a work that is a GPL derivative to be distributed under non-commercial terms. PostGIS runs as a database extension that TART talks to over SQL; it is not linked into TART's code. **[Legal review]** Whether that keeps TART outside the GPL derivative-work boundary, and whether shipping PostGIS in TART's Docker Compose images is "mere aggregation".
- **AGPL/GPL dependencies in general**: a TART policy should screen dependencies for copyleft licenses that cannot sit under a non-commercial outbound license. Combining Commons Clause with a GPL/AGPL base is especially problematic: GPLv3 §7 lets recipients remove "further restrictions".
- **BUSL-specific**: the Change License must be GPLv2+-compatible, so after conversion TART would become ordinary GPL-compatible software. That is consistent with GPL dependencies but ends the non-commercial restriction.

## Fit against the §6 intent (facts, not a recommendation)

| §6 requirement | Where the texts line up | Where they diverge |
| --- | --- | --- |
| Permanent ban on commercial exploitation | PolyForm NC, Prosperity, CC BY-NC, Commons Clause (selling only) | BUSL converts within ≤4 years. Shield and Small Business allow some commercial use. Prosperity allows a 30-day commercial trial. |
| Free community deployment, modification, forks | PolyForm NC, Prosperity, Commons Clause | BUSL needs a custom Additional Use Grant. |
| Explicit ban on commercial SaaS/hosting | Commons Clause (paid hosting) | PolyForm NC and Prosperity only implicitly (through the undefined "noncommercial"). |
| Paid professional assistance allowed | Commons Clause FAQ (but its text says otherwise) | PolyForm NC and Prosperity are unclear. |
| Software-specific, established, unmodified text | PolyForm, Prosperity, BUSL | CC BY-NC is discouraged for software by CC itself. Commons Clause depends on a base license. |

**Documented gap**: no standard license examined *expressly* allows paid technical assistance and community cost recovery *and* expressly bars commercial SaaS while keeping the non-commercial limit permanent. README §6 says that in this case the gap should be recorded and legal review recommended before writing any custom terms.

## Open points for professional legal review (summary)

1. How "noncommercial" (undefined) in PolyForm NC and Prosperity is interpreted under Italian and EU law, and whether an Italian translation or governing-law note is needed.
2. Whether Italian cultural associations, APS/ETS, and informal groups fall under "charitable organization" or the general noncommercial purpose.
3. Whether instances charging cost-recovery fees, and contractors paid to deploy or maintain TART, are commercial use under each candidate.
4. Whether a BUSL Additional Use Grant phrased as "non-commercial production use" would work, and whether its time-limited conversion fits the project's intent.
5. The GPL boundary for PostGIS (and any future copyleft dependency) under a non-commercial outbound license, including Docker image distribution.
6. Contributor inbound terms (CLA vs. DCO) and who acts as licensor and enforces the license.
7. How a trademark policy can permit "Powered by TART" while preventing impersonation, and whether "TART" can or should be registered.
8. Enforceability of "Acceptance"-style terms under Italian contract law.

## Possible follow-up questions (not resolved here)

- **Contributor inbound policy** (CLA/DCO) and the identity of the licensor entity.
- **TART trademark policy** and "Powered by TART" usage rules.
- **Dependency license policy** (allow and deny lists, GPL/AGPL screening) for the chosen stack.
- **Licensing of archive data and user content** (for example, CC BY-NC vs. CC BY-SA vs. ODbL for data). This is separate from the software license per README §7.
