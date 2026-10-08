# Research: Digital Services Act duties for an archive Instance

Ticket: [#19](https://github.com/spippoli/tart/issues/19). Surfaced by [#8](https://github.com/spippoli/tart/issues/8) (`docs/research/data-content-licensing-gdpr.md` on branch `research/data-content-licensing-gdpr`).
Date: 2026-10-08. Status: research, not a decision. The product rules belong to [#14](https://github.com/spippoli/tart/issues/14) ("Content rights and GDPR product rules").

**Not legal advice.** Points marked **[legal review]** need a qualified lawyer, ideally one familiar with Italian law and AGCOM practice.

Article numbers refer to Regulation (EU) 2022/2065 (the Digital Services Act, DSA) unless stated otherwise. The DSA applies in full from 17 February 2024 (Art. 93(2)).

---

## Summary

- **Who the "provider" is.** The DSA attaches to whoever operates an Instance, not to the TART software project. Each Instance operator is a separate provider, supervised by the Digital Services Coordinator (DSC) of the Member State where it is established (Art. 56(1)). For Rome, assuming an Italian operator, that is **AGCOM**.
- **Is an Instance in scope at all?** The DSA covers "information society services", meaning services "normally provided for remuneration" (Recital 5, Directive 2015/1535). The CJEU reads this broadly: the remuneration need not come from the user (*Papasavvas*, C‑291/13, paras 28–29), and a free service can qualify when it is part of an economic activity (*Mc Fadden*, C‑484/14, paras 41–43). The Commission designated **Wikipedia (Wikimedia Foundation, a non-profit)** as a very large online platform. Whether a purely volunteer archive with no revenue, ads or fees is an information society service is genuinely uncertain. **[legal review]** The safe working assumption is that an Instance **is in scope as a hosting service**.
- **Duties that apply regardless of size** (all intermediary services plus hosting, Chapter III Sections 1–2):
  - Art. 11: a point of contact for authorities. AGCOM asks Italian providers to notify it to `dsa@agcom.it`.
  - Art. 12: a point of contact for users.
  - Art. 14: terms and conditions that describe moderation policy, including human review and complaint handling.
  - Art. 9–10: comply with authority orders and inform the affected user.
  - **Art. 16: notice and action.**
  - **Art. 17: statement of reasons.**
  - Art. 18: report suspected threats to life or safety to the police.
- **Duties a small Instance is exempt from.**
  - Art. 15 transparency reports: exempt for micro and small enterprises (Art. 15(2)).
  - All "online platform" duties in Section 3 (Art. 19), except answering a DSC's request for user numbers (Art. 24(3)). The exempt duties are internal complaint handling (Art. 20), out-of-court dispute settlement (Art. 21), trusted-flagger priority (Art. 22), misuse suspensions (Art. 23), the Commission's statements-of-reasons database (Art. 24(5)), the dark-pattern ban (Art. 25), advertising rules (Art. 26), recommender transparency (Art. 27) and minor-protection duties (Art. 28).
  - **Catch 1:** the exemption is defined through Commission Recommendation 2003/361/EC, which counts as an "enterprise" any entity engaged in an economic activity. An entity is in DSA scope only if it provides a service "normally provided for remuneration", so an in-scope Instance can probably claim the exemption, but the text is not explicit. **[legal review]**
  - **Catch 2:** an entity 25 % or more controlled by public bodies is never an SME (Recommendation Annex, Art. 3(4)). If a municipality, public university or public museum runs an Instance, Section 3 applies in full if the Instance is an online platform.
- **Moderation before publication and the hosting exemption (Art. 6).**
  - The exemption covers only providers that act "neutrally" and have no "knowledge of, or control over" the information (Recital 18; *L'Oréal v eBay*, C‑324/09, paras 113–116; *YouTube and Cyando*, C‑682/18, paras 105–106, 109).
  - TART's model has Moderators view, select and approve every Submission as part of an *authoritative* archive. That looks like the "active role" and "editorial responsibility" the case law excludes (*Papasavvas*, para 45).
  - Art. 7 protects good-faith measures aimed at **illegal content** only. Recital 26 adds that such measures do not by themselves guarantee the exemption.
  - Likely result: pending Submissions are hosted content, but **approved Archive records may not benefit from the Art. 6 exemption**, so the Instance operator could be directly liable under national law (copyright, defamation, portrait rights) for what it approves. The DSA does not itself create that liability (Recital 17). **[legal review]**
  - Separately, the CJEU held in *Russmedia* (C‑492/23, 2 December 2025) that the hosting exemption **cannot be invoked against GDPR obligations**. A platform operator acting as controller must screen user content for sensitive data **before** publication.
- **Product implications** (for #14 to decide):
  - A public "report" (notice) mechanism on every Archive record and Documentation item that does not require login, captures the Art. 16(2) elements, sends a receipt, and notifies the reporter of the decision.
  - Withdrawal as the DSA "action", with a structured Art. 17 statement of reasons sent to every affected Submitter.
  - Statement-of-reasons-grade rejection messages for Submissions.
  - Instance configuration for contact points and terms.
  - Records detailed enough to produce a transparency report if one is ever needed.

---

## 1. Is an Instance a provider in scope?

### 1.1 Hosting service, and maybe an online platform

- A **hosting** service is "the storage of information provided by, and at the request of, a recipient of the service" (Art. 3(g)(iii)). An Instance stores Submissions, Documentation items (images, PDFs, text) and profile data supplied by Users, so it is a hosting service.
- An **online platform** is a hosting service that "at the request of a recipient of the service, stores and disseminates information to the public" (Art. 3(i)). "Dissemination to the public" means making it available "at the request of the recipient of the service who provided the information" to a potentially unlimited number of people (Art. 3(k)). Recital 14 adds that dissemination counts "only where that dissemination occurs upon the direct request by the recipient of the service that provided the information."
  - On a TART Instance, publication happens only after a Moderator approves it. It is arguable that publication then results from the Instance's decision, not the Submitter's "direct request", so the Instance would be a hosting service but not an online platform. It is equally arguable that the Submitter asks for publication and approval is just a gate. **[legal review]**
  - For a small, non-public-body Instance the question matters little, because Art. 19 removes the platform-only duties anyway (§3). It matters if an Instance is publicly controlled or grows.
- Recital 13 says a feature that is "minor and purely ancillary" to an editorial service (its example is newspaper comments) does not make the service an online platform. User contributions are TART's principal function, so this carve-out is unlikely to help.

### 1.2 The "normally provided for remuneration" threshold

- The DSA covers providers of information society services as defined in Directive (EU) 2015/1535: "any service normally provided for remuneration, at a distance, by electronic means and at the individual request of a recipient" (Recital 5).
- The CJEU has held that remuneration need not come from the recipient (*Papasavvas*, C‑291/13, paras 28–29, citing Recital 18 of the e-Commerce Directive). A free service is covered when it is provided "within the course of [an] economic activity", for example as advertising for the provider's goods or services (*Mc Fadden*, C‑484/14, paras 41–43). The *Mc Fadden* referring court asked whether the test looks at the specific provider or the market for similar services (question 1). The Court answered only for the specific case.
- Data point: the Commission designated **Wikipedia (Wikimedia Foundation Inc.)** as a very large online platform on 25 April 2023. The Commission therefore treats a donation-funded, non-profit encyclopaedia as being in DSA scope.
- An Instance run by volunteers with no ads, fees, sponsorship or paid staff is the weakest case for "remuneration". Donations, grants, a paid hosting arrangement or institutional backing would strengthen it. Whether a Rome Instance is in scope is **[legal review]**.
- Working assumption for product design: **assume the Instance is in scope.** The baseline duties are cheap, overlap with what the brief already asks for ("communicating moderation decisions", README §10 and §17), and are hard to retrofit.

### 1.3 Who is the provider, and who supervises

- The provider is whoever operates the Instance: an association, a foundation, a person, or an institution. The TART software project (or brand owner) is not the provider of a third party's Instance. This matches ADR 0001 (one Instance per deployment) and the CLAUDE.md separation of platform and archive identity.
- The Member State of the provider's main establishment has exclusive supervisory powers (Art. 56(1)). In Italy the DSC is **AGCOM**, designated by decree-law no. 123/2023 (AGCOM press release of 30 October 2023; art. 15 of that decree per AGCOM delibera 270/24/CONS).
- Penalties are set by each Member State, capped at 6 % of annual worldwide turnover (Art. 52(3)). Italy's penalty rules were not checked. **[unverified]**

### 1.4 AGCOM supervisory contribution (Italy-specific)

- Art. 15(5) of decree-law 123/2023 funds AGCOM's DSC role through a contribution of 0.135 per thousand of the turnover of intermediary service providers established in Italy (AGCOM delibera 270/24/CONS).
- For 2024, the delibera exempted providers whose taxable base was **€500,000 or less** (Art. 1(3)). However, Art. 4(1) required an online declaration **"anche nel caso in cui il contributo non sia dovuto"** (even when no contribution is due), with sanctions for a missing declaration (Art. 4(4)).
- AGCOM adopts a new delibera each year. The rules for 2025 and 2026, and whether a no-revenue volunteer association must file, were not verified. **[unverified] [legal review]** This is an operational duty of the Rome operator, not a product feature.

---

## 2. Duties that apply to every Instance (no size exemption)

| Article | Duty | What it means for TART |
|---|---|---|
| Art. 9 | Report back to an authority that orders action against specific illegal content | Moderators need a way to Withdraw on an order and record the order reference. Art. 17(5) says no statement of reasons is due for Art. 9 orders, but Art. 9(5) requires informing the user. |
| Art. 10 | Report back to an authority that orders information about specific users, and inform the user | Operational. Only data "already collected… and which lies within its control" can be required (Art. 10(2)(b)), which is an argument for data minimisation. |
| Art. 11 | Single electronic point of contact for authorities, made public, with the languages accepted | Instance configuration: authority contact email and languages. One must be an official language of the establishment Member State (Art. 11(3)): Italian for Rome. AGCOM asks Italian providers to notify it to `dsa@agcom.it` or by PEC with the subject "COMUNICAZIONE PUNTO DI CONTATTO ex art. 11 DSA". |
| Art. 12 | Single point of contact for users: electronic, user-friendly, and "not solely" automated | Instance configuration: a public contact channel answered by a human. |
| Art. 13 | Legal representative in the EU | Applies only to operators established outside the EU. |
| Art. 14 | Terms and conditions describing content restrictions, moderation policies, procedures, tools, "algorithmic decision-making and human review", and complaint-handling rules; plain language; machine-readable; notify significant changes; explain them to minors if the service is mainly used by minors; apply them diligently and proportionately | Terms are Instance configuration. Drafting them is out of scope for the MVP map, but the product needs a terms page per locale, a version history, and a way to notify Users of changes. The terms must describe pre-moderation, Withdrawal grounds and the notice channel. |
| Art. 16 | Notice-and-action mechanism (see §4) | Report flow. |
| Art. 17 | Statement of reasons for restrictions (see §5) | Withdrawal and rejection messages. |
| Art. 18 | Promptly inform police or judicial authorities of information giving rise to suspicion of a criminal offence threatening life or safety | Moderator escalation path and guidance, for example for threats written in a photographed piece. |

Art. 8 rules out any general obligation to monitor. TART's pre-moderation is voluntary, a product choice in the brief, not a DSA duty.

---

## 3. Size exemptions

| Duty | Who is exempt | Source |
|---|---|---|
| Art. 15 annual transparency report on content moderation | Providers that "qualify as micro or small enterprises as defined in Recommendation 2003/361/EC" and are not very large online platforms | Art. 15(2) |
| Section 3, online platforms (Art. 20–28) | Online platforms that qualify as micro or small enterprises, and for 12 months after they lose that status. The exemption does not cover Art. 24(3): giving the DSC or Commission user numbers on request | Art. 19(1); Recital 57 |
| Section 4, online marketplaces (Art. 29–32) | Not relevant: TART concludes no distance contracts | Art. 29 |

**The thresholds** (Recommendation 2003/361/EC, Annex, Art. 2) are:

- Small: fewer than 50 staff and annual turnover or balance sheet ≤ €10 million.
- Micro: fewer than 10 staff and ≤ €2 million.

A volunteer Instance falls far below both.

**The "enterprise" wrinkle.**

- The Recommendation defines an enterprise as "any entity engaged in an economic activity, irrespective of its legal form… including… associations regularly engaged in an economic activity" (Annex, Art. 1).
- If an Instance is in DSA scope, that is because its service counts as economic (§1.2). On that reading it is a micro enterprise and exempt.
- If it has no economic activity, it is arguably not an information society service at all.
- Either way a small, private Instance should end up with only the Section 1–2 duties. The text does not address non-economic providers directly. **[legal review]**

**The public-body trap.** "An enterprise cannot be considered an SME if 25 % or more of the capital or voting rights are directly or indirectly controlled… by one or more public bodies" (Annex, Art. 3(4)).

- An Instance run by a city council, a public university or a state museum would get no Art. 15 or Art. 19 exemption.
- If it is an online platform (§1.1), it would owe internal complaint handling for at least six months after each decision (Art. 20), out-of-court dispute settlement information (Art. 21), trusted-flagger priority (Art. 22), misuse policies (Art. 23), submission of every statement of reasons to the Commission database (Art. 24(5)), and the Art. 25 and 28 interface and minor-protection duties.
- This matters for the multi-instance model, because cultural institutions are plausible Instance operators. Instance configuration might need a "full online platform duties" profile. The decision belongs to #14 or the platform/instance boundary ticket.

Recital 57 says exempt providers may adopt any of these duties voluntarily.

**Trusted flaggers (Art. 22)** only bind online platforms that are not exempt.

- In Italy, AGCOM awards the status under delibera 283/24/CONS, in force since 15 September 2024. The status lasts three years.
- A trusted flagger's notice to an exempt Instance is an ordinary Art. 16 notice. The Instance must still process it diligently, just without a legal priority duty.
- AGCOM's list of awarded flaggers (a PDF attachment) was not read. **[unverified]** Copyright-focused flaggers are the ones most likely to target an archive of photographed artworks.

---

## 4. Notice and action (Art. 16), mapped to Withdrawal

### What the DSA requires of every hosting provider

- **Who can notify:** "any individual or entity", by electronic means only. The mechanism must be "easy to access and user-friendly" (Art. 16(1)). Recital 50 adds that it should be "clearly identifiable, located close to the information in question", should allow notifying "multiple specific items… through a single notice", and should "allow, but not require, the identification" of the notifier.
- **What the form must make it easy to supply** (Art. 16(2)):
  - (a) a substantiated explanation of why the content is illegal;
  - (b) its exact location, such as the URL, plus any extra identification needed;
  - (c) the notifier's name and email, except for child sexual abuse offences;
  - (d) a statement of bona fide belief that the notice is accurate and complete.
- **Effect on liability:** a notice gives "actual knowledge or awareness" for Art. 6 purposes when a diligent provider can identify the illegality "without a detailed legal examination" (Art. 16(3); Recital 53; *YouTube*, para 116). After that, the exemption depends on acting "expeditiously" (Art. 6(1)(b)).
- **Process duties:**
  - Acknowledge receipt "without undue delay" when contact details are given (Art. 16(4)).
  - Decide "in a timely, diligent, non-arbitrary and objective manner", and disclose any use of automated means (Art. 16(6)). Urgency depends on the type of content, for example threats to life (Recital 52).
  - Notify the notifier of the decision, with information on redress (Art. 16(5)).
- **"Illegal content"** means anything not complying with EU law or the law of any Member State (Art. 3(h)). Recital 12 lists "the non-authorised use of copyright protected material" and "unlawful non-consensual sharing of private images". It also says an image of an illegal act is not illegal content merely because it depicts one. That point is relevant: a photograph of unauthorised graffiti is not illegal content just because the graffiti was illegal.

### Mapping to TART concepts

- **Withdrawal is TART's "action".** The glossary defines it as hiding an Archive record or Documentation item "for legal, rights, or privacy reasons". That covers the DSA's "removal" and "disabling of access" (Art. 3(t), Art. 17(1)(a)). Because Withdrawal hides rather than deletes, it fits "disabling access". It also keeps the evidence needed to defend or reverse the decision. The #10 media research already routes all media through the app, so Withdrawal is a database flag.
- **Who notifies.** Typical notifiers on an urban art archive:
  - an Artist or their agent: copyright in the artwork, moral rights, attribution disputes;
  - a photographer whose photo was uploaded by someone else;
  - a person visible in a photo: portrait rights under art. 96 L. 633/1941, and the GDPR;
  - a person named in an Artist record or Attribution: defamation or GDPR, including attributing an illegal act to an identifiable person;
  - a building owner;
  - an authority.

  All of them use one Art. 16 channel. Requests under GDPR Arts 15–22 are a separate legal track with their own deadlines. One intake form can serve both if it records which legal ground is invoked. **[legal review]** on whether a combined form is acceptable.
- **Granularity.** Notices target "specific items of information" (Art. 16(1)), and action should be "strictly targeted" (Recital 51). So Withdrawal must be possible per Documentation item, and ideally per field or claim (for example one Attribution), not only per Artwork. The current glossary allows Withdrawal of an Archive record or a Documentation item. Whether a single Attribution or Artist detail can be withdrawn without hiding the whole record is a modelling question for #14 and the domain model.
- **Pending Submissions** are also hosted content. A notice may target something not yet public, for example after a Submitter shares a preview link. The report mechanism should therefore cover anything addressable by URL, not only approved records.
- **The notice record** must keep: received-at time, notifier contact (optional), the items targeted, the ground claimed (law or terms), the decision, the decision time, the reasons, whether automation was used, and the redress information sent. This feeds Art. 16(5), Art. 17 and any Art. 15 report. Personal data in notices raises its own GDPR retention question.
- **Accessibility and i18n.** The report control must be reachable without hover, labelled, and available in every UI locale (CLAUDE.md invariants). The notifier's language is not necessarily the content language.

---

## 5. Statement of reasons (Art. 17), mapped to Withdrawal and Submission rejection

### What the DSA requires

- A "clear and specific statement of reasons" must go to "any affected recipients" for restrictions imposed "on the ground that the information provided… is illegal content or incompatible with their terms and conditions" (Art. 17(1)). The restrictions covered include:
  - any restriction of visibility, "including removal… disabling access… or demoting" (a);
  - suspension or termination of the service (c);
  - suspension or termination of an account (d).
- It applies only where electronic contact details are known (Art. 17(2)), and "at the latest from the date that the restriction is imposed".
- **Minimum content** (Art. 17(3)):
  - (a) what the measure is, its territorial scope and duration;
  - (b) the facts relied on, and whether it followed an Art. 16 notice or the provider's own initiative. The notifier's identity is included only "where strictly necessary"; Recital 54 gives intellectual property claims as an example;
  - (c) any automated means used;
  - (d) the legal ground and why the content is illegal on that ground, or (e) the contractual ground in the terms and why the content conflicts with it;
  - (f) the redress available: internal complaint handling where it exists, out-of-court settlement, and the courts.
- Recital 55 says recipients "should always have a right to effective remedy before a court".

### Mapping to TART

- **Withdrawal → statement of reasons to the affected Submitters.** The "affected recipient" is whoever provided the information.
  - A Documentation item has one Submitter.
  - An Archive record is built from many Revisions by different Submitters. Withdrawing a whole Artwork arguably affects every Submitter whose content is hidden.
  - Proposed rule for #14: notify the Submitters of the withdrawn items. Pseudonymised or deleted accounts have no contact details, so Art. 17(2) does not apply to them.
- **Withdrawal reason codes** should be structured. Each needs a legal ground (copyright, portrait right, GDPR, defamation, authority order) or a contractual ground (a clause in the Instance terms), plus a free-text explanation. Codes need translations for the UI, but the explanation is written per case and may not be in the Submitter's UI language.
- **Rejecting a Submission.**
  - A rejected Submission was never public. Whether refusing to publish is a "restriction of visibility" under Art. 17(1)(a) is not settled in the text.
  - Arguments that it is: the definition of content moderation includes measures that "affect the availability, visibility, and accessibility" of information, and measures that affect "the ability of the recipients of the service to provide that information" (Art. 3(t)). Art. 17(2) applies "regardless of why or how" the restriction was imposed.
  - When the rejection ground is illegality (an uploaded photo infringes someone's copyright) or a clause of the terms (the contribution guidelines), Art. 17 very plausibly applies.
  - When the ground is purely editorial (insufficient evidence, a duplicate, a request for revision), it applies only if the terms make those criteria contractual, which they probably will. **[legal review]**
  - Practical conclusion for #14: **give every rejection the Art. 17(3) elements.** That means: what happened; the grounds, with a reference to the terms clause or law; that the decision was taken by a human Moderator (and any automated pre-checks, such as duplicate detection); and how to contest it, at least by revising and resubmitting, using the contact point, or going to court. The brief already requires "communicating moderation decisions" and explaining "what action is required from the contributor" (README §10 and §17), so the extra cost is small.
- **Account suspension or termination** of a User also triggers Art. 17(1)(d).
- **Moderation notes.** The statement of reasons the Submitter receives is a different artefact from internal moderation notes. The visibility of notes is an open item on the map.

### What is optional for a small Instance

- An internal appeal system (Art. 20) and a redress section naming certified out-of-court bodies (Art. 21) are platform duties covered by the Art. 19 exemption.
- The statement of reasons must still list the redress "available", which for an exempt Instance may be resubmission, the contact point and the courts.
- A lightweight "ask for reconsideration" action costs little and is voluntary (Recital 57).

---

## 6. Moderation before publication and the hosting exemption

### The rule

- Art. 6(1) shields a hosting provider from liability for information "stored at the request of a recipient" as long as it lacks actual knowledge or awareness, or acts expeditiously once it gets it.
- The shield does not apply "where the recipient of the service is acting under the authority or the control of the provider" (Art. 6(2)).
- Recital 18: the exemptions "should not apply where, instead of confining itself to providing the services neutrally by a merely technical and automatic processing… the provider… plays an active role of such a kind as to give it knowledge of, or control over, that information", including information "developed under the editorial responsibility of that provider".

### CJEU case law (developed under e-Commerce Directive Art. 14, carried into the DSA: Recital 16)

- *Google France* (C‑236/08 to C‑238/08) and ***L'Oréal v eBay*** (C‑324/09, paras 113–116):
  - Storing content, setting terms, being paid and giving general information do not remove the exemption.
  - "optimising the presentation… or promoting" specific content is an active role that does remove it.
- ***Papasavvas*** (C‑291/13, para 45): a newspaper publisher that "has knowledge of the information which it posts and exercises control over that information" cannot be an intermediary under Articles 12–14, "whether or not access to that website is free of charge".
- ***YouTube and Cyando*** (C‑682/18 and C‑683/18, Grand Chamber, 2021):
  - The test is whether the operator's conduct is "merely technical, automatic and passive" or "an active role that gives it knowledge of or control over that content" (para 106).
  - The Court relied on the fact that the operators "do not create, select, view or monitor content uploaded to their platforms" (para 109).
  - Automated detection of infringements does not by itself amount to an active role (para 109).
  - Indexing, search and recommendations do not give "specific" knowledge (para 114, now DSA Recital 22).

### The DSA safety valve and its limits

- Art. 7: providers do not lose the exemption "solely because they, in good faith and in a diligent manner, carry out voluntary own-initiative investigations into, or take other measures aimed at detecting, identifying and removing, or disabling access to, **illegal content**".
- Recital 26 adds that such activities "should not be taken into account when determining whether the provider can rely on an exemption… without this rule however implying that the provider can necessarily rely thereon."

### Application to TART

- **TART pre-moderation is not only an illegal-content filter.** Moderators review every Submission for accuracy, evidence and duplicates, compare it with existing data, and approve it as part of an *authoritative* archive (README §10 and §17; ADR 0002). That is knowledge of and control over each published item, close to editorial responsibility.
- The part of moderation that screens for illegality (copyright, privacy, defamation) is covered by Art. 7. The editorial selection is not.
- **Likely consequence:**
  - Information stored while pending is hosted at the Submitter's request and plausibly covered by Art. 6.
  - Once a Moderator approves it into an Archive record, a court could treat the Instance as having knowledge of and control over it. The Art. 6 shield would then not be available for that content, and liability would follow the ordinary national rules (copyright, defamation, portrait rights, GDPR) as if the Instance had published it itself.
  - The DSA does not decide whether the Instance is then liable. It only stops shielding it (Recital 17). **[legal review]**
- The invariant "Submissions are not archive records; only approved data becomes authoritative" (CLAUDE.md) is a deliberate product choice that this research does not challenge. The point is that it carries a legal cost, which should be managed through:
  1. Moderation checklists that cover the legal risks (copyright and quotation, bystanders, naming of identifiable people), not only accuracy.
  2. Contributor warranties and licences, as in #8.
  3. Fast, granular Withdrawal.
  4. Possibly separating the parts of the Instance that host without editorial review (for example user profile text, if any) from approved archive content. Recital 15 allows different provisions to apply to different services of one provider.
- **GDPR is not shielded either way.** In *Russmedia Digital* (C‑492/23, Grand Chamber, 2 December 2025), the operator of an online marketplace was held to be a controller of personal data in user ads. It must, **before publication**, identify ads containing Art. 9 GDPR sensitive data and refuse them unless consent or another exception is shown. It also "cannot rely" on the hosting exemptions for its GDPR obligations. The DSA itself is "without prejudice" to the GDPR (Art. 2(4)(g)).
  - *Russmedia* concerns Art. 9 sensitive data in a marketplace, not Art. 10 offence data in an archive, so it is not directly on point.
  - Its logic suggests that an Instance's pre-moderation must check personal data, such as Attributions of unauthorised works to identifiable people and bystanders in photos, as a controller duty. **[legal review]**
  - This reinforces the #8 open questions on Artist records and bystander privacy.

### Copyright overlay (outside the DSA)

- The DSA is without prejudice to EU copyright law (Art. 2(4)(b), Recital 11).
- The special Art. 17 regime of the DSM Directive (EU) 2019/790 targets "online content-sharing service providers", defined as storing a "large amount" of protected works that the provider "organises and promotes for profit-making purposes". It expressly excludes "not-for-profit online encyclopedias, not-for-profit educational and scientific repositories" (DSM Directive Art. 2(6)).
- A non-commercial Instance very likely falls outside that regime, but this was not researched in depth. **[legal review]**
- Separately, AGCOM's art. 174-sexies LDA contact-point duty (introduced by the "decreto Omnibus") covers network access providers, search engines, VPNs, CDNs and similar services, and hosting providers only when they act as reverse proxies. It does not appear to reach an ordinary Instance.

---

## 7. Product implications to hand to #14

These are options and constraints, not decisions.

1. **Report mechanism (Art. 16)** on every public Archive record, Documentation item and Artist record, and on any URL-addressable pending content.
   - No login required; the form makes the Art. 16(2)(a)–(d) elements easy to provide.
   - Several items can be reported in one notice. The notifier chooses a ground category (copyright, portrait or privacy, defamation, other illegality, terms violation).
   - Automatic acknowledgement; decision notice with redress information.
   - Accessible, localised, not hover-dependent.
2. **Notice log** as a first-class record: timestamps, items, ground, decision, reasons, automation flag, outcome.
   - This makes Art. 16(5) and Art. 17 traceable and an Art. 15 report possible. The harmonised templates are in Implementing Regulation (EU) 2024/2835: calendar-year periods, published within two months, Annex I templates from 1 July 2025.
   - Retention needs a GDPR rule.
3. **Withdrawal with structured reasons.** Each Withdrawal carries a reason code tied to a legal or terms ground, a free-text explanation, a source (notice, authority order, own initiative), the measure's scope and duration, and the date.
   - It triggers an Art. 17 statement to the affected Submitters who have contact details.
   - Withdrawal stays out of the Timeline (glossary).
   - **Decide:** whether the public sees a neutral "withdrawn" placeholder (not required by the DSA), and how granular Withdrawal is (Documentation item, Attribution, field).
4. **Submission rejection** messages built to the Art. 17(3) template: grounds with a reference to the terms clause or law, human decision, the automated checks used, and redress options. One template system can serve both rejections and Withdrawals.
5. **Instance configuration:**
   - authority point of contact (Art. 11) and its languages;
   - user point of contact (Art. 12);
   - terms of service per locale, with versioning and change notification (Art. 14);
   - a DSA profile ("small hosting provider" vs "full online platform duties" for publicly controlled Instances, see §3);
   - the name of the operator, as distinct from the TART brand.
6. **Moderator tooling:**
   - a separate queue for notices, with urgency triage (Recital 52);
   - recording of authority orders (Art. 9);
   - an escalation path for threats to life or safety (Art. 18);
   - a legal-risk checklist in the review screen (§6).
7. **Not needed for a small private Instance** (Art. 19), but cheap to design for: a reconsideration request, trusted-flagger tagging of notices, and repeat-infringer handling.

---

## 8. Points needing professional legal review

1. Whether a volunteer-run, revenue-free Instance is an "information society service" at all ("normally provided for remuneration"), and how donations, grants or institutional backing change that.
2. Whether an in-scope but non-economic operator can rely on the Art. 15(2) and Art. 19 micro/small-enterprise exemptions, which are defined through the "enterprise" concept of Recommendation 2003/361/EC.
3. Whether a pre-moderated Instance is an "online platform" (dissemination "upon the direct request" of the Submitter, Recital 14), which matters for publicly controlled Instances.
4. **Whether approving Submissions into an authoritative archive removes the Art. 6 hosting exemption for approved content**, given *L'Oréal*, *Papasavvas* and *YouTube* para 109, and which national liability regimes then apply (Italian copyright, defamation, art. 96 L. 633/1941).
5. Whether rejecting a Submission is a "restriction of visibility" requiring an Art. 17 statement of reasons, and whether editorial grounds count as "incompatible with terms and conditions".
6. Who the "affected recipients" are when a multi-Submitter Archive record is withdrawn.
7. Whether one intake channel can handle both DSA notices and GDPR data-subject requests.
8. Italian specifics: the AGCOM contribution and declaration duty for zero-revenue operators in 2025 and 2026, and the Italian penalty regime under Art. 52.
9. How *Russmedia* (C‑492/23) affects pre-publication screening of personal data (Attributions to identifiable people, bystanders).
10. Whether DSM Directive Art. 17 (online content-sharing service providers) could ever apply to an Instance.

## 9. Open questions that may deserve their own ticket

- **Notice-and-action and Withdrawal workflow spec:** the report form, notice log, reason codes, statement-of-reasons templates, and Withdrawal granularity (record, Documentation item, Attribution or field). It overlaps #14 but is large enough to stand alone.
- **Instance operator and legal-entity guidance:** what an Instance operator must set up outside the software (contact points, AGCOM notification and contribution declaration, terms, law-enforcement escalation), as a checklist in the Instance setup docs. It ties into Journey F and the operations item.
- **Publicly controlled Instances:** whether TART supports a "full online platform" compliance profile (Art. 20–28), or documents that such operators are unsupported in the MVP.

---

## Sources

Primary legal texts (EUR-Lex):

- Regulation (EU) 2022/2065 (Digital Services Act), consolidated HTML: <https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32022R2065>. Arts 2, 3, 6–18, 19–25, 52, 56, 93; Recitals 5, 12–18, 22, 26, 41, 50–58.
- Commission Recommendation 2003/361/EC (SME definition): <https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32003H0361>. Annex Arts 1, 2, 3(4).
- Directive (EU) 2015/1535, Art. 1(1)(b) (information society service): <https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32015L1535>
- Directive (EU) 2019/790 (DSM copyright), Art. 2(6): <https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32019L0790>
- Commission Implementing Regulation (EU) 2024/2835 (transparency report templates): <https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32024R2835>

CJEU (EUR-Lex):

- C‑324/09 *L'Oréal v eBay*, 12 July 2011, paras 112–116: <https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:62009CJ0324>
- C‑291/13 *Papasavvas*, 11 September 2014, paras 28–29, 45–46: <https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:62013CJ0291>
- C‑484/14 *Mc Fadden*, 15 September 2016, paras 39–43: <https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:62014CJ0484>
- C‑682/18 and C‑683/18 *YouTube and Cyando*, 22 June 2021, paras 103–117: <https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:62018CJ0682>
- C‑492/23 *Russmedia Digital*, 2 December 2025, operative part: <https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:62023CJ0492>
- C‑236/08 to C‑238/08 *Google France*: cited through *L'Oréal* and *YouTube*, not fetched directly.

European Commission:

- DSA questions and answers (updated 19 December 2025): <https://digital-strategy.ec.europa.eu/en/faqs/digital-services-act-questions-and-answers>. It says only that small and micro enterprises are "exempted from some rules" and does not address non-profits.
- List of designated VLOPs and VLOSEs (Wikipedia, Wikimedia Foundation Inc., designated 25 April 2023): <https://digital-strategy.ec.europa.eu/en/policies/list-designated-vlops-and-vloses>

AGCOM (Italy's DSC):

- Art. 11 point of contact notice (6 June 2024): <https://www.agcom.it/competenze/piattaforme-online/digital-service-act/comunicazione-rappresentante-legale-e-punto-di-contatto-ex-art-11-dsa>
- Trusted flaggers, delibera 283/24/CONS: <https://www.agcom.it/competenze/piattaforme-online/digital-service-act/Segnalatori-Attendibili>
- Delibera 270/24/CONS, DSC contribution for 2024: <https://www.agcom.it/sites/default/files/provvedimenti/delibera/2024/Del.%20270_24_CONS_giro%20firme.pdf>
- Press release of 30 October 2023 (designation by d.l. 123/2023): <https://www.agcom.it/sites/default/files/migration/article/Comunicato%20stampa%2030-10-2023.pdf>
- Art. 174-sexies LDA contact point notice (10 March 2025): <https://www.agcom.it/comunicazione/avvisi/comunicazione-punto-di-contatto-e-rappresentante-legale-ex-art-174-sexies-lda>

**Method note.**

- The DSA, the Recommendation, the CJEU judgments, the DSM Directive and IR 2024/2835 were downloaded from EUR-Lex and quoted from the full text.
- AGCOM web pages were read through a summarising fetch. Delibera 270/24/CONS and the press release were read as full PDF text.

**Not verified:**

- Italy's DSA penalty rules.
- AGCOM contribution rules for 2025 and 2026.
- AGCOM's list of awarded trusted flaggers.
- The decree number behind art. 174-sexies LDA.
- The *Google France* judgment text.
