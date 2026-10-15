# UX redesign proposal: a modern, intuitive TART

**Status:** proposal, not normative. Nothing here changes the specs, the ADRs, or the code. Each section ends with the spec text it would change, so that an accepted part becomes its own spec PR (with an ADR where the decision is hard to reverse), as `CLAUDE.md` requires.

**Companion prototype:** [`ux-redesign/prototype.html`](ux-redesign/prototype.html). A single static file, no build step: open it in a browser (Explore with sign selection and the Filters dialog, the Artwork page, the four-step contribution flow, sign-in). It shows Explore, an Artwork page, the contribution flow, and sign-in, in light and dark, at desktop and phone width. All content in it is fictional.

## 1. Why

The implementation follows the specs faithfully, and the specs were written for correctness first: accessibility, uncertainty, moderation, legal handling. What they did not set out is a **visual and interaction language**. The result, read from the code (`frontend/src/app.css`, `lib/shell/Header.svelte`, `lib/discovery/*`, the sign-in page) and the specs, is a product that is correct but unguided:

| Observation | Where | Effect on a visitor |
|---|---|---|
| Browser-default look: `system-ui`, 1 px borders on every control, no type, spacing, or elevation scale | `app.css`, component `<style>` blocks | Everything has the same weight; nothing says "start here". |
| Header carries the logo, the archive name, six text links of equal weight, a search box, the language switcher, and account links | `Header.svelte` | Contributing, the archive's main purpose, is one link among six; on a phone it is behind a "Menu" button. |
| Explore opens with an intro band and a filter bar of many fields, then the map | Discovery spec, Explore and Archive views | The map, the reason to come, starts below the fold on a laptop. |
| On a phone, Map and List are two exclusive pages behind a switch | Discovery spec, Explore and Archive views | The user loses either the place or the content, and can never see both. |
| Artwork page is one long linear document, ten `h2` sections in a fixed order | `artworks/[ref]/+page.svelte` | The photo is third; actions are at the bottom; there is no overview. |
| Contribution is a 7-step stepper for a new Artwork, with free navigation but no sense of what is required | Contribution spec, Submission form | A first-time contributor meets seven stages before seeing a result; required and optional steps look alike. |
| Sign-in shows two paragraphs of explanation before the field | `sign-in/+page.svelte` | Friction at the exact moment someone has decided to help. |

None of these is a bug. They are the absence of design decisions, and they are cheap to fix **without touching a single invariant**.

> Caveat: this diagnosis comes from reading the code and specs, not from usability testing. Section 10 (phase 0) proposes a short test to confirm or overturn it before anything is built.

## 2. Principles

1. **Map and photo first.** TART is about places and images. The first screen of every page leads with one of them.
2. **One obvious next step per screen.** One primary button per view, using the Instance accent. Everything else is secondary or quiet.
3. **Show, then ask.** Browsing needs no account, no explanation, no dialog. Account and rules appear at the moment they matter.
4. **Contributing feels like adding to something, not filling a form.** Start with the photo, ask little, defer the optional.
5. **Calm, archival tone.** Paper and ink, the Pompeian accent, generous space, restrained motion. No gamification, in line with "No engagement mechanics".
6. **Everything in this document keeps the architectural invariants** (section 9). Where a proposal touches one, it says how it stays whole.

## 3. Design language

A small token set in `app.css`, replacing per-component magic numbers. The values below are the proposal; the prototype implements them.

| Token group | Proposal |
|---|---|
| Type | One bundled variable sans (body, UI) with a serif for archive and record titles, echoing the map's Goudy small caps. Scale 14 / 16 / 18 / 22 / 28 / 36 px, line height 1.5 body and 1.2 headings. Fonts and their licences go through the third-party asset manifest (ADR 0016). |
| Space | 4 px base: 4, 8, 12, 16, 24, 32, 48, 64. One page gutter, one card padding. |
| Surface | Three levels: page (`--background`), card (`--surface`, 1 px hairline, 12 px radius), raised (panels and sheets, one soft shadow). |
| Buttons | **Primary**: accent fill. **Secondary**: outline. **Quiet**: text only with an underline on focus and hover. Minimum 44 px target on touch, 24 px never undercut on desktop (WCAG 2.5.8). |
| Chips and badges | Pills with a text label; Condition always shows **sign + word** (ADR 0015), never colour alone. |
| Motion | 150–200 ms transitions on opacity and transform only, all removed under `prefers-reduced-motion`. Nothing animates on hover alone. |
| Theme | Unchanged mechanism: `prefers-color-scheme`, paper `#FFFFFF`/`#121212` page backgrounds, ink and paper tokens from ADR 0017. |

**Open point.** Foundations says the accent "is never a text colour". A primary button fills with the accent and puts text on it. Contrast is not the problem (white on `#7A2E1C` is about 10:1; `#1C1B1A` on `#F0A08C` is about 8:1) but the sentence must be amended to "never the colour of text on the page background; allowed as a fill behind text that meets 4.5:1".

**Spec text affected:** Foundations (UI backgrounds and accent sentence, i18n shell); a new short "Design tokens" subsection there.

## 4. Navigation and shell

**Today:** `Logo Name | Explore Archive Artists Contribute About | Search | IT EN | Account Sign out`.

**Proposed**

- **Desktop header**: logo and archive name at the left. Centre: three destinations, *Explore*, *Archive*, *Artists*. Right: a search field (icon button that expands to a labelled field; always a real `<input type="search">`), the language switcher as a compact `IT · EN`, **Contribute** as the one filled button, and an *Account* disclosure.
- **Account disclosure** holds: My contributions, Account, Moderation (Moderators only), Sign out. For anonymous visitors it reads *Sign in*.
- **About, legal, contacts, Data licence** move to the footer only. They are not destinations a visitor needs in the primary bar.
- **Phone**: the header shrinks to logo, search, and Account; a **bottom tab bar** carries *Explore*, *Archive*, **+ Contribute**, *Account*. The tab bar is a `<nav>`, has visible labels (no icon-only buttons), and sits under any bottom sheet.
- Without JavaScript the header and tab bar are plain links, as today.

Why: the destination count drops from six to three, the one action the project depends on becomes the most visible thing on every page, and the layout matches what visitors know from map and photo apps.

**Spec text affected:** Foundations (header and footer, acceptance criterion 35), Discovery (Header search), Contribution (Contribute hub entry point).

## 5. Discover (journey A)

### 5.1 Explore

**Today:** intro band, filter bar, map, then the list; on desktop the list sits beside the map, on a phone Map and List are exclusive.

**Proposed: map-first, list beside it.**

- **Desktop (≥ 60 rem):** a two-pane layout filling the viewport below the header. Left pane (about 26 rem): search field, a **Filters** button with a count badge, active-filter chips, the live count ("32 artworks in this area · page 1 of 2"), then the list cards. Right pane: the map, full height. Selecting a sign **replaces the list pane** with the Location panel (stratigraphy), with a "Back to list" button at the top and focus on the panel title. Closing restores the list and its scroll position. The panel no longer covers the map.
- **Phone:** the map fills the screen. A **bottom sheet** with three explicit states: *peek* (count and a "Show list" button), *list*, *Location*. Changing state is by buttons, never by drag alone (WCAG 2.5.7), though drag may be added as a progressive extra. The user can keep seeing the map while reading the list.
- **Filters** move from an always-open bar to a **dialog/panel** opened from the *Filters* button: grouped fieldsets (Condition, Expression type, Area, Years), a result preview on the Apply button ("Show 14 artworks"), and *Clear*. Chips stay visible outside it, each removable.
- **Intro band** shrinks to a one-line header under the nav on first visit ("Documenting Rome's urban art · About"), dismissible and remembered per browser. The empty-archive band remains as today, with a primary button.
- Behaviour that stays exactly as specified: one sign per Location (ADR 0019), Condition signs and the stack, clusters, `?superficie=` and `?mappa=` in the URL, "Selected" label on list entries, nothing on hover, the skip link and landmark order, the without-WebGL2 and without-JavaScript paths, 24 entries per page.

### 5.2 List card

Photo thumbnail at the left, 4:3, with the Condition badge (sign + word) over the bottom edge; title (serif); attribution summary; "where" line; two actions: the title link and *Show on map*. No change to the thumbnail rule (best Condition shown, neutral box when none).

### 5.3 Artwork page

**Today:** header text, then ten sections in a fixed order.

**Proposed**, same content, same order of *meaning*, different shape:

- **Top:** large gallery (first image 16:9, thumbnails below, each with its alt text and licence line one tap away), title and Condition badge beside or below it.
- **Desktop:** two columns. Main column: description, Attribution (certainty and evidence in words), Timeline, Sources, related Artworks. A sticky **side card**: *Where* (mini-map and place line), the Instance's actions grouped as **Add photos**, **Report a condition change**, **Propose an edit**, and the Revisions link.
- **Phone:** one column; the actions become a sticky bottom bar with a single *Contribute* button that opens a list of the three.
- An **in-page anchor row** under the title (Overview · Timeline · Sources) for orientation. It is plain links to `id`s.
- Dates, uncertainty, and attribution are rendered exactly as ADR 0015 and the Archive records spec require; only their layout changes.

**Spec text affected:** Discovery (Explore and Archive views, Selection and the side panel, Focus order and landmarks, Filters and Applying filters), Archive records (Public record pages order, actions placement).

## 6. Contribute (journeys B–D)

### 6.1 Entry

- **Contribute button** in the header and tab bar goes to the hub, now a screen of **four choice cards**, each one sentence and one illustration-free button: *Document a new artwork*, *Add photos to an existing artwork*, *Report a change or disappearance*, *Fix something that is wrong*. The last three first ask which artwork (a search field), which removes the current need to find the record page first. Record-page actions deep-link past that question.
- Anonymous visitors see the cards too; the sign-in step appears **when they pick one**, with `?next=`, as the spec already routes it.

### 6.2 New Artwork: from seven steps to four

Today: Location → Documentation → The Artwork → Attribution → Creation date → Sources → Review.

| # | Proposed step | Contains | Required |
|---|---|---|---|
| 1 | **Photos and place** | Upload files (Observed date, Rights basis, Creator credit, licence, alt text per file; initial Condition) then the Location | Files, Location, initial Condition |
| 2 | **The artwork** | Title or explicit *Untitled*, Expression types, description, Series | Title choice, type |
| 3 | **Details** *(optional)* | Attribution (unknown is the default and an explicit choice), Creation date, Sources | none beyond rules already in force (`confirmed` needs a citation, etc.) |
| 4 | **Review and submit** | Preview in the editorial label, note to Moderators, terms | Terms when needed |

- Every existing field survives; nothing is dropped. Steps 3 and 4 of today's list are **sections** of the new step 3, each collapsible, with a one-line summary when collapsed.
- **Start with the photo**: on a phone the first action is "Take or choose a photo", the most natural way to start. The Observed date prefills from EXIF as a labelled suggestion, as the spec has it.
- **A persistent progress header**: "Step 2 of 4 · The artwork", the step list below it as words (complete / to complete / to fix), and a **fixed bottom bar** with *Back*, *Next*, and "Saved automatically · 10:42". Navigation stays free, as the spec says.
- **A "what's still needed" summary** in the Review step lists missing required items as links to their fields, so the first submit rarely fails. Validation still runs on submit; this only surfaces the same rules earlier, non-blocking.
- **Inline help instead of paragraphs**: the reminder about people and number plates, the licence note, and the "location is the artwork's, not yours" note become short helper lines under the control they concern, each with a *Learn more* link to the guidelines.

**An idea that needs a decision, not a given:** suggest the Location from the photo's EXIF GPS. It would save the most effort in the whole flow, but it touches privacy (the photographer's position is not the artwork's position, and EXIF position must be stripped from published files). It is **not** in the prototype's behaviour; it is listed as an open question.

### 6.3 Other editors

The same shell (progress header, bottom bar, autosave line) applies to History event, Edit, Add documentation, Artist, Area, Merge, and Unmerge. Their steps are unchanged; the visual language is shared so a contributor learns it once. History events keep the type groups, now as radio cards with the one-line description visible, the Observed date, and a live Evidence level readout.

### 6.4 My contributions

A list of cards, each with the status **in words** and a small step-by-step line (Draft → Submitted → Decision), the next action, and the date. Filter by status as in the spec; no counts, rankings, or streaks.

**Spec text affected:** Contribution and moderation (Submission form structure and the kind/steps table, Contribute hub and My contributions, Entry points), Foundations (Location-step wording only if EXIF suggestion is accepted).

## 7. Sign-in and account

- **One field first**: "Email", a single *Continue* button, and one line of reassurance ("We'll email you a code. No password."). Passkey sign-in appears as a secondary button, only when the browser supports it, above the email field.
- **Registration** keeps its fields (display name, age confirmation, terms) and appears after the code step, as today, with shorter copy and the legal text one tap away.
- The `?next=` return stays; after sign-in the user lands back **on the thing they were doing**, with a toast "Signed in as …" in a polite live region.
- **Account page**: sections as cards (Profile, Sign-in methods, Data and deletion), each short; destructive actions at the end with explicit confirmation.

**Spec text affected:** Foundations §2 (auth pages copy and layout only; behaviour unchanged).

## 8. Moderation (journey E)

- The Queue becomes a **master–detail** layout on desktop: the list at the left, the selected Submission at the right, so a Moderator can go through several without page loads. On a phone it is two screens.
- Status, kind, and flags are text badges. The Review checklist stays fixed and always visible beside the decision buttons, as specified.
- The current-against-proposed comparison keeps its rules (stacked below 600 px, current left, proposed right). Nothing in the "first decision wins" model changes.

**Spec text affected:** Contribution and moderation (Queue, Submission page layout).

## 9. What does not change (invariants check)

| Invariant | How the proposal stays within it |
|---|---|
| Submissions are not archive records | Preview stays labelled "Proposed · not public until approved", hatched with a dashed outline. |
| Disappearance is never deletion | Disappeared Artworks stay in every default result; the Condition badge shows the word. |
| Uncertainty is first-class | Dates, attribution, and approximate positions keep their wording and readouts; only layout moves. |
| No engagement mechanics | No likes, follower counts, streaks, badges, trending, or "contributor of the month". My contributions shows status only. |
| Accessibility (WCAG 2.2 AA) | No state by colour alone; nothing on hover; drag only as an extra to buttons; 44 px touch targets; focus moves to panel titles; reduced-motion respected. Every new screen must pass axe in `it` and `en`. |
| Map-provider agnostic | The map stays behind the existing `MapControl`; the layout reserves a rectangle and a panel, nothing about MapLibre. |
| i18n from day one | All new strings go through Paraglide; layouts tolerate longer German or Italian strings and `dir=rtl`. |
| Multi-instance | Tokens read the Instance accent and logo; no Rome-specific layout. |

## 10. Rollout

Each step is a separate PR and none depends on the next.

| Phase | Content | Needs |
|---|---|---|
| 0 | **Validate**: five-person test on the prototype (two people who have never seen TART, one phone-only, one keyboard-only, one with a screen reader). Tasks: find an artwork near a place, find out what happened to it, add a photo. | Decision to run it. |
| 1 | **Tokens and components** (buttons, chips, cards, badges, dialog, sheet) in `app.css` and `lib/ui/`. No layout change. | Foundations spec edit (accent sentence, design tokens). |
| 2 | **Shell**: header, account disclosure, bottom tab bar, footer. | Foundations and Discovery spec edits. |
| 3 | **Explore** two-pane, bottom sheet, filter dialog. | Discovery spec edit. |
| 4 | **Artwork page** layout. | Archive records spec edit. |
| 5 | **Contribution** hub, 4-step form shell (lands with the contribution tickets in progress, so the spec edit should come first to avoid building the 7-step form twice). | Contribution spec edit. |
| 6 | Sign-in, account, moderation layout. | Small spec edits. |

**Timing note:** the contribution implementation is under way on another branch. Phase 5's spec change should be agreed before the editor UI is built.

## 11. Open questions

1. **Typeface**: a bundled variable sans plus a serif, or keep system fonts and spend the effort elsewhere? Bundling adds licence entries to the asset manifest and about 60–100 KB of fonts.
2. **EXIF location suggestion** (6.2): worth the privacy review?
3. **Bottom tab bar versus a header menu on phones**: the tab bar is more discoverable, but takes screen height from the map and sheet.
4. **Dismissible intro band**: is remembering it in `localStorage` acceptable under the privacy policy (a per-viewer convenience, no tracking), or should the band simply be shorter and always shown?
5. **Four steps versus keeping seven**: the 7-step list encodes the spec's modules; the 4-step version groups them. Confirm no module relies on a separate step boundary (autosave, resume-to-first-incomplete).

## 12. Out of scope

A logo or brand redesign (Foundations leaves it out of scope), new features (no social, no comments, no ranking), changes to the data model, the lifecycle, the permissions, or the API.
