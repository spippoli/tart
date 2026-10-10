# Foundations

Feature spec 1 of 7 in the [delivery order](index.md#delivery-order). It covers what every other feature builds on: **Instance configuration**, authentication and sessions, storage and the media pipeline, the i18n shell (layout, navigation, language routing, account and About pages), and the Operator CLI. It depends on no other feature spec.

The invariants in [`CLAUDE.md`](../../CLAUDE.md), the vocabulary in [`GLOSSARY.md`](../../GLOSSARY.md), and the ADRs apply throughout and are cited, not restated ([spec index, Sources of truth](index.md#sources-of-truth)).

## References

**ADRs applied**

| ADR | What this spec takes from it |
|---|---|
| [0001](../adr/0001-one-instance-per-deployment.md) | One database per **Instance**; Users are local to it |
| [0004](../adr/0004-mvp-tech-stack.md) | Stack, topology, storage adapter, upload path, media processing libraries, worker, SMTP adapter, CI checks |
| [0005](../adr/0005-passwordless-in-app-auth.md) | Email one-time code, passkeys, session model, CSRF, authentication interface, roles in the database |
| [0008](../adr/0008-single-content-language-and-prefixed-ui-languages.md) | **Content language** vs **UI language**, prefixed routing, root redirect, message catalogues, formatting, `lang`/`dir` |
| [0009](../adr/0009-instance-configuration-as-validated-files.md) | The configuration directory, environment variables, validation, versioning, vocabularies, identity, community and legal keys, operational keys, CLI role grants |
| [0010](../adr/0010-public-url-scheme.md) | Translated path segments are UI strings; 301 and 410 behaviour the shell must render |
| [0011](../adr/0011-provisional-software-license.md) | "Powered by TART" is shown by default and may be removed (§7); dependency licence tiers (§8) |
| [0012](../adr/0012-per-file-licence-with-rights-basis.md) | EXIF handling, private originals, public rendition cap, licence allowlist, `min_age` |
| [0013](../adr/0013-hide-not-delete-for-legal-removals.md) | Purge and data exports run from the Operator CLI; account deletion is self-service |
| [0016](../adr/0016-licence-policy-for-map-assets-and-data.md) | Map attribution as a non-empty `{text, url}` list; courtesy credits on the About TART page from the asset manifest |
| [0017](../adr/0017-map-cartography-style.md) | The Instance accent is also validated against the map fills; dark theme follows the UI theme |

**Glossary terms used**: **Instance**, **Operator**, **Instance configuration**, **Data licence**, **Licensor**, **UI language**, **Content language**, **User**, **Moderator**, **Submitter**, **Submission**, **Submission status**, **Documentation item**, **Creator credit**, **Rights basis**, **Expression type**, **Surface type**, **Decision message**, **Area**, **Location**, **Withdrawal**, **Purge**, **Notice**.

**Resolution comments incorporated**: [Platform vs instance configuration boundary](https://github.com/spippoli/tart/issues/6), [Tech stack decision](https://github.com/spippoli/tart/issues/13), [i18n strategy: UI vs multilingual content](https://github.com/spippoli/tart/issues/16), [Information architecture and page inventory](https://github.com/spippoli/tart/issues/15) (shell, navigation, sign-in, account, About pages), [Submission and moderation lifecycle](https://github.com/spippoli/tart/issues/5) (draft expiry), [Research: media pipeline and storage within budget](https://github.com/spippoli/tart/issues/10) (pipeline outline), [Content rights and GDPR product rules](https://github.com/spippoli/tart/issues/14) (EXIF, minimum age, account), [Submission form flow](https://github.com/spippoli/tart/issues/27) (per-file upload fields, server-side drafts).

## Problem Statement

TART must run as many independent local archives, each with its own name, territory, languages, policies, and licences, without any of that being hardcoded for Rome. An **Operator** needs a way to describe their archive, start it on a small server (Rome: at most €20/month excluding VAT and off-site backups), and know before going live that the description is complete and valid. Visitors need a coherent, accessible interface in their own UI language even though the archive's content is written in one Content language. Contributors need to sign in without yet another password and to upload photos and PDFs from a phone in the street without leaking where they stood when they took the picture. Every later feature (records, map, Submissions, legal actions, notifications) needs the same configuration, identity, storage, and translation services underneath it.

## Solution

A single platform build, configured per Instance from a secret-free directory of files plus environment variables, validated in full at startup. Users sign in with a one-time code sent by email and may add passkeys; FastAPI owns an opaque, revocable session. Uploaded files go through a quarantine and a background worker that validates them, strips identifying metadata, and produces public renditions, while every object stays private and is served through the app. The SvelteKit shell renders every page under a UI-language prefix, with the Instance's identity in the header, "Powered by TART" in the footer, and the Operator's own texts on About pages in the Content language. A `tart` command-line tool gives the Operator the actions that have no UI in the MVP: checking configuration and granting roles, with Purge and data exports added by later specs.

## User Stories

**Operator: configuration**

1. As an Operator, I want to describe my archive in a directory of plain text files, so that I can set it up without a configuration UI.
2. As an Operator, I want that directory to hold no secrets, so that I can version it in a public repository and use it unchanged in staging and production.
3. As an Operator, I want secrets and infrastructure wiring in environment variables, so that credentials never end up in the published configuration.
4. As an Operator, I want to run `tart config check` before a deploy, so that I find configuration errors before the service fails to start.
5. As an Operator, I want every configuration error reported at once, so that I don't fix them one restart at a time.
6. As an Operator, I want a misspelled or unknown key to be an error, so that a typo is never silently ignored.
7. As an Operator, I want a JSON Schema for the configuration, so that my editor autocompletes and checks keys.
8. As an Operator, I want the service to refuse to start when my configuration's `config_version` doesn't match the platform, so that an upgrade never runs on a configuration shape it doesn't understand.
9. As an Operator, I want to choose my Instance's Expression types, Surface types, and Decision message reasons, with labels in each enabled UI language, so that the vocabulary fits my city.
10. As an Operator, I want to retire a vocabulary entry instead of deleting it, so that existing records keep their values.
11. As an Operator, I want startup to fail if I removed a vocabulary key still in use, so that no record ends up with a dangling value.
12. As an Operator, I want to set my archive's name, short description, logo (light and dark), favicon, and accent colour, so that the archive has its own identity.
13. As an Operator, I want to be told at startup if my accent colour fails WCAG AA contrast, so that I can't ship an inaccessible theme.
14. As an Operator, I want to declare my country, place name, time zone, boundary polygon, and default map view, so that the archive is about my territory.
15. As an Operator, I want to choose the Content language, the enabled UI languages, and the default UI language, so that the archive speaks to my community.
16. As an Operator, I want to set the registration mode (`open`, `invite`, or `closed`) and the minimum age, so that registration matches my community's policy and local law.
17. As an Operator, I want to choose the Data licence and the licences allowed for uploaded files from a platform list, so that the archive stays reusable.
18. As an Operator, I want to write my About page, editorial guidelines, contribution policy, terms of use, and privacy policy as Markdown files, so that I can edit them like any document.
19. As an Operator, I want to set the draft expiry period and the maximum upload size, so that storage stays within my budget.
20. As an Operator, I want to choose local disk or an S3-compatible bucket for storage, so that I can start small and move to object storage later.
21. As an Operator, I want to configure SMTP, so that sign-in codes and notifications reach Users.

**Operator: CLI**

22. As an Operator, I want to grant the Moderator role to an email address from the command line, creating the User if needed, so that I can bootstrap moderation without any special-cased account.
23. As an Operator, I want the CLI to share the platform's validation, so that `tart config check` gives the same answer as startup.

**Visitor: shell and languages**

24. As a visitor, I want `/` to send me to my language (from my earlier choice, then my browser, then the archive default), so that I land in a language I read.
25. As a visitor, I want every page to have a language prefix in its URL, so that I can share a link in a specific language.
26. As a visitor, I want a language switcher that keeps me on the same page, so that I don't lose my place.
27. As a visitor, I want only the languages the archive enables to be offered, so that I never reach a half-supported language.
28. As a visitor reading in English, I want Italian archive content marked with its language, so that my screen reader pronounces it correctly.
29. As a visitor, I want dates and numbers formatted for my UI language and the archive's time zone, so that they read naturally.
30. As a visitor, I want the archive's own name and logo in the header and "Powered by TART" in the footer, so that I know whose archive this is and what runs it.
31. As a visitor, I want About pages with the archive's guidelines, policies, contacts, and data licence, so that I can understand and trust the archive.
32. As a visitor, I want an About TART page in my UI language, so that I know what the platform is and who made its parts.
33. As a visitor on a phone, I want a "Menu" button rather than hover menus, so that I can navigate by touch and keyboard.
34. As a keyboard or screen-reader user, I want every shell control reachable and labelled, so that I can use the archive without a mouse.
35. As a visitor, I want clear error pages (403, 404, 410) in my UI language, so that I understand what happened.

**User: sign-in and account**

36. As a contributor, I want to sign in with a code sent to my email, so that I don't need another password.
37. As a contributor, I want to add a passkey, so that I can sign in faster on my own devices.
38. As a contributor who clicked "Contribute" while signed out, I want to come back to where I was after signing in, so that I don't lose my place.
39. As a new contributor, I want the sign-in page to tell me whether I can register on this archive, so that I know what to expect under `open`, `invite`, or `closed`.
40. As a new contributor, I want to declare that I meet the minimum age, so that I can register lawfully.
41. As a User, I want to set my display name, which may be a pseudonym, so that I choose how I'm credited publicly.
42. As a User, I want to set my preferred UI language, so that the interface and my emails use it.
43. As a User, I want to manage my passkeys and email address and delete my account from one Account page, so that I control my data.
44. As a User, I want signing out to end my session immediately, so that a shared device is safe.
45. As a User, I want no public profile, so that the archive never ranks or displays me.

**User: uploads**

46. As a contributor on a phone, I want to upload photos straight from the camera, including HEIC, so that I can document an Artwork on the spot.
47. As a contributor, I want the photo's capture date and position offered only as suggestions for the Observed date and the map pin, so that I stay in control of what is recorded.
48. As a contributor, I want the GPS and device identifiers removed from what the archive stores, so that my own position is never published.
49. As a contributor, I want an upload that is too large or not a supported file to fail with a clear message, so that I can fix it.
50. As a contributor, I want my draft's files to stay private until approval, so that nothing I upload is public by accident.

**Moderator**

51. As a Moderator, I want the Moderation entry in the user menu, so that I reach the queue quickly.
52. As a signed-in User without the role, I want an explanatory 403 on Moderation pages, so that I know why I can't see them.

**Platform maintainers**

53. As a maintainer, I want a missing message key to fail the build, so that no UI language ships incomplete.
54. As a maintainer, I want the API to return stable error codes with parameters, so that every error is translated by the frontend.
55. As a maintainer, I want the TypeScript API client generated from FastAPI's schema with a drift check in CI, so that frontend and backend never disagree silently.
56. As a maintainer, I want CI to reject dependencies outside the licence tiers, so that the software stays within PolyForm Noncommercial's terms.

## Implementation Decisions

### Modules

Each module has a narrow interface; the provider boundaries (authentication, storage, email, map) are ports with adapters, as the implementation principles in `CLAUDE.md` require.

| Module | Interface (what callers see) | Lives in |
|---|---|---|
| Instance configuration | Load and validate a directory plus environment into one immutable, typed configuration, or a complete list of errors; expose the public subset | backend (`api`, `worker`, CLI) |
| Authentication | Request a code, verify a code, register and verify a passkey, sign out; behind an authentication interface whose only MVP implementation is the built-in one | backend |
| Session | Resolve the current User and roles from a request; create and revoke sessions | backend |
| Storage | Put, get (streamed, with byte ranges), and delete objects by key, in a quarantine or a permanent area; two adapters: local filesystem and S3-compatible | backend |
| Media pipeline | Enqueue processing of a quarantined upload; jobs that validate, sanitise, and derive renditions or previews | `worker` |
| Email | Send a rendered message; one SMTP adapter | backend (`worker`) |
| Message catalogues | Frontend (Paraglide) and backend (emails) catalogues, both under the missing-key check | frontend, backend |
| Shell | Root layout, header, navigation, footer, language routing, sign-in, account, About, and error pages | frontend |
| Operator CLI | `tart` command with subcommands | backend |

The map module ([ADR 0004](../adr/0004-mvp-tech-stack.md)) is specified by the Discovery spec; Foundations only loads and validates the map configuration.

### 1. Instance configuration

**Layers** (from [#6](https://github.com/spippoli/tart/issues/6)):

| Layer | Held in | Changed by |
|---|---|---|
| Platform | Code | Releases: domain model, closed vocabularies, UI languages and messages, map module, TART brand and "Powered by TART" |
| Instance configuration | The configuration directory | The Operator, then a restart |
| Community archive | Database | Approved **Submissions** only (every Archive record, including **Areas**) |
| User | Database | The User (profile, preferred UI language, own Submissions); roles by the Operator through the CLI |

**Configuration directory.** Read-only and secret-free ([ADR 0009](../adr/0009-instance-configuration-as-validated-files.md)): `instance.toml`, separate vocabulary files, the Operator's Markdown texts (About, editorial guidelines, contribution policy, terms of use, privacy policy), the SVG logo (light and dark), the favicon, a MapLibre style file, and a GeoJSON boundary. The PMTiles file is not in the directory; it lives in a data volume.

**Environment variables.** Every secret and all infrastructure wiring: database URL, public base URL, storage choice and S3 credentials, SMTP settings, session key, PMTiles volume path. Caddy receives `max_upload_mb` through the environment as well.

**Loading and validation.**
- Only FastAPI's image (`api` and `worker`) reads the directory, with `tomllib`, into Pydantic models at startup.
- Invalid configuration stops the service and reports **every** error, not only the first. Unknown keys are errors.
- `tart config check` runs the same validation. A JSON Schema exported from the models supports editors.
- No hot reload: a change needs a restart.
- `config_version` starts at 1 and is bumped by any platform release that changes the configuration's shape. A mismatch stops the service and points to the release notes. There is no automatic migration.
- Checks that go beyond the shape: an accent colour that fails WCAG AA contrast against the light and dark backgrounds ([ADR 0009](../adr/0009-instance-configuration-as-validated-files.md)) and against the map fills ([ADR 0017](../adr/0017-map-cartography-style.md)); a missing vocabulary label for any enabled UI language ([ADR 0008](../adr/0008-single-content-language-and-prefixed-ui-languages.md)); an enabled UI language the platform image doesn't contain; an empty map attribution list ([ADR 0016](../adr/0016-licence-policy-for-map-assets-and-data.md)); a missing terms of use, privacy policy, or DSA contact; a vocabulary key used in the database but absent from the files.

**Open vocabularies** (Expression type, Surface type, Decision message reasons): each entry has an immutable `key` (what the database stores), one label per enabled UI language, an order, an optional description, and a `retired` flag. Entries are never deleted; a retired entry stays displayed and filterable on existing records but is not selectable in new Submissions. The platform ships the brief's §9 list as a starting vocabulary.

**Closed vocabularies** stay in the platform because code reasons over them: Condition, History event types, Submission status, Attribution certainty, Uncertain date precision and qualifier. Their labels are platform UI messages.

**No custom fields.** Configurability stops at vocabularies; an Instance cannot add fields to the core model.

**Public subset.** The SvelteKit frontend never reads the directory. It gets the public subset of the configuration (identity, languages, geography, map attribution, vocabularies with labels, registration mode, licences, Operator texts) from an API endpoint and caches it.

**Operator texts** are Markdown in the Content language. They are not moderated and have no Revisions; their history is the configuration repository's history.

### 2. Authentication and sessions

**Sign-in** ([ADR 0005](../adr/0005-passwordless-in-app-auth.md)):
- The User enters an email and receives a one-time code: 6 digits, valid 10 minutes, with attempt limits and rate limits per email and per IP.
- Optional passkeys through `py_webauthn`, added and removed on the Account page.
- No passwords and no social login in the MVP.
- The page is `/<ui-language>/accedi` (`/en/sign-in`) and offers email code and passkey. Its registration text depends on the `registration` mode.

**Registration.**
- `open`: anyone who meets the minimum age may register.
- `invite`: only invited people may register. Who issues invites, and how, is not decided (see Open items).
- `closed`: no self-registration. The Operator can still create a User through `tart users grant` ([ADR 0009](../adr/0009-instance-configuration-as-validated-files.md)).
- There is no manual account approval in any mode.
- The minimum age is `min_age` from the configuration and is self-declared at registration ([ADR 0012](../adr/0012-per-file-licence-with-rights-basis.md)).
- Acceptance of the Instance's versioned terms happens before the first Submission, not at registration ([ADR 0012](../adr/0012-per-file-licence-with-rights-basis.md)); it is specified by the Contribution and moderation spec.

**Sessions.**
- FastAPI owns the session: an opaque session ID stored in PostgreSQL (no JWT), so revocation is immediate.
- Cookie: `HttpOnly; Secure; SameSite=Lax`, on the single origin Caddy serves.
- During server rendering, SvelteKit forwards the User's cookie when it calls FastAPI over the internal network.
- CSRF: `SameSite=Lax`, an `Origin` check on state-changing requests, and a required custom header on API calls.
- Security parameters (code lifetime and attempts, rate limits, session lifetime) are platform constants that configuration cannot weaken ([ADR 0009](../adr/0009-instance-configuration-as-validated-files.md)).

**Authentication interface.** Authentication sits behind an interface so a later Instance can plug in an external OIDC provider; only the built-in implementation ships, and the authentication method is not configurable in the MVP.

**Roles.** Roles live in TART's database whatever the authentication method. In the MVP the only role is Moderator, assigned by the Operator through the CLI. No role is special-cased in code for bootstrapping. Who may approve what is decided by the Contribution and moderation spec ([Moderation roles and permissions](https://github.com/spippoli/tart/issues/43)).

**Access rules owned by the shell** ([#15](https://github.com/spippoli/tart/issues/15)):
- An anonymous user who triggers a contribution action goes to sign-in with `?next=` and returns there afterwards.
- On `/<ui-language>/moderazione`, an anonymous user is sent to sign-in; a signed-in User without the Moderator role gets an explanatory 403.
- There are no public User profiles.

**Account** (`/it/account`, `/en/account`): display name (may be a pseudonym; it is what public Revisions pages show, [#14](https://github.com/spippoli/tart/issues/14)), preferred UI language (also used for the User's emails, [ADR 0008](../adr/0008-single-content-language-and-prefixed-ui-languages.md)), passkeys, email, and account deletion. The deletion flow (erasing email and credentials, a stable pseudonym, deleting drafts, retracting open Submissions) is specified by the Rights and legal actions spec ([ADR 0013](../adr/0013-hide-not-delete-for-legal-removals.md)). My contributions (`/it/account/contributi`) belongs to the Contribution and moderation spec.

**Email.** A generic SMTP adapter configured through the environment, with Mailpit in development (Compose profile). Emails are rendered by the `worker` from the backend message catalogue in the recipient's preferred UI language. Reliable delivery is critical: if email is down, nobody without a passkey can sign in ([ADR 0005](../adr/0005-passwordless-in-app-auth.md)).

### 3. Storage and media pipeline

**Storage adapter** ([ADR 0004](../adr/0004-mvp-tech-stack.md)):
- Two implementations: local filesystem (the minimal default) and S3-compatible. Rome uses Hetzner Object Storage. There is no self-hosted S3 server in the reference stack.
- All objects are private and served through the app. Whether a file is public is a database flag (pending Submission, approved, withdrawn), never a move or a deletion of the object.
- Uploaded files are immutable once stored ([#5](https://github.com/spippoli/tart/issues/5)).

**Upload path.**
1. The browser streams a multipart upload to FastAPI through Caddy; uploads never pass through SvelteKit.
2. Size limits are enforced by both Caddy and the app, from `max_upload_mb`.
3. FastAPI writes the file to a quarantine area and enqueues a processing job.

**Processing** (in the `worker`, Procrastinate on PostgreSQL, same image as `api`, with its own memory and time limits). Following the outline of [#10](https://github.com/spippoli/tart/issues/10) as adopted by [ADR 0004](../adr/0004-mvp-tech-stack.md):
1. Detect the file type from its content (magic bytes), not from its name or declared type.
2. Enforce size and pixel limits (Pillow's decompression-bomb guard, tightened), fully decode the file, and reject it if decoding fails.
3. Read the EXIF capture date and GPS **as suggestions only**, returned to the Submission form to prefill the Observed date and a map pin ([ADR 0012](../adr/0012-per-file-licence-with-rights-basis.md)). They are never stored as a Location: the artwork location is not the submitter's location.
4. Strip GPS and device identifiers from the stored original. The original stays private.
5. Images: apply EXIF orientation and produce WebP renditions with Pillow, with no EXIF, XMP, or IPTC metadata. Public renditions are capped at a resolution set in the Instance configuration ([ADR 0012](../adr/0012-per-file-licence-with-rights-basis.md)). HEIC is decoded with `pi-heif` (decode-only).
6. PDFs: render a first-page preview with `pypdfium2`.
7. PyMuPDF (AGPL) and libvips are excluded ([ADR 0004](../adr/0004-mvp-tech-stack.md), [ADR 0011](../adr/0011-provisional-software-license.md)).

The per-file fields a Submitter fills in (Observed date, **Rights basis**, **Creator credit**, licence from the allowlist) are specified by the Contribution and moderation spec ([#27](https://github.com/spippoli/tart/issues/27)); a link is linked, never uploaded.

**Lifecycle of uploaded files.**
- Draft media are server-side and private, and never public ([#5](https://github.com/spippoli/tart/issues/5)).
- A draft never edited is discarded after 24 hours ([#15](https://github.com/spippoli/tart/issues/15)).
- An abandoned draft expires after `draft_expiry_days`, and its media are deleted ([#5](https://github.com/spippoli/tart/issues/5)).
- The worker also cleans up abandoned uploads ([ADR 0004](../adr/0004-mvp-tech-stack.md)).
- Media of approved Documentation items are never deleted except by a Purge ([ADR 0013](../adr/0013-hide-not-delete-for-legal-removals.md)).

**Serving.** Files are streamed by the app with an authorisation check: an approved, non-withdrawn Documentation item's renditions are public; pending media are visible only to their Submitter and to Moderators; originals are never public. PMTiles are served by Caddy from the data volume (Discovery spec).

### 4. i18n shell

**Languages** ([ADR 0008](../adr/0008-single-content-language-and-prefixed-ui-languages.md), [#16](https://github.com/spippoli/tart/issues/16)):
- UI languages belong to the platform. Each ships complete in the single prebuilt frontend image; an Instance enables a subset and picks a default. A UI language is added only at platform level, complete. There is no translation platform in the MVP.
- Every UI language is URL-prefixed (`/it/…`, `/en/…`), with translated pathnames. Disabled UI languages answer 404.
- Only the root `/` redirects: by cookie, then `Accept-Language`, then the Instance default.
- The language switcher in the header offers only the enabled UI languages, keeps the same page, and sets the cookie.
- `hreflang` and `x-default` are written once in the root layout.
- Paraglide JS with pinned versions; a missing message key is a build error. The backend catalogue for emails is held to the same check.
- The API returns stable error codes with parameters; the frontend translates them.
- Archive content and Operator texts are in the Content language, never translated, and rendered with their own `lang` (and `dir`) whatever the UI language. Sources and textual Documentation items may carry their own language tag.
- Configured vocabulary labels are UI strings, one per enabled UI language, from the configuration.
- Dates, numbers, and distances use `Intl` with the UI language and the Instance's explicit time zone. Each Uncertain date precision and qualifier combination has its own platform message.
- Styles use CSS logical properties and set `dir` from the start; right-to-left UI languages are not tested in the MVP.

**Layout** ([#15](https://github.com/spippoli/tart/issues/15)):
- **Header**: the Instance's logo and archive name (the primary identity); primary navigation Explore · Archive · Artists · Contribute · About; a search field that submits to the list view with `?q=` (behaviour in the Discovery spec); the language switcher; the user menu: Sign in, or My contributions / Account / Moderation (Moderators only) / Sign out.
- **Mobile**: navigation sits behind a "Menu" disclosure button, never hover.
- **Footer**: "Powered by TART", linking to the internal About TART page; the Data licence; contacts; legal links. "Powered by TART" is rendered by the platform, not a configuration key; it is shown by default and is permitted, not mandatory ([ADR 0011 §7](../adr/0011-provisional-software-license.md)).
- **Browser title**: `<Page> — <Archive name>`.
- **Theme**: light and dark logo variants, the accent checked against both themes. The map follows the UI theme ([ADR 0017](../adr/0017-map-cartography-style.md)).

**About pages.** A hub at `/it/informazioni` (`/en/about`) with subpages rendering the Operator's Markdown texts in the Content language, plus contacts (general and DSA), the Data licence, and the platform's About TART page. About TART is rendered by the platform, translated into every UI language, and lists the courtesy credits generated from the third-party asset manifest ([ADR 0016](../adr/0016-licence-policy-for-map-assets-and-data.md)).

**Routes owned by this spec** (path segments are UI strings and may change before launch, [ADR 0010](../adr/0010-public-url-scheme.md)):

| Page | `it` | `en` |
|---|---|---|
| Root | `/` → redirect | |
| Sign in | `/it/accedi` | `/en/sign-in` |
| Account | `/it/account` | `/en/account` |
| About hub | `/it/informazioni` | `/en/about` |
| About subpages | `/it/informazioni/{linee-guida, policy-contributi, termini, privacy, contatti, licenza-dati, tart}` | `/en/about/{guidelines, contribution-policy, terms, privacy, contact, data-licence, tart}` |
| Errors | 403, 404, 410 | |

The other routes of the [#15](https://github.com/spippoli/tart/issues/15) route table belong to the specs that own those pages. The shell provides the error-page frame; the content of the 410 page for withdrawn records is specified by the Rights and legal actions spec.

### 5. Operator CLI

A `tart` command for the actions that have no UI in the MVP. It uses the same configuration models and validation as the services.

| Command | Behaviour | Specified in |
|---|---|---|
| `tart config check` | Runs the full startup validation and reports every error | This spec |
| `tart users grant moderator <email>` | Grants the Moderator role, creating the User if needed | This spec |
| Purge | Permanently erases content already withdrawn or redacted, only when the law requires it | Rights and legal actions |
| User data export | Produces the Art. 15 and Art. 20 exports on request | Rights and legal actions |

Command names other than the first two are left to the specs that own them.

### Topology and stack

As in [ADR 0004](../adr/0004-mvp-tech-stack.md): a monorepo (`backend/`, `frontend/`, `deploy/`); services `caddy`, `frontend`, `api`, `worker`, `db` (PostgreSQL + PostGIS from the upstream image, unmodified), and `mailpit` in development only. Alembic migrations run at `api` startup. Reference sizing is 4 GB RAM minimum, 8 GB recommended. Backups, upgrades, and monitoring belong to the Operations and portability spec.

## Testing Decisions

A good test exercises a module through its external interface and asserts observable behaviour (an HTTP response, a stored object, a rendered page, an error list), never internal calls. The repository has no code yet, so there is no prior art; these seams are the first.

- **Configuration loader**: a directory and an environment in, a validated configuration or a complete error list out (pytest). Fixtures: Rome's configuration as a valid case; one directory per failure (unknown key, wrong `config_version`, missing label, low-contrast accent, empty attribution, missing legal text). The same fixtures run through `tart config check`.
- **Authentication and sessions**: through the HTTP API with FastAPI's test client and an email adapter that captures messages. Covers code expiry and attempt limits, registration under each `registration` mode, session revocation on sign-out, and the CSRF rules (missing custom header, foreign `Origin`).
- **Storage**: one contract test suite run against both adapters (put, streamed get with byte ranges, delete, quarantine vs permanent). How the S3 adapter is exercised in CI is left to implementation.
- **Media pipeline**: worker jobs fed fixture files (JPEG with GPS EXIF, rotated JPEG, HEIC, PNG, PDF, a truncated file, a decompression bomb, a file whose extension lies). Asserts on the stored outputs: no GPS or device identifiers in the original, no metadata in renditions, orientation applied, the rendition cap respected, rejections with error codes.
- **Shell**: Playwright with axe over the shell pages in every enabled UI language, at desktop and mobile widths: root redirect order, switcher, disabled-language 404, `lang` on content, keyboard-only navigation of the Menu button and user menu.
- **CI checks** ([ADR 0004](../adr/0004-mvp-tech-stack.md), [ADR 0011](../adr/0011-provisional-software-license.md), [ADR 0016](../adr/0016-licence-policy-for-map-assets-and-data.md)): missing message keys (frontend and backend), OpenAPI client drift, the dependency licence allow-list, and the third-party asset manifest.

## Acceptance criteria

**Instance configuration**
1. With Rome's configuration directory and a complete environment, `api` and `worker` start; `tart config check` exits successfully.
2. A configuration with several errors stops startup and lists all of them; `tart config check` prints the same list and exits with a failure status.
3. An unknown key, a `config_version` different from the platform's, a missing vocabulary label for an enabled UI language, an enabled UI language missing from the image, an empty map attribution list, or a missing terms of use, privacy policy, or DSA contact each fail validation.
4. An accent colour below WCAG AA contrast against the light or dark background, or against the map fills of [ADR 0017](../adr/0017-map-cartography-style.md), fails validation.
5. Removing a vocabulary key that the database uses fails startup; marking it `retired` succeeds, and the value still displays on existing records.
6. The configuration directory contains no secret; every secret and connection setting is read from the environment.
7. The frontend reads configuration only through the public API endpoint, and that endpoint exposes no environment value.
8. Changing a configuration file has no effect until a restart.

**Authentication and sessions**
9. Requesting a code sends a 6-digit code by email; it is rejected after 10 minutes and after the attempt limit; repeated requests are rate-limited per email and per IP.
10. Under `open`, a new email can register after a self-declared minimum-age confirmation; under `closed`, it cannot; under any mode, no manual approval step exists.
11. A User can add a passkey on the Account page and then sign in with it.
12. The session cookie is `HttpOnly`, `Secure`, and `SameSite=Lax`; after sign-out, the same session ID is rejected on the next request.
13. A state-changing API request without the required custom header, or with a foreign `Origin`, is refused.
14. Server-rendered pages show the signed-in state, because SvelteKit forwards the cookie to FastAPI.
15. An anonymous contribution action leads to sign-in with `?next=` and returns to the original page afterwards.
16. `/it/moderazione` sends an anonymous user to sign-in and answers a signed-in non-Moderator with a translated, explanatory 403; the Moderation menu entry appears only for Moderators.
17. `tart users grant moderator <email>` gives the role to an existing User, or creates the User with the role.

**Storage and media**
18. With either storage adapter, an uploaded file is stored privately and can be fetched only through the app.
19. An upload above `max_upload_mb` is refused by Caddy and by the app with a translatable error code.
20. A file whose content is not a supported type, or that fails to decode, is rejected regardless of its extension.
21. After processing, the stored original has no GPS or device identifiers, renditions carry no EXIF, XMP, or IPTC metadata, and EXIF orientation is applied.
22. No public rendition exceeds the configured resolution cap; the original is never served publicly.
23. The EXIF capture date and GPS reach the Submission form only as prefilled suggestions, and no Location is stored from them unless the Submitter places it.
24. A PDF upload produces a first-page preview.
25. Draft and pending media are served only to their Submitter and to Moderators; a never-edited draft is discarded after 24 hours, and an abandoned draft's media are deleted after `draft_expiry_days`.

**i18n shell**
26. `/` redirects by cookie, then `Accept-Language`, then the Instance default; every other page is under a UI-language prefix.
27. A disabled UI language prefix answers 404; the switcher lists only enabled UI languages and keeps the current page.
28. Every page carries `hreflang` alternates for the enabled UI languages and an `x-default`.
29. No user-facing string is hardcoded: navigation, buttons, labels, validation messages, statuses, errors, `aria-label`s, and empty states come from the message catalogue, and a missing key fails the build.
30. Content in the Content language is marked with its `lang` (and `dir`) when the UI language differs; Operator texts on About pages likewise.
31. Dates and numbers use `Intl` with the UI language and the Instance time zone.
32. The header shows the Instance logo (with its alt text) and archive name; the footer shows "Powered by TART" linking to the About TART page, the Data licence, contacts, and legal links; the browser title reads `<Page> — <Archive name>`.
33. On narrow screens the navigation opens from a labelled "Menu" button; no shell function depends on hover.
34. Shell pages pass axe with no WCAG 2.2 AA violations, in every enabled UI language, in light and dark themes, at desktop and mobile widths; every control is keyboard-operable with a visible focus indicator; no state is conveyed by colour alone.
35. Emails are rendered in the recipient's preferred UI language from the backend catalogue.

**CI**
36. CI fails on a missing message key, on drift between the OpenAPI schema and the generated client, on a dependency outside the licence tiers of [ADR 0011](../adr/0011-provisional-software-license.md), and on a third-party asset without a manifest entry ([ADR 0016](../adr/0016-licence-policy-for-map-assets-and-data.md)).

## Instance configuration

Keys named in the decisions are given as keys; for the other settings the decisions fix the content but not the key name, so the exact names are set by the configuration models and their exported JSON Schema (see Open items). "Not decided" means the decisions give no value for Rome.

| Setting | Key | Where | Rome |
|---|---|---|---|
| Configuration shape version | `config_version` | `instance.toml` | `1` |
| Archive name (Content language) | — | `instance.toml` | Not decided (see Open items) |
| Short description (Content language) | — | `instance.toml` | Not decided |
| Logo, light and dark, with alt text | — | SVG files + `instance.toml` | Not decided |
| Favicon | — | file | Not decided |
| Accent colour | — | `instance.toml` | Not decided |
| General contact | — | `instance.toml` | Not decided |
| DSA contact (required) | — | `instance.toml` | Not decided |
| Country (ISO 3166-1) | — | `instance.toml` | `IT` |
| Place name (Content language) | — | `instance.toml` | Not decided |
| Boundary polygon | — | GeoJSON file | Not decided |
| Default map view | — | `instance.toml` | Not decided |
| Time zone | — | `instance.toml` | `Europe/Rome` |
| Content language | — | `instance.toml` | `it` |
| Enabled UI languages | — | `instance.toml` | `it`, `en` |
| Default UI language | — | `instance.toml` | `it` |
| Expression types | — | vocabulary file | The brief's §9 starting vocabulary; Rome's labels not decided |
| Surface types | — | vocabulary file | Not decided (the brief's §9 list covers Expression types only) |
| Decision message reasons | — | vocabulary file | Not decided |
| Registration mode | `registration` | `instance.toml` | `open` |
| Minimum age (self-declared) | `min_age` | `instance.toml` | `14` |
| Data licence (SPDX) | `data_license` | `instance.toml` | `CC-BY-SA-4.0` |
| Licences allowed for files, and default | `contribution_license` (shape open, see Open items) | `instance.toml` | `CC-BY-4.0`, `CC-BY-SA-4.0`, `CC0-1.0`; default `CC-BY-SA-4.0` |
| Public image rendition cap | — | `instance.toml` | Not decided |
| Draft expiry | `draft_expiry_days` | `instance.toml` | `90` (platform default) |
| Maximum upload size | `max_upload_mb` | `instance.toml` and Caddy's environment | `25` (platform default) |
| Map style | — | MapLibre style file | Discovery spec |
| Map attribution (`{text, url}` list, non-empty) | — | `instance.toml` | `© OpenStreetMap` → `https://www.openstreetmap.org/copyright` |
| About, editorial guidelines, contribution policy | — | Markdown files | Not written yet |
| Terms of use, privacy policy (required) | — | Markdown files | Not written yet (drafting is out of scope) |

Environment (names set by implementation and documented for Operators): database URL, public base URL, storage choice, S3 endpoint, bucket, and credentials (Rome: Hetzner Object Storage), SMTP settings, session key, PMTiles volume path, and the upload limit for Caddy.

**Platform constants, not configuration**: one-time code length (6) and lifetime (10 minutes), code attempt limits, rate limits, session lifetime, the closed vocabularies, the authentication method, and "Powered by TART".

## Out of Scope

- A configuration UI and creating an Instance through the interface (Journey F).
- Custom metadata fields on Archive records; only vocabularies are configurable.
- Passwords, social login, and external identity providers (the interface allows one later).
- In-app role management; roles are granted through the CLI.
- In-app notification centre; email content and triggers are in the Notifications spec.
- A translation platform or translator workflow; UI languages are added complete at platform level.
- Translation of archive content or Operator texts.
- Testing right-to-left UI languages.
- Video and audio uploads; image blurring tools.
- A self-hosted S3 server.
- UI design tokens and a full design system.
- Backups, upgrades, monitoring, and the public data dump (Operations and portability spec).
- Account deletion, Purge, and data exports beyond the CLI shell (Rights and legal actions spec).
- Drafting the terms of use, privacy policy, trademark policy, and CLA.

## Further Notes

Not normative.

### Open items

The decisions are silent on these. Each needs a decision (or an owning ticket) before the affected implementation ticket starts; none should be filled in by an implementer's guess.

**Rome values**
1. **Archive name.** [ADR 0009](../adr/0009-instance-configuration-as-validated-files.md) requires the archive name in the Content language (`it`), but the only name on record is the English "Rome Urban Art Archive" (brief §4, spec index). Rome's Italian archive name is not decided.
2. Rome's short description, place name, logo, favicon, accent colour, boundary polygon, default map view, general and DSA contacts, and public image rendition cap are not decided (the spec index lists most of them).
3. Rome's Surface type entries, Decision message reasons, and Italian and English labels for the starting Expression types are not decided.

**Configuration shape**
4. **Key names** for identity, geography, languages, contacts, the rendition cap, and the map are not fixed by any decision; neither is the layout of the vocabulary files.
5. **File licence keys.** [ADR 0009](../adr/0009-instance-configuration-as-validated-files.md) names a single `contribution_license` key, while [ADR 0012](../adr/0012-per-file-licence-with-rights-basis.md) requires an allowlist of file licences with a default. The key shape (for example, a list plus a default) is not decided.
6. **Privacy contact.** [ADR 0013](../adr/0013-hide-not-delete-for-legal-removals.md) sends account-level GDPR requests to "the Operator's privacy contact", but [ADR 0009](../adr/0009-instance-configuration-as-validated-files.md) lists only general and DSA contact points. Whether a separate privacy contact key exists is not decided.
7. **Notice reasons.** [ADR 0013](../adr/0013-hide-not-delete-for-legal-removals.md) makes them a configurable list with defaults, but [ADR 0009](../adr/0009-instance-configuration-as-validated-files.md) lists only three open vocabularies. Whether Notice reasons are a fourth open vocabulary (keys, labels per UI language, `retired`) is not decided; it is needed by the Rights and legal actions spec.
8. **Terms versioning.** Terms are accepted again "when they change" ([ADR 0012](../adr/0012-per-file-licence-with-rights-basis.md)), but terms are a Markdown file with no Revisions. How a new version is declared (an explicit version key, a content hash, a date) is not decided.
9. **The backgrounds the accent is checked against.** UI design tokens are out of scope, so the light and dark background colours used in the startup contrast check are not defined yet.
10. **`tart config check` and the database.** Startup fails when a vocabulary key in use is missing, which needs the database. Whether `tart config check` also connects to the database, or checks the files alone, is not decided.
11. **Map style ownership** (Instance theme vs style file) is open in [Map style ownership: Instance theme vs style file](https://github.com/spippoli/tart/issues/37); it decides what the map part of the configuration contains.

**Authentication and accounts**
12. **Invite mode**: who issues invites (Operator via CLI, Moderators in the UI) and how an invitation is redeemed are deferred to [Moderation roles and permissions](https://github.com/spippoli/tart/issues/43).
13. **Role revocation**: only `tart users grant moderator` is decided; there is no decided command to revoke a role ([#43](https://github.com/spippoli/tart/issues/43)).
14. **Platform constant values**: code attempt limit, rate-limit thresholds, and session lifetime (absolute and idle) are not decided.
15. **Registration data**: whether a display name is required at registration (and its default), whether display names must be unique, and the initial preferred UI language are not decided.
16. **Email change**: the Account page lists the email, but the change flow (for example, confirming the new address with a code) is not decided.
17. **Language of a sign-in email to an unregistered address**: a new person has no preferred UI language yet; presumably the UI language of the page they used, but this is not decided.

**Media**
18. **Accepted file types**: [ADR 0004](../adr/0004-mvp-tech-stack.md) names image processing, HEIC, and PDF; the research ([#10](https://github.com/spippoli/tart/issues/10)) listed JPEG, PNG, WebP, HEIC, AVIF, and PDF. The final list (AVIF in particular) is not decided. HEIC is also subject to legal review ([ADR 0011 §9](../adr/0011-provisional-software-license.md)); if ruled out, HEIC uploads are dropped.
19. **Renditions**: the number and sizes of WebP renditions (the research suggested 3–4) and the pixel limit for the decompression guard are not decided.
20. **Upload limit scope**: whether `max_upload_mb` applies per file or per request is not stated.
21. **Abandoned uploads**: when an upload not attached to any draft is cleaned up is not decided.
22. **Caching** of served media (headers, whether a CDN may cache public renditions) is not decided; [ADR 0004](../adr/0004-mvp-tech-stack.md) rules out direct bucket access.

**Shell**
23. **Theme selection**: whether the light/dark theme follows `prefers-color-scheme` only or also offers a toggle is not decided.
24. **Abuse protection**: rate limiting of Submissions and Notices and spam protection under `open` registration are still unticketed ("Performance and limits" on the map); they may add to this spec.

### Recommendations for implementers

- Accept only same-origin relative paths in `?next=`, so the sign-in return cannot be used as an open redirect.
- Per-container memory use is unmeasured and is an explicit risk to Rome's €20/month target ([ADR 0004](../adr/0004-mvp-tech-stack.md)); measure it on the first running build.
- SvelteKit 3.0 was released on 2026-10-01: pin versions and expect ecosystem documentation to lag.
- The CLI needs the configuration and the database, so shipping it in the `api` image (run with `docker compose exec` or `run`) is the natural choice; packaging is not decided.
