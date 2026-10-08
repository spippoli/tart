# Research: archive data and contributor content licensing, GDPR

- **Ticket**: [#8](https://github.com/spippoli/tart/issues/8), part of the MVP specification map [#2](https://github.com/spippoli/tart/issues/2)
- **Date**: 2026-10-08
- **Status**: research input, not a decision. Decisions belong to the "Content rights and GDPR product rules" ticket.
- **Not legal advice.** Every point marked **[legal review]** needs a qualified lawyer (Italian copyright and EU data protection) before it becomes a product rule.

Domain terms (Instance, Archive record, Documentation item, Source, Submission, Submitter, User, Artist, Withdrawal, Observed date) are used as defined in [`GLOSSARY.md`](../../GLOSSARY.md).

## Question

1. What licences fit **(a)** structured archive data and **(b)** contributor Documentation items (photos, PDFs, text)? Per-upload choice or one required licence? Uploader vs photographer attribution?
2. How do comparable projects (Wikimedia Commons, Wikidata, OpenStreetMap, Europeana, street-art platforms) handle this?
3. What GDPR obligations apply to a community archive for account deletion, data export, contributions by deleted Users, and EXIF/location metadata?

## Summary

- **Four separate rights layers** sit on a single Documentation item: the artwork's copyright (the Artist), the photo's copyright or related right (the photographer, who is not necessarily the Submitter), the data protection rights of identifiable people (Submitters, Artists, bystanders), and the Instance's database right over the archive as a whole. A contributor licence can only cover the rights the contributor actually holds.
- **Italy has no freedom of panorama.** A photo of an in-copyright mural is a reproduction of the artwork, and the Submitter's licence cannot clear that. This is the largest legal risk for the archive, and it is not specific to TART. **[legal review]**
- **Structured data**: the realistic candidates are CC0, CC BY 4.0, CC BY-SA 4.0 and ODbL 1.0. Of the CC licences, only version 4.0 explicitly licenses EU sui generis database rights. CC0 maximises reuse (Wikidata, Europeana). ODbL keeps share-alike and matches OSM. A non-commercial (NC) data licence would fit TART's ethos but would cut the data off from Wikimedia and OSM.
- **Documentation items**: there are three models. In the first, one licence is required (simple, and Commons-compatible if it is CC BY or CC BY-SA). In the second, the Submitter chooses from a per-upload allowlist (the Commons model). In the third, the Submitter grants a display-only licence to the Instance and keeps all other rights (the most contributor-friendly, but nothing is reusable). The licence choice should be per Instance configuration, not hardcoded.
- **The credit line is not the User account.** CC 4.0 attribution follows the creator, can use a pseudonym, and must be removed on request. Storing the credit (photographer name or pseudonym) separately from the Submitter's account lets accounts be deleted without breaking licence compliance.
- **GDPR, account deletion**: the dominant pattern (OSM) is to pseudonymise the account, keep the contributions under a generated name, and delete profile content. Pseudonymised data is still personal data under Recital 26. Keeping contributions needs a lawful basis and possibly an Art. 17(3) exception. Whether a private community archive can rely on the "archiving in the public interest" exception (Art. 17(3)(d), Recital 158) is uncertain. **[legal review]**
- **EXIF GPS is personal data.** It records the photographer's position, which is distinct from the artwork's Location. Data minimisation (Art. 5(1)(c)) and privacy by design (Art. 25) argue for stripping it from published files. The capture date can be offered as a suggested Observed date before stripping.
- **New risks surfaced**: Artist records about identifiable people, attributions of unauthorised graffiti (possibly "offence" data under Art. 10 GDPR), bystander portraits (Art. 96 L. 633/1941), the Digital Services Act notice-and-action duties for hosting providers, and the age of digital consent (14 in Italy, and it varies per Instance).

---

## 1. The rights layers on a Documentation item

| Layer | Holder | Source of the right | Effect of a contributor licence |
|---|---|---|---|
| Artwork | Artist (a person, often pseudonymous) | Italian copyright law, L. 633/1941. Moral rights (paternity and integrity, art. 20) are inalienable (art. 22). | None. The Submitter cannot license it. |
| Photograph (creative) | Photographer | L. 633/1941 art. 2(7) (photographic works) | Licensable by the photographer only |
| Photograph ("simple photograph") | Photographer | L. 633/1941 art. 87 ff., a related right lasting 20 years (art. 92) | Licensable by the photographer only |
| Portrait of identifiable people | The people depicted | L. 633/1941 art. 96–97, and the GDPR | Not covered by any copyright licence. CC 4.0 explicitly excludes privacy and publicity rights (§2(b)). |
| Archive as a database | The Instance operator, as "costitutore" | L. 633/1941 art. 102-bis (EU Directive 96/9/EC) | Licensed by the Instance's data licence |

Sources: L. 633/1941 consolidated text ([InterLex](https://www.interlex.it/testi/l41_633.htm); official text on [Normattiva](https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:legge:1941-04-22;633)); [CC BY-SA 4.0 legal code](https://creativecommons.org/licenses/by-sa/4.0/legalcode.en).

Relevant Italian details:

- **Simple photographs (art. 87–92)**: art. 87 covers images of people, objects and events obtained by a photographic process, including reproductions of figurative art. The exclusive right lasts 20 years from production (art. 92). Art. 90 lists the indications that copies should carry: the photographer's name, the date, and, for photos of artworks, the name of the author of the artwork photographed. Where those indications are missing, reproduction is not considered unlawful unless the photographer proves bad faith. This argues for credit fields covering both the photographer and the artwork's Artist. Whether a given street-art photo is a "creative" or a "simple" photograph is case by case, and Commons calls the distinction "rather vague" ([Commons: Italy](https://commons.wikimedia.org/wiki/Commons:Copyright_rules_by_territory/Italy)).
- **Database right (art. 102-bis)**: the "costitutore" is whoever makes a substantial investment in building the database. Here that is most plausibly the Instance operator, not individual contributors. **[legal review]**: who is the costitutore for a volunteer-built archive, and does a community association qualify?

## 2. Freedom of panorama and artwork reproduction in Italy

- Wikimedia Commons marks Italy as **"Not OK"** for freedom of panorama in every category (buildings, 3D art, 2D art). It notes that "pictures from public places don't formally enjoy any exception in Italian copyright law", and that objects still under copyright only allow the quotation right of art. 70 ([Commons: Italy](https://commons.wikimedia.org/wiki/Commons:Copyright_rules_by_territory/Italy); [Commons: Freedom of panorama](https://commons.wikimedia.org/wiki/Commons:Freedom_of_panorama)).
- **Art. 70(1)** of L. 633/1941 permits summary, quotation or reproduction of parts of a work for criticism, discussion or teaching, provided it does not compete with the economic use of the work. Whether a documentary archive reproducing whole murals fits this exception is untested here. **[legal review]**
- **Art. 70(1-bis)** allows free online publication, without charge, of low-resolution or degraded images for teaching or scientific use, and only where that use is non-profit. Commons calls it "minimal and never implemented", because the implementing decree was never adopted. It looks tailor-made for a non-profit archive but cannot be relied on without advice. **[legal review]**
- Commons' general rule: "photographs of the unauthorized derivative work should not be uploaded" ([Commons: Freedom of panorama](https://commons.wikimedia.org/wiki/Commons:Freedom_of_panorama)). In practice, Commons cannot host photos of most living artists' Italian murals. This limits any plan to mirror TART media to Commons.
- **Cultural heritage code** (D.Lgs. 42/2004, arts. 107–108): photos of cultural heritage assets can need authorisation and fees for commercial use. Commons advises assuming older works may be heritage assets. Most street art will not qualify, but old or listed murals might. **[legal review]**
- I found no primary source settling whether unauthorised (illegal) graffiti attracts copyright in Italy. It is commonly assumed that it does, since originality and not legality is the test, but this was not verified here. **[legal review]**

Product implication (not a decision): the **Withdrawal** mechanism is the natural channel for takedown requests from Artists and rights holders. The rights posture (for example: non-commercial, documentary purpose, attribution of the Artist, prompt Withdrawal on request) should be stated in the Instance's terms.

## 3. Licensing options for structured archive data

What "data" covers: Archive records (Artwork, Artist, Location, Site, Series, Area), History events, Attributions and Source citations. It does not cover Documentation item files. Free-text descriptions are a grey zone. Wikidata licenses structured data under CC0 and text under CC BY-SA, so a split licence is possible.

| | CC0 1.0 | CC BY 4.0 | CC BY-SA 4.0 | ODbL 1.0 (+ contents licence) | A "-NC" variant (CC BY-NC(-SA) 4.0) |
|---|---|---|---|---|---|
| Covers EU sui generis database right | Waives it | Yes, explicitly (§4) | Yes, explicitly (§4) | Yes, the core purpose | Yes (§4) |
| Attribution required | No (can be requested in usage guidelines) | Yes | Yes | Yes (notice) | Yes |
| Share-alike | No | No | Yes, for adapted material | Yes, for derivative databases (§4.4). "Produced works" (e.g. maps) need only a notice (§4.3, §4.5). | Optional |
| Commercial reuse | Allowed | Allowed | Allowed | Allowed | Prohibited |
| Covers contents individually | n/a | Yes | Yes | **No**: the database only. Contents need a separate licence (OSM pairs it with DbCL). | Yes |
| Accepted by Wikidata / Commons | Wikidata: yes (CC0 only). Commons: yes. | Commons: yes. Wikidata: no. | Commons: yes. Wikidata: no. | Neither | Neither (Commons rejects NC) |
| Used by | Wikidata, Europeana metadata | Many open-data portals | Wikipedia text, Street Art Cities images | OpenStreetMap | Not by any comparable open project |

Sources: [CC BY-SA 4.0 legal code](https://creativecommons.org/licenses/by-sa/4.0/legalcode.en) (§1(12) definition of Sui Generis Database Rights, §2(b), §3, §4); [CC wiki: Data](https://wiki.creativecommons.org/wiki/Data) (CC 4.0 covers sui generis rights; CC0 recommended to maximise reuse; advises against NC/ND for scholarly databases); [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/) (Preamble, §2.4, §4.2–4.7); [Wikidata: Licensing](https://www.wikidata.org/wiki/Wikidata:Licensing); [Commons: Licensing](https://commons.wikimedia.org/wiki/Commons:Licensing); [Europeana Data Exchange Agreement](https://pro.europeana.eu/page/the-data-exchange-agreement) (metadata published under CC0; the page returned HTTP 403 to automated fetch, so the content is corroborated by [Creative Commons' 2011 announcement](https://creativecommons.org/2011/09/22/europeana-adopts-new-data-exchange-agreement-all-metadata-to-be-published-under-cc0/)).

Trade-offs to weigh:

- **CC0** gives maximum reuse and interoperability with Wikidata, so artwork records could become Wikidata items. It gives up any legal hold on attribution and on commercial reuse of the data. Europeana and Wikidata both chose it deliberately for metadata.
- **CC BY-SA 4.0 / ODbL** keep derivatives open. ODbL's split between database and contents is precise but adds complexity: a second licence for the contents, plus the "produced work" rules. ODbL §4.6 also requires anyone publicly using a derivative database to offer a machine-readable copy, which implies TART should offer a data dump anyway.
- **NC licences** would mirror the non-commercial software intent, but the CC wiki advises against them for scholarly data, and Commons and Wikidata reject them. Note that the software licence and the data licence are separate concerns (brief §7). Nothing forces them to match.
- **Multi-instance**: the data licence should be an **Instance configuration value** with a platform default. Federation or aggregation of several Instances' data (e.g. a future "all TART archives" view) is only frictionless if the licences are compatible. **[legal review]** CC BY-SA 4.0 ↔ ODbL compatibility is not established. Neither is listed as compatible with the other.
- **OSM base map**: if the map uses OSM-derived tiles (PMTiles), every Instance must display OSM attribution and make clear that the data is under ODbL ([OSM copyright](https://www.openstreetmap.org/copyright)). Rendered tiles count as an ODbL "produced work": a notice is enough, and archive data shown on top is not infected. Copying OSM geometries (e.g. building outlines) into Location records, however, would arguably create a derivative database under ODbL §4.4. **[legal review]** if Locations are ever traced from OSM.

## 4. Licensing options for Documentation items

### Models

| Model | Example | Pros | Cons |
|---|---|---|---|
| **A. Single required free licence** (e.g. CC BY-SA 4.0) | [Street Art Cities](https://streetartcities.com/terms) (images and descriptions under CC BY-SA 4.0, creators keep ownership); Wikipedia text ([WMF Terms of Use §7](https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use)) | Simple UX, predictable reuse, Commons-compatible licence | Excludes contributors who will not license freely. Does not cover third-party material (newspaper scans, archive photos). |
| **B. Per-upload choice from an allowlist** | [Wikimedia Commons](https://commons.wikimedia.org/wiki/Commons:Licensing) (CC0, CC BY, CC BY-SA and others; NC/ND rejected) | Respects contributor preference, mixes own work and public-domain material | More UX and moderation burden. Per-item licence display and filtering needed. |
| **C. Licence to the Instance only** (non-exclusive, perpetual, display/archive licence; all other rights reserved) | Common platform pattern | Lowest barrier for contributors | Nothing reusable by third parties, so it undermines archival preservation (no one else can legally mirror the archive if the Instance dies) |
| **D. Hybrid**: A or B for own work, plus an "external material" path | Commons' VRT permission process for third-party works | Covers press clippings and historical photos | Needs a permission workflow, or a rule that third-party material is linked as a **Source**, not uploaded |

Observations:

- **Irrevocability**: CC 4.0 licences are irrevocable (§2(a)(1)). WMF's Terms of Use make contributors agree not to revoke. The licence therefore survives account deletion. GDPR rights over personal data in the item (e.g. a face) are a separate matter (§5).
- **Attribution mechanics**: CC 4.0 §3(a)(1)(A)(i) lets the creator be credited "including by pseudonym if designated", and §3(a)(3) requires reusers to remove attribution information **if requested by the Licensor**. OSM's [Contributor Terms](https://osmfoundation.org/wiki/Licence/Contributor_Terms) make attribution optional at the contributor's choice, via a contributors page.
- **Uploader vs photographer**: Commons requires the description page to state the source, the author and the licence, and only the copyright holder can license ([Commons: Licensing](https://commons.wikimedia.org/wiki/Commons:Licensing)). A data model with distinct **Submitter** (the User), **creator/credit** (free text: photographer name or pseudonym), **licence**, and **rights basis** (own work / permission / public domain / link only) mirrors this. It also satisfies art. 90 L. 633/1941, which expects the photographer's name, the date, and the photographed artwork's author.
- **Warranties**: OSM (§1a) and Commons both require contributors to confirm they hold the rights. OSM reserves the right to remove any contribution (§1b). The equivalent here is the Withdrawal of a Documentation item.
- **Artwork rights are untouched** by any model (see §2). Licence badges should not imply that the artwork itself is reusable. **[legal review]**: wording of the licence notice for photos of in-copyright artworks.
- Street Art Cities also claims an exclusive licence over the metadata its users contribute (§9.2 of its terms, as read via automated fetch; not independently verified). This is the opposite of the open-data approach above.
- I found no published licensing policies for other street-art archives that were authoritative enough to cite. Only Street Art Cities' terms were readable.

## 5. GDPR obligations

Primary text: [Regulation (EU) 2016/679 on EUR-Lex](https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32016R0679). Italian implementation: D.Lgs. 196/2003 as amended by D.Lgs. 101/2018 (Codice privacy).

### Who is the controller

Each **Instance operator** is the controller (Art. 4(7)) of its Users' data and of personal data in its archive (consistent with ADR 0001, one Instance per deployment). The TART project is not a controller of Instance data unless it hosts Instances. In that case a processor agreement (Art. 28) would be needed. The platform can only *enable* compliance: it supplies the features, the defaults and template texts. Drafting the privacy policy is out of scope (map #2).

### Personal data in an archive like TART

- **User accounts and Submissions**: email, username, IP/log data, and the Submitter's identity on each Revision.
- **Artist records**: an Artist is a "public identity, never a legal identity" (GLOSSARY). An Alias that can be linked to a natural person is still personal data (Art. 4(1); pseudonymised data stays personal data under Recital 26).
- **Documentation items**: faces and licence plates of bystanders, and EXIF metadata. Art. 4(1) names "location data" explicitly as an identifier.
- **Attributions of unauthorised works**: imbrattamento (defacement) is an offence under Italian criminal law, so stating that an identifiable person made an illegal piece may count as data "relating to criminal convictions and offences" (Art. 10), which may only be processed under official authority or where Union or Member State law authorises it. This was not settled by any source found. **[legal review]**, and a strong candidate for a product rule (e.g. Attributions name the Artist's public identity only, and never link Alias to legal name).

### Lawful bases (Art. 6) and the expression and archiving regimes

- Account and contribution handling: Art. 6(1)(b) contract (terms of service) and/or 6(1)(f) legitimate interest. OSM retains contributor data on a legitimate-interest basis ([OSMF Privacy Policy](https://osmfoundation.org/wiki/Privacy_Policy)).
- Archive content about Artists and third parties: likely 6(1)(f), possibly together with the **Art. 85** freedom-of-expression regime. Italy implements this in Codice privacy **art. 136 ff.**, which covers publication of "articoli, saggi e altre manifestazioni del pensiero anche nell'espressione accademica, artistica e letteraria" (text via [Brocardi](https://www.brocardi.it/codice-della-privacy/parte-ii/titolo-xii/capo-i/art136.html)). Recital 153 frames this as balancing data protection against freedom of expression.
- **Archiving in the public interest** (Art. 89, Recital 158): Recital 158 describes bodies that hold records of public interest and, under Union or Member State law, have a duty to acquire, preserve and give access to records of enduring value. The Garante's *Regole deontologiche* for archiving and historical research (provvedimento n. 513 of 19 Dec 2018, GU n. 12 of 15 Jan 2019, doc. web 9069661) apply to archives of public bodies and to private archives *declared of notable historical interest* ([summary](https://www.diritto.it/?p=62243)). A volunteer urban-art archive is probably **not** in scope by default. It is still a useful benchmark. **[legal review]**
- Consent (6(1)(a)) is a fragile basis for archive content, because withdrawal triggers erasure under Art. 17(1)(b).

### Account deletion and contributions by deleted Users

- **Art. 17(1)** right to erasure. **Art. 17(3)** exceptions include (a) exercising freedom of expression and information, (d) archiving in the public interest, scientific or historical research or statistics per Art. 89(1), insofar as erasure would make the purpose impossible or seriously impair it, and (e) legal claims.
- **Comparable practice (OSM)**: on deletion, the account is renamed to a user-ID-based name, and "contributions and changeset comments will be retained with this name". Diary entries and the user page are removed. The email address is kept non-publicly so the contributor can be contacted about their contributions. Accounts with no contributions are deleted outright ([OSMF Privacy Policy](https://osmfoundation.org/wiki/Privacy_Policy)). WMF's Terms of Use say public contributions are unaffected by account termination ([§13](https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use)).
- Implications for TART (options, not decisions):
  - Keep Revisions and approved content, but replace the Submitter with a pseudonym. This preserves the audit trail (ADR 0002) without exposing identity. Recital 26 means the pseudonym is still personal data while any re-identification key, such as a retained email, exists.
  - Delete outright: unapproved drafts, rejected Submissions, profile text, and moderation notes that are not needed as evidence (retention period to define).
  - The photographer **credit line** on a Documentation item is licence compliance data, not account data. If the photographer asks to be uncredited, CC 4.0 §3(a)(3) supports removing it. A credit linked to the account could instead fall back to "anonymous contributor".
  - Personal data *inside* Documentation items (a face, a name written in a text) is handled per item via Withdrawal or redaction. Account deletion does not resolve it.
  - **[legal review]**: whether retaining a deleted User's contributions can rest on legitimate interest or Art. 17(3)(a), given that the 17(3)(d) public-interest archiving exception may not be available.

### Data export

- **Art. 15** (access, with a copy of the data) applies always. **Art. 20** (portability) covers data the person *provided*, processed by automated means on the basis of consent or contract, in a structured, commonly used, machine-readable format. **Art. 20(4)**: it must not adversely affect the rights and freedoms of others.
- Practical scope: profile, Submissions (including the Documentation item files the User uploaded), comments and Submission statuses, exported as JSON plus the original files. Excluded or redacted: other Users' identities, Moderators' internal notes where disclosure would affect others (Art. 15(4) for copies, Art. 20(4)). **[legal review]** on how much of the moderation history is disclosable.
- ODbL §4.6 and general archival-preservation goals point to a separate, Instance-level **public data dump**, distinct from the personal export.

### EXIF and location metadata

- GPS coordinates in EXIF give the **photographer's** position at capture time. They are personal data (Art. 4(1) "location data"). They are also not the artwork's Location (CLAUDE.md invariant: the artwork location is not the submitter's location).
- Art. 5(1)(c) (data minimisation) and Art. 25 (data protection by design and by default) favour stripping GPS, device serial numbers and owner fields from **published** files by default.
- Comparable practice: Commons does **not** strip EXIF. It hides GPS behind "show extended details", some upload tools turn EXIF GPS into a visible `{{Location}}` template, and it points users to third-party tools to strip metadata themselves ([Commons: Exif](https://commons.wikimedia.org/wiki/Commons:Exif)). OSM leaves GPS traces to users to trim before upload ([OSMF Privacy Policy](https://osmfoundation.org/wiki/Privacy_Policy)). Both put the burden on the user. A server-side default is stronger privacy by design.
- Design options: (1) strip on ingest and keep nothing; (2) read EXIF client-side to *suggest* an Observed date and a starting point for the Location pin (which the Submitter must confirm), then strip before upload; (3) keep the original privately for moderation evidence and publish a stripped derivative. Option (3) creates retention and access obligations.
- EXIF copyright/artist fields can pre-fill the credit line. Licence information embedded in EXIF is retained by Commons and is useful for reusers.

### Other obligations that surfaced

- **Age of digital consent**: Art. 8 sets 16 with a national floor of 13. **Italy sets 14** (Codice privacy art. 2-quinquies). This must be an **Instance configuration value**, because it differs per Member State. It only matters where consent is the basis. **[legal review]** whether registration relies on consent at all.
- **Information duties**: Art. 13 for Users. Art. 14 for people described but not asked (Artists, people in photos). Art. 14(5)(b) relieves the duty where informing would be impossible or involve disproportionate effort, notably for archiving and historical research under Art. 89(1). Its applicability is tied to the archiving question above. **[legal review]**
- **Portrait rights** (L. 633/1941 art. 96–97): a person's portrait may not be shown without consent unless justified, for example by notoriety, public events, or scientific, didactic or cultural purposes. These rights run in parallel with the GDPR. A blur/redaction rule for bystanders needs a decision.
- **Records of processing (Art. 30), breach notification (Art. 33–34), DPO (Art. 37)**: a small Instance is unlikely to need a DPO (no large-scale systematic monitoring). Art. 30's under-250-employees exemption does not apply to processing that is not occasional, so records of processing are probably needed. **[legal review]**
- **Digital Services Act** (Regulation (EU) 2022/2065, [EUR-Lex](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32022R2065)): an Instance hosting user uploads is a hosting service. Notice-and-action (Art. 16) and statements of reason (Art. 17) apply to all hosting providers. Micro and small enterprises are exempt from the additional online-platform duties (Art. 19). Pre-moderation may affect the hosting liability exemption (Art. 6) and the "no general monitoring" framing. **Not researched in depth.** See the open questions.

## 6. Points needing professional legal review

1. Reproducing photos of in-copyright street art without freedom of panorama: can art. 70(1) quotation or (1-bis) cover a non-profit documentary archive, and what notice and takedown posture reduces risk?
2. Copyright status of unauthorised graffiti in Italy.
3. Who holds the art. 102-bis database right in a volunteer-built archive, and therefore who licenses the data.
4. Licence compatibility for any cross-Instance aggregation (CC BY-SA 4.0 vs ODbL vs CC0), and the use of OSM-derived geometries.
5. Whether attributing unauthorised works to identifiable people is Art. 10 GDPR offence data, and what that requires.
6. The lawful basis for retaining a deleted User's contributions, and whether any Art. 17(3) exception applies to a private community archive.
7. Scope of disclosure of moderation history in access and portability requests.
8. Wording of licence notices so they do not imply rights in the artwork.
9. DSA status of an Instance and its interaction with pre-moderation.

## 7. Open questions that may deserve their own ticket

- **Digital Services Act and notice-and-action**: Instance obligations as a hosting provider, and how Withdrawal requests from rights holders, Artists and data subjects map onto DSA Art. 16–17.
- **Personal data in Artist records**: rules for Aliases, never storing legal names, and handling Artist requests (object, rectify, withdraw), as distinct from the user–artist claim question already on the map.
- **Bystander privacy in Documentation items**: blur/redaction policy and tooling, and whether moderation requires it before approval.
- **Instance-level public data dump and preservation**: format, cadence and licence notice, so an archive can outlive its Instance.

## Sources

- Creative Commons, [CC BY-SA 4.0 legal code](https://creativecommons.org/licenses/by-sa/4.0/legalcode.en); [CC wiki: Data](https://wiki.creativecommons.org/wiki/Data)
- Open Data Commons, [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/)
- OpenStreetMap Foundation, [Contributor Terms](https://osmfoundation.org/wiki/Licence/Contributor_Terms); [Privacy Policy](https://osmfoundation.org/wiki/Privacy_Policy); [Copyright and Licence](https://www.openstreetmap.org/copyright)
- Wikimedia, [Commons: Licensing](https://commons.wikimedia.org/wiki/Commons:Licensing); [Commons: Freedom of panorama](https://commons.wikimedia.org/wiki/Commons:Freedom_of_panorama); [Commons: Copyright rules by territory/Italy](https://commons.wikimedia.org/wiki/Commons:Copyright_rules_by_territory/Italy); [Commons: Exif](https://commons.wikimedia.org/wiki/Commons:Exif); [Wikidata: Licensing](https://www.wikidata.org/wiki/Wikidata:Licensing); [WMF Terms of Use](https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use)
- Europeana, [Data Exchange Agreement](https://pro.europeana.eu/page/the-data-exchange-agreement); Creative Commons, [Europeana adopts CC0 for metadata (2011)](https://creativecommons.org/2011/09/22/europeana-adopts-new-data-exchange-agreement-all-metadata-to-be-published-under-cc0/)
- Street Art Cities, [Terms](https://streetartcities.com/terms)
- EU, [GDPR (Regulation 2016/679)](https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32016R0679); [Digital Services Act (Regulation 2022/2065)](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32022R2065)
- Italy, L. 22 aprile 1941 n. 633 ([Normattiva](https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:legge:1941-04-22;633), [InterLex consolidated text](https://www.interlex.it/testi/l41_633.htm)); Codice privacy art. 136 ([Brocardi](https://www.brocardi.it/codice-della-privacy/parte-ii/titolo-xii/capo-i/art136.html)); Garante, Regole deontologiche per archiviazione e ricerca storica, provv. n. 513/2018 (doc. web 9069661)

Method note: the GDPR article texts for Art. 4(1), 10, 14(5)(b), 17(3)(d) and 89(1) are cited from the EUR-Lex consolidated text, but automated fetching returned only partial extracts. The article numbers and wording should be re-checked against EUR-Lex when they are turned into product rules.
