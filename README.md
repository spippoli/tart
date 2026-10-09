# TART — Platform Design Brief

## 1. Role and mission

Act as a senior product designer and UX/UI designer with expertise in digital archives, cultural heritage platforms, collaborative knowledge systems, map-based applications, community platforms, and open/source-available software projects.

Your task is to design the user experience, information architecture, interface, and product principles of **TART**, a collaborative platform for documenting, exploring, and preserving the history of urban art.

The initial instance of TART is focused on **Rome, Italy**.

TART aims to become the largest collaborative archive of urban art in Rome while also being designed from the beginning as a platform that can be deployed by independent communities in other cities and countries.

TART should therefore be understood as both:

1. A platform for building a local urban-art archive.
2. A reusable technological and cultural foundation that can support multiple independent local communities.

The project should support a model such as:

```text
Rome Urban Art Archive
Powered by TART

Berlin Urban Art Archive
Powered by TART

Lisbon Urban Art Archive
Powered by TART
```

Each local instance should be able to maintain its own community, archive, moderation processes, and editorial identity while using the TART software platform.

---

## 2. Product mission

TART exists to address two fundamental problems:

* Urban artworks are frequently ephemeral and may disappear, deteriorate, be modified, covered, or destroyed.
* Documentation about these artworks is often fragmented, unstructured, or lost, making their history difficult to reconstruct.

TART preserves the memory of urban art through:

* photographs;
* other forms of media;
* geographical locations;
* artist information;
* historical documentation;
* community contributions;
* structured historical records.

The platform should make it possible to document an artwork even after its physical existence has ended.

The core idea is:

> **The disappearance of an artwork does not mean the disappearance of its history.**

---

## 3. TART as a reusable local-community platform

Although the first TART deployment is intended for Rome, the product must not be architecturally or conceptually limited to Rome.

The design should make it possible for another community to deploy TART and create its own local archive.

Examples include:

* a street-art archive for another Italian city;
* an urban-art archive in another European city;
* a community-run archive for a country or region;
* an archive maintained by a cultural association;
* an academic or research-oriented local archive;
* a municipal or cultural institution using TART.

The local community should be able to define its own:

* geographical scope;
* users;
* moderators;
* editorial practices;
* archive content;
* local terminology;
* visual identity where appropriate;
* community rules.

Do not design TART as a centralized global social network.

Instead, design it as a **reusable platform for independent local archives**.

---

## 4. "Powered by TART" model

The project should support a recognizable attribution model based on:

> **Powered by TART**

A local deployment may present its own identity prominently while acknowledging the underlying platform.

For example:

```text
ROME URBAN ART ARCHIVE

Powered by TART
```

or:

```text
BERLIN STREET ART ARCHIVE

Powered by TART
```

The design should distinguish:

* the identity of the local archive;
* the TART platform identity;
* the content and data belonging to that local community.

Do not assume that every deployment must use the TART visual identity as its primary branding.

The TART name and logo should be treated separately from the software license and from local archive data.

The design should therefore anticipate a future distinction between:

* **software license**;
* **TART trademark/brand usage**;
* **local archive data and content**.

---

## 5. Product principles

All design decisions must follow these principles:

1. **Archive first** — documenting, discovering, and understanding artworks is the primary purpose.
2. **Place matters** — geographical location is a fundamental part of each artwork's identity and the overall browsing experience.
3. **Time matters** — an artwork is not a static record. Its history and evolution must be documented over time.
4. **Collaborative knowledge** — registered users contribute documentation and corrections through a structured submission workflow.
5. **Human moderation** — community contributions are reviewed before becoming part of the authoritative archive.
6. **Historical memory** — disappeared, destroyed, covered, or deteriorated artworks remain valuable archival records.
7. **Evidence and attribution** — distinguish documented facts, community-provided information, uncertain attributions, and verified information.
8. **Independent communities** — local communities should be able to operate their own TART deployment.
9. **Non-commercial mission** — TART should support community, cultural, educational, research, institutional, and other non-commercial uses rather than becoming a commercial SaaS or commercial product.
10. **No engagement-driven social mechanics** — the platform should not be designed around likes, followers, popularity, or advertising.
11. **Long-term preservation** — the value of the archive should increase as documentation accumulates over time.
12. **Open collaboration** — the software should be reusable and adaptable by communities while protecting the project's non-commercial mission.

---

## 6. Licensing and project governance

Licensing is part of the product design and architecture and must be considered during the project.

The intended model is:

> TART software should be freely available for people and organizations to deploy, modify, and operate their own local community archives, but it should not be used as the basis for a commercial product, commercial SaaS, or other commercial exploitation of the software.

The project should support legitimate operational activities such as:

* running a local TART instance;
* modifying and extending the software;
* creating forks;
* deploying TART for another city or country;
* operating a community archive;
* paying ordinary infrastructure costs such as hosting, storage, domains, or backups;
* obtaining professional technical assistance for deployment or maintenance where this is consistent with the chosen license.

The project should prevent, subject to the final legal wording of the license:

* selling TART as software;
* selling modified versions of TART;
* offering TART as a commercial SaaS;
* offering hosted TART instances as a commercial product;
* sublicensing TART commercially;
* charging users for access to TART as a commercial service;
* commercially exploiting TART as a software product.

### Important licensing distinction

Do not assume that "open source" and "non-commercial" are compatible terms.

A license that prohibits commercial use is generally **source-available rather than Open Source according to the OSI definition**.

The project should therefore use precise terminology in its documentation.

Preferred terminology includes:

* "source-available";
* "freely available for non-commercial use";
* "community-oriented platform";
* "community-run software".

Avoid describing TART as "Open Source" unless the final licensing model actually satisfies the relevant definition.

### License evaluation task

As part of the project design work, evaluate available standard licenses suitable for the intended model.

At minimum, consider:

* PolyForm Noncommercial;
* Business Source License;
* other established source-available/non-commercial licenses that may be appropriate.

Do not automatically select a license without documenting the reasoning.

For each candidate license, evaluate:

* permission to deploy independent local instances;
* permission to modify and fork;
* redistribution rights;
* treatment of hosted/SaaS deployments;
* definition of commercial use;
* compatibility with community organizations;
* treatment of infrastructure costs;
* clarity for contributors;
* enforceability and practical interpretation;
* compatibility with the "Powered by TART" model;
* interaction with trademark/brand protection;
* interaction with third-party dependencies.

The final project documentation must contain a **Licensing Decision Record** explaining:

1. Which license was selected.
2. Why it was selected.
3. Which uses are explicitly permitted.
4. Which uses are explicitly prohibited.
5. How local community deployments are treated.
6. How commercial use is treated.
7. How the TART name and logo are treated.
8. How third-party code and dependencies are handled.
9. Whether additional legal review is recommended.

Do not write a custom license merely for convenience. Prefer an established standard license when it adequately expresses the project's requirements.

If no standard license precisely matches the intended model, explicitly document the gap and recommend legal review before creating a custom license.

### Current decision

TART is source-available under the PolyForm Noncommercial License 1.0.0 (`LICENSE`), provisionally and pending professional legal review. The Licensing Decision Record is [`docs/adr/0011-provisional-software-license.md`](docs/adr/0011-provisional-software-license.md).

---

## 7. Separation of software, brand, data, and content

Do not treat everything in the TART ecosystem as being covered by the same license.

At minimum distinguish:

### Software

The TART source code and related software components.

This is the subject of the project's software license.

### TART brand

The:

* TART name;
* TART logo;
* official project identity.

Brand usage should be considered separately from the software license.

The project should be able to allow local deployments to say:

> Powered by TART

without automatically granting permission to impersonate the official TART project.

### Local archive data

Each deployment may maintain its own archive.

Data licensing must be considered separately from the software license.

### User-generated content

Photographs, descriptions, documentation, and other content submitted by users may have rights belonging to the contributors or third parties.

The platform must not assume that the TART software license grants rights to this content.

### Artwork rights

TART documents physical artworks and their history.

The software license does not grant rights to the underlying artworks or automatically grant rights to photographs of those artworks.

The design should therefore anticipate appropriate rights, attribution, and content policies.

---

## 8. Target audience

Design primarily for:

* Urban art enthusiasts.
* Photographers documenting street art and other forms of urban creativity.
* Citizens interested in the cultural history of their city.
* Artists who want to discover or document their work.
* Community contributors who help improve the archive.
* Moderators responsible for reviewing submissions and maintaining data quality.
* Cultural organizations and institutions that may operate local archives.

The interface must support both casual visitors who want to discover nearby artworks and dedicated contributors who need to document an artwork accurately.

---

## 9. Scope of the archive

TART documents any form of creative urban expression, including but not limited to:

* murals and large-scale paintings;
* graffiti and lettering;
* stencils;
* posters and paste-ups;
* stickers and other graphic interventions;
* installations and sculptural works;
* temporary or experimental urban art;
* other creative interventions in public or urban spaces.

Do not limit the information architecture or visual language to murals alone.

---

## 10. Core domain concepts

### Artwork

An individual work or creative intervention.

At minimum, an artwork record must support:

* geographical location;
* one or more photographs or other forms of documentation;
* description or identifying information;
* historical record of changes over time.

The information architecture should also accommodate:

* title or commonly used name;
* type of artistic expression;
* artist attribution;
* unknown or uncertain authorship;
* creation date or estimated period;
* documentation dates;
* additional photographs and media;
* contextual notes;
* historical references;
* current or last documented condition;
* relationships with other artworks or locations.

Do not assume all information is available when an artwork is first submitted.

### Artwork history

An artwork must support a chronological history of its documented evolution.

Possible events include:

* first known documentation;
* new photographs;
* additional evidence;
* changes in physical condition;
* deterioration;
* partial damage;
* modification;
* overpainting;
* covering;
* removal;
* destruction;
* disappearance;
* new information about the artist or attribution.

The interface must clearly distinguish the artwork's historical evolution from the history of edits to its database record.

Historical entries should be presented chronologically and associated with dates, documentation, and sources where available.

Do not assume that the exact creation date or disappearance date is always known.

### Artist

An artist record represents an individual or creative identity associated with one or more artworks.

Artist records may be created or enriched through community submissions.

Artists may have dedicated public pages containing:

* name or artistic alias;
* biography or contextual information;
* associated artworks;
* geographical areas of activity;
* relevant documentation and references.

An artist may register as an ordinary community user.

Do not assume that a registered user automatically owns, controls, or has verified authorship of an artist record.

### Location

A geographical location is a primary means of discovering and contextualizing artworks.

Location-based browsing should support:

* exploring artworks on a map;
* discovering nearby works;
* understanding the concentration of artworks;
* opening an artwork from its map marker;
* exploring historical artworks whose physical presence has disappeared.

Distinguish the geographical location of an artwork from the location of the person submitting it.

### Submission

A submission is a proposed new artwork or proposed modification/addition to an existing record.

Submissions must support a moderation lifecycle:

* draft or in-progress submission;
* submitted for review;
* approved;
* rejected;
* revised and resubmitted.

The interface must communicate submission status clearly and explain what action is required from the contributor.

### User and moderation

Users must register to contribute to the archive.

The platform has a moderation team responsible for reviewing contributions before they become part of the authoritative archive.

Design interfaces for:

* account registration and sign-in;
* user profile and contribution history;
* creating and editing submissions;
* tracking submission status;
* reviewing proposed changes;
* approving or rejecting submissions;
* communicating moderation decisions;
* maintaining useful moderation history.

Keep social functionality deliberately limited to what is necessary to support contributions, review, and community management.

Do not prioritize likes, follower counts, popularity rankings, or engagement-driven feeds.

---

## 11. Primary user journeys

### Journey A — Discover urban art

1. A visitor opens TART.
2. They see a map-centered way to explore urban art.
3. They browse geographical areas and discover artworks.
4. They open an artwork detail page.
5. They explore photographs, context, artist information, and historical evolution.
6. They discover related artworks or the artist's page.

The journey must remain useful even when an artwork no longer exists physically.

### Journey B — Document a new artwork

1. A registered user identifies an artwork.
2. They start a new submission.
3. They select its geographical location.
4. They upload photographs or provide other documentation.
5. They enter available information.
6. They indicate uncertainty where appropriate.
7. They review and submit the record.
8. They receive confirmation that the submission is awaiting moderation.
9. They can track the result.

### Journey C — Contribute to an existing artwork

1. A user opens an existing artwork.
2. They identify missing, outdated, or incorrect information.
3. They propose an edit, add documentation, or submit a historical update.
4. The proposal enters moderation.
5. Once approved, the archive reflects the accepted contribution.

Make it clear that a proposed edit is not automatically an accepted fact.

### Journey D — Document an artwork's disappearance

1. A user opens an existing artwork record.
2. They submit evidence that the work has deteriorated, been covered, removed, or destroyed.
3. They provide photographs, dates, observations, or references.
4. The proposal is reviewed.
5. Once approved, the artwork retains its archival record and its history reflects the newly documented condition.

Never design disappearance as deletion from the archive.

### Journey E — Moderate contributions

1. A moderator opens the review queue.
2. They identify pending submissions and their type.
3. They compare proposed changes with the existing record.
4. They inspect photographs, sources, location, attribution, and uncertainty.
5. They approve or reject the proposal.
6. The contributor receives a clear status update.
7. The archive is updated only after approval.

Make moderation efficient, transparent, and suitable for a growing collection.

### Journey F — Create a local TART community

Design the conceptual journey for an organization or community that wants to create its own local archive.

At minimum consider:

1. Obtain and deploy TART.
2. Configure the local geographical scope.
3. Configure community and moderation roles.
4. Configure local branding and identity.
5. Configure language preferences.
6. Create the initial archive.
7. Invite contributors and moderators.
8. Publish the local archive.
9. Display appropriate "Powered by TART" attribution.

The final design should make clear which aspects belong to TART and which belong to the local deployment.

---

## 12. Information architecture

Propose a clear navigation system covering at least:

* **Explore** — map and discovery of artworks.
* **Archive** — searchable and filterable catalogue.
* **Artists** — artist discovery and individual artist pages.
* **Artwork detail** — documentation, location, attribution, and chronological history.
* **Contribute** — submit an artwork or propose an update.
* **My contributions** — submissions and moderation status.
* **Moderation** — dedicated review tools for authorized moderators.
* **About** — mission, methodology, documentation standards, and project information.

Consider whether the map should be the homepage or central element of the main exploration experience.

The default proposal should prioritize map-based discovery without preventing users from browsing the archive as a list.

Keep public discovery separate from authenticated contribution workflows.

For multi-instance deployments, consider which configuration belongs to:

* the TART platform;
* the local archive;
* the local community;
* individual users.

---

## 13. Visual direction

Create a distinctive identity for an independent cultural archive documenting urban creativity.

The design should feel:

* editorial and archival;
* contemporary but not trend-driven;
* visually rich;
* geographical and exploratory;
* credible and carefully curated;
* open to diverse artistic expressions;
* usable for long-term documentation;
* independent of commercial social-media aesthetics.

Use artwork photography as the primary visual material wherever appropriate.

Consider the contrast between the physical city, its walls and surfaces, and the digital preservation of its creative history.

Develop a restrained, coherent design system.

Establish:

* typography;
* color palette;
* spacing;
* iconography;
* image treatments;
* map markers;
* status indicators;
* interaction patterns.

Avoid:

* generic social-media dashboards;
* excessive gradients;
* gamification;
* engagement-driven UI;
* overly corporate SaaS aesthetics;
* designs that assume all artworks are colorful murals;
* treating historical records as disposable content.

Do not imitate an existing platform directly.

---

## 14. Content, language, and internationalization

The initial product is focused on Rome, Italy.

### Communication and documentation

* **User-agent communication:** All communication between the user and the AI agent must be in Italian, including questions, explanations, plans, progress updates, and summaries.
* **Project documentation:** All project documentation, including README files, specifications, architecture documents, and technical documentation, must be written in English.
* **Code:** All source code, identifiers, variable names, function names, comments, and code-level documentation must be written in English.
* **User-facing content:** The platform must support internationalization from the beginning.

### UI languages

* Italian (`it`) is the default and primary language.
* English (`en`) is the alternative language.
* The architecture must support adding additional languages in the future.

All user-facing text must be translatable, including:

* navigation;
* buttons;
* form labels;
* validation messages;
* notifications;
* moderation statuses;
* error messages;
* accessibility labels;
* empty states;
* system messages.

Do not hardcode user-facing strings inside application components.

Use a consistent internationalization mechanism and externalized translation resources.

Ensure that layouts accommodate differences in text length between languages.

Use locale-aware formatting for:

* dates;
* times;
* numbers;
* other localized values.

Keep language-independent domain data separate from UI translation resources.

Where appropriate, allow descriptive content to be available in multiple languages without duplicating the underlying artwork record.

Do not assume that the language of an artwork description, artist name, or historical source is the same as the user's selected interface language.

### Content guidelines

Use realistic example content relevant to Rome's urban environment, but do not invent historical claims about real artworks or artists.

Clearly mark illustrative sample records as fictional when their factual accuracy cannot be established.

Avoid lorem ipsum in final design proposals.

Use concise, respectful, culturally appropriate language in every supported language.

Ensure that Italian and English interfaces provide equivalent functionality and a consistent user experience.

---

## 15. Map and geographical experience

The map is a core product feature, not a secondary widget.

Design a map experience that considers:

* dense clusters of artworks;
* marker selection;
* artwork previews;
* filters by artistic expression;
* artist;
* date;
* documented condition;
* search by place or address;
* synchronized list/results panel;
* navigation between map and artwork detail;
* historical artworks no longer physically present;
* clear distinctions between documented location and current physical existence.

Consider:

* marker clustering;
* progressive loading;
* responsive layouts.

Do not assume that the map must use a particular provider or mapping library.

The interface should remain understandable when location information is approximate or incomplete.

---

## 16. Artwork detail and historical timeline

The artwork detail page is one of the most important screens in TART.

Design it to communicate:

1. What the artwork is.
2. Where it is or was located.
3. What visual documentation exists.
4. Who created it, if known.
5. What is known and unknown about its history.
6. How the artwork has changed over time.
7. How users can contribute additional evidence or corrections.

Use a chronological timeline or equivalent history-oriented interface.

Support multiple photographs and documentation items associated with different dates.

Make uncertainty visible without making the interface feel unreliable.

Unknown artist, estimated dates, disputed attribution, and unverified information must be represented explicitly.

Where appropriate, distinguish:

* last documented physical condition;
* current known condition;
* date the condition was observed;
* date the information was submitted;
* date the information was approved.

These dates are not necessarily the same.

---

## 17. Contribution and moderation UX

Design submission forms that encourage structured, useful information without making contributions unnecessarily difficult.

Use progressive disclosure.

Consider:

* clear field labels;
* contextual guidance;
* map-based location selection;
* multiple image uploads;
* date precision;
* estimated dates;
* unknown dates;
* attribution uncertainty;
* supporting evidence;
* references;
* duplicate artwork warnings;
* preview before submission;
* draft persistence if appropriate;
* accessible validation;
* clear moderation status.

For moderators provide:

* pending queue;
* filters;
* sorting;
* submission type;
* contributor;
* existing versus proposed data;
* image comparison;
* evidence inspection;
* map preview;
* approval/rejection;
* moderation notes;
* duplicate/conflict warnings.

Do not confuse community submissions with authoritative archive records.

---

## 18. Search, filters, and discovery

Design search and filtering around the needs of an archival catalogue.

Consider searching by:

* artwork name;
* description;
* artist;
* geographical area;
* type of urban expression;
* date;
* historical period;
* physical condition;
* availability of documentation.

Provide useful empty states and clear reset mechanisms.

Support both exploratory discovery and precise lookup.

Avoid ranking artworks exclusively by popularity or engagement.

---

## 19. Multi-instance and local configuration

Because TART is intended to support independent local communities, identify which parts of the application must be configurable per deployment.

At minimum consider:

### Local identity

* archive name;
* logo;
* visual identity;
* description;
* "Powered by TART" attribution.

### Geography

* city;
* region;
* country;
* geographical boundaries;
* default map view.

### Languages

* enabled languages;
* default language;
* locale settings.

### Community

* registration policy;
* moderation roles;
* contribution policies;
* local editorial guidelines.

### Archive

* supported artwork categories;
* metadata fields;
* historical documentation rules;
* attribution conventions.

### Platform

* authentication configuration;
* storage;
* map provider;
* email;
* external integrations.

Do not hardcode Rome-specific assumptions into the core product architecture.

Rome should be the initial configuration, not a fundamental architectural constraint.

---

## 20. Responsive design and accessibility

Design for desktop and mobile.

Users may discover an artwork on a computer and document it directly from the street using a phone.

On mobile prioritize:

* artwork details;
* map navigation;
* location selection;
* camera/image upload;
* quick contributions;
* submission status;
* touch-friendly controls.

On desktop take advantage of wider layouts for:

* map-plus-list browsing;
* historical timelines;
* moderation comparison;
* archive exploration.

Follow WCAG 2.2 AA as a design target.

Include:

* keyboard navigation;
* sufficient contrast;
* visible focus states;
* accessible forms;
* meaningful image alternatives;
* non-color-only status indicators.

Do not make essential functionality dependent on hover.

---

## 21. Functional states to design

For each major screen consider:

* loading;
* successful content;
* empty archive;
* empty search results;
* incomplete artwork information;
* missing images;
* approximate location;
* unknown attribution;
* disputed attribution;
* disappeared artwork;
* destroyed artwork;
* submission awaiting moderation;
* approved submission;
* rejected submission;
* validation errors;
* network failure;
* upload failure;
* unauthorized moderation access;
* no pending moderation tasks.

States must communicate the actual situation without misleading the user.

---

## 22. Deliverables

Produce a coherent design proposal for the entire TART platform.

At minimum deliver:

1. **Product and UX principles**
2. **Information architecture**
3. **Core user journeys**
4. **Multi-instance/local deployment model**
5. **Visual direction**
6. **Key screens**

   * Homepage/main exploration.
   * Map/archive search.
   * Artwork detail.
   * Artwork history.
   * Artist profile.
   * New artwork submission.
   * Existing artwork update.
   * User contribution dashboard.
   * Moderation queue.
   * Moderation review.
   * Local instance configuration.
7. **Reusable components**
8. **Responsive behavior**
9. **Interaction and state specifications**
10. **Implementation-ready design notes**
11. **Internationalization strategy**
12. **Licensing Decision Record**
13. **Brand and "Powered by TART" strategy**
14. **Data/content rights considerations**

Prioritize the core archival experience and map-to-artwork journey before secondary features.

---

## 23. Working method

Work in the following sequence.

### Phase 1 — Understand

Inspect the existing repository, project documentation, current implementation, and established technology choices.

Identify existing constraints.

Do not replace the existing architecture or technology stack without an explicit reason.

### Phase 2 — Define

Produce:

* information architecture;
* core journeys;
* page inventory;
* visual direction;
* multi-instance model;
* language/i18n strategy;
* licensing options;
* brand strategy.

Identify ambiguities that materially affect the design.

Ask focused questions when essential information is missing.

Otherwise document reasonable assumptions and proceed.

### Phase 3 — Licensing decision

Before finalizing the project architecture, evaluate the candidate software licenses.

Document:

* requirements;
* candidate licenses;
* advantages;
* limitations;
* compatibility with the local-community model;
* implications for commercial use;
* implications for SaaS;
* implications for forks;
* implications for local deployments;
* relationship with TART branding.

Produce a clear **Licensing Decision Record**.

Do not silently choose a license.

Do not invent legal claims.

Where legal interpretation is required, clearly identify the issue and recommend professional legal review.

### Phase 4 — Prototype

Build or specify the core screens and reusable components as a coherent, navigable experience.

Prioritize realistic content and working interactions over decorative mockups.

The prototype should demonstrate the "Powered by TART" model and show how a local instance can differ from the TART platform itself.

### Phase 5 — Validate

Evaluate the experience against the core product principles and user journeys.

Check that users can:

* discover artworks geographically;
* understand artwork history;
* explore works that no longer exist;
* distinguish proposed information from approved archival records;
* contribute evidence;
* track submissions;
* review contributions when authorized;
* understand which community/archive they are visiting;
* understand that the local archive is powered by TART.

Check that a future community outside Rome could reasonably use the same product without redesigning its core architecture.

---

## 24. Definition of success

The design succeeds when TART feels like a trustworthy, living archive of urban creativity:

* easy to explore;
* meaningful to contribute to;
* capable of documenting change over time;
* geographically rich;
* deliberately different from a conventional social network;
* reusable by independent local communities;
* clearly identifiable as the technology behind those communities.

A successful local deployment should feel like **its own community archive**, while still communicating:

> **Powered by TART**

Every major design decision should support:

1. historical preservation;
2. geographical discovery;
3. documentation quality;
4. collaborative contribution;
5. transparent moderation;
6. independent local communities;
7. long-term sustainability;
8. non-commercial use of the platform.

When in doubt, prioritize historical context, geographical discovery, documentation quality, community ownership, and long-term usefulness over engagement metrics, commercial optimization, or visual novelty.
