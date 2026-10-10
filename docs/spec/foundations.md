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
| [0008](../adr/0008-single-content-language-and-prefixed-ui-languages.md) | **Content language** vs **UI language**, prefixed routing, root redirect, message catalogues, formatting, `lang`/`dir`, the language of each email |
| [0009](../adr/0009-instance-configuration-as-validated-files.md) | The configuration directory, environment variables, validation, versioning, vocabularies, identity (accent with light and dark values), community and legal keys, operational keys, the two map style files and their validation, the role and Invitation CLI, `self_approval`, `tart tiles update` |
| [0010](../adr/0010-public-url-scheme.md) | Translated path segments are UI strings; 301 and 410 behaviour the shell must render |
| [0011](../adr/0011-provisional-software-license.md) | "Powered by TART" is shown by default and may be removed (§7); dependency licence tiers (§8) |
| [0012](../adr/0012-per-file-licence-with-rights-basis.md) | EXIF handling, private originals, public rendition cap, licence allowlist, `min_age` |
| [0013](../adr/0013-hide-not-delete-for-legal-removals.md) | Purge and data exports run from the Operator CLI; account deletion is self-service |
| [0016](../adr/0016-licence-policy-for-map-assets-and-data.md) | Map attribution as a non-empty `{text, url}` list; courtesy credits on the About TART page from the asset manifest |
| [0017](../adr/0017-map-cartography-style.md) | The Instance accent is also validated against the map fills; dark theme follows the UI theme |
| [0020](../adr/0020-backups-replay-erasures-and-forward-only-upgrades.md) | Migrations run only from `tart upgrade`; `api` and `worker` refuse a database revision that differs from the code |

**Glossary terms used**: **Instance**, **Operator**, **Instance configuration**, **Data licence**, **Licensor**, **UI language**, **Content language**, **User**, **Moderator**, **Submitter**, **Submission**, **Submission status**, **Documentation item**, **Creator credit**, **Rights basis**, **Invitation**, **Expression type**, **Surface type**, **Decision message**, **Area**, **Location**, **Withdrawal**, **Purge**, **Notice**.

**Resolution comments incorporated**: [Platform vs instance configuration boundary](https://github.com/spippoli/tart/issues/6), [Tech stack decision](https://github.com/spippoli/tart/issues/13), [i18n strategy: UI vs multilingual content](https://github.com/spippoli/tart/issues/16), [Information architecture and page inventory](https://github.com/spippoli/tart/issues/15) (shell, navigation, sign-in, account, About pages), [Submission and moderation lifecycle](https://github.com/spippoli/tart/issues/5) (draft expiry), [Research: media pipeline and storage within budget](https://github.com/spippoli/tart/issues/10) (pipeline outline), [Content rights and GDPR product rules](https://github.com/spippoli/tart/issues/14) (EXIF, minimum age, account), [Submission form flow](https://github.com/spippoli/tart/issues/27) (per-file upload fields, server-side drafts), [Map style ownership: Instance theme vs style file](https://github.com/spippoli/tart/issues/37) (map style files, dual accent), [Basemap tile pipeline per Instance](https://github.com/spippoli/tart/issues/38) (`tart tiles update`), [Moderation roles and permissions](https://github.com/spippoli/tart/issues/43) (role CLI, `self_approval`, Invitations), [Notifications](https://github.com/spippoli/tart/issues/44) (email language), [Media types, renditions and caching](https://github.com/spippoli/tart/issues/88) (file types, renditions, abandoned uploads, caching), [Instance configuration keys and contacts](https://github.com/spippoli/tart/issues/85) (key names, file layout, licences, contacts, Notice reasons, terms version, `tart config check --database`), [Operator as decider and Moderator self-review](https://github.com/spippoli/tart/issues/93) (role-count warnings), [Redaction, current-value removal and Purge](https://github.com/spippoli/tart/issues/95) (Purge and credit anonymisation command names).

## Problem Statement

TART must run as many independent local archives, each with its own name, territory, languages, policies, and licences, without any of that being hardcoded for Rome. An **Operator** needs a way to describe their archive, start it on a small server (Rome: at most €20/month excluding VAT and off-site backups), and know before going live that the description is complete and valid. Visitors need a coherent, accessible interface in their own UI language even though the archive's content is written in one Content language. Contributors need to sign in without yet another password and to upload photos and PDFs from a phone in the street without leaking where they stood when they took the picture. Every later feature (records, map, Submissions, legal actions, notifications) needs the same configuration, identity, storage, and translation services underneath it.

## Solution

A single platform build, configured per Instance from a secret-free directory of files plus environment variables, validated in full at startup. Users sign in with a one-time code sent by email and may add passkeys; FastAPI owns an opaque, revocable session. Uploaded files go through a quarantine and a background worker that validates them, strips identifying metadata, and produces public renditions, while every object stays private and is served through the app. The SvelteKit shell renders every page under a UI-language prefix, with the Instance's identity in the header, "Powered by TART" in the footer, and the Operator's own texts on About pages in the Content language. A `tart` command-line tool gives the Operator the actions that have no UI in the MVP: checking configuration, managing the Moderator role and Invitations, and refreshing basemap tiles, with Purge, data exports, backups, upgrades, and the Data dump added by later specs.

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
12. As an Operator, I want to set my archive's name, short description, logo (light and dark), favicon, and accent colour (a light and a dark value), so that the archive has its own identity.
13. As an Operator, I want to be told at startup if either accent value fails WCAG AA contrast against its theme, so that I can't ship an inaccessible theme.
14. As an Operator, I want to declare my country, place name, time zone, boundary polygon, and default map view, so that the archive is about my territory.
15. As an Operator, I want to choose the Content language, the enabled UI languages, and the default UI language, so that the archive speaks to my community.
16. As an Operator, I want to set the registration mode (`open`, `invite`, or `closed`) and the minimum age, so that registration matches my community's policy and local law.
17. As an Operator, I want to choose the Data licence and the licences allowed for uploaded files from a platform list, so that the archive stays reusable.
18. As an Operator, I want to write my About page, editorial guidelines, contribution policy, terms of use, and privacy policy as Markdown files, so that I can edit them like any document.
19. As an Operator, I want to set the draft expiry period and the maximum upload size, so that storage stays within my budget.
20. As an Operator, I want to choose local disk or an S3-compatible bucket for storage, so that I can start small and move to object storage later.
21. As an Operator, I want to configure SMTP, so that sign-in codes and notifications reach Users.
22. As an Operator, I want to ship my own light and dark map styles, and be told at startup if they break TART's rules, so that the map fits my city without hiding the archive's signs.
23. As an Operator, I want to decide whether a Moderator may approve their own Submissions (`self_approval`), so that a one-Moderator archive can start and a larger one can require a second reviewer.

**Operator: CLI**

24. As an Operator, I want to grant the Moderator role to an email address from the command line, creating the User if needed, so that I can bootstrap moderation without any special-cased account.
25. As an Operator, I want to revoke the Moderator role with immediate effect and list who holds it, so that I can react when a Moderator leaves or misbehaves.
26. As an Operator, I want to create an Invitation from the command line, so that I can invite people when no Moderator exists yet.
27. As an Operator, I want one command that extracts my territory's basemap tiles and swaps them in safely, so that the map works without a third-party tile service.
28. As an Operator, I want the CLI to share the platform's validation, so that `tart config check` gives the same answer as startup.

**Visitor: shell and languages**

29. As a visitor, I want `/` to send me to my language (from my earlier choice, then my browser, then the archive default), so that I land in a language I read.
30. As a visitor, I want every page to have a language prefix in its URL, so that I can share a link in a specific language.
31. As a visitor, I want a language switcher that keeps me on the same page, so that I don't lose my place.
32. As a visitor, I want only the languages the archive enables to be offered, so that I never reach a half-supported language.
33. As a visitor reading in English, I want Italian archive content marked with its language, so that my screen reader pronounces it correctly.
34. As a visitor, I want dates and numbers formatted for my UI language and the archive's time zone, so that they read naturally.
35. As a visitor, I want the archive's own name and logo in the header and "Powered by TART" in the footer, so that I know whose archive this is and what runs it.
36. As a visitor, I want About pages with the archive's guidelines, policies, contacts, and data licence, so that I can understand and trust the archive.
37. As a visitor, I want an About TART page in my UI language, so that I know what the platform is and who made its parts.
38. As a visitor on a phone, I want a "Menu" button rather than hover menus, so that I can navigate by touch and keyboard.
39. As a keyboard or screen-reader user, I want every shell control reachable and labelled, so that I can use the archive without a mouse.
40. As a visitor, I want clear error pages (403, 404, 410) in my UI language, so that I understand what happened.

**User: sign-in and account**

41. As a contributor, I want to sign in with a code sent to my email, so that I don't need another password.
42. As a contributor, I want to add a passkey, so that I can sign in faster on my own devices.
43. As a contributor who clicked "Contribute" while signed out, I want to come back to where I was after signing in, so that I don't lose my place.
44. As a new contributor, I want the sign-in page to tell me whether I can register on this archive, so that I know what to expect under `open`, `invite`, or `closed`.
45. As a new contributor, I want my sign-in code email in the language of the page I signed in from, so that I can read it before I have any preference.
46. As an invited person, I want to register with the ordinary email code at the invited address, so that accepting an Invitation needs no extra step.
47. As a new contributor, I want to declare that I meet the minimum age, so that I can register lawfully.
48. As a User, I want to set my display name, which may be a pseudonym, so that I choose how I'm credited publicly.
49. As a User, I want to set my preferred UI language, so that the interface and my emails use it.
50. As a User, I want to manage my passkeys and email address and delete my account from one Account page, so that I control my data.
51. As a User, I want signing out to end my session immediately, so that a shared device is safe.
52. As a User, I want no public profile, so that the archive never ranks or displays me.

**User: uploads**

53. As a contributor on a phone, I want to upload photos straight from the camera, including HEIC, so that I can document an Artwork on the spot.
54. As a contributor, I want the photo's capture date and position offered only as suggestions for the Observed date and the map pin, so that I stay in control of what is recorded.
55. As a contributor, I want the GPS and device identifiers removed from what the archive stores, so that my own position is never published.
56. As a contributor, I want an upload that is too large or not a supported file to fail with a clear message, so that I can fix it.
57. As a contributor, I want my draft's files to stay private until approval, so that nothing I upload is public by accident.

**Moderator**

58. As a Moderator, I want the Moderation entry in the user menu, so that I reach the queue quickly.
59. As a signed-in User without the role, I want an explanatory 403 on Moderation pages, so that I know why I can't see them.

**Platform maintainers**

60. As a maintainer, I want a missing message key to fail the build, so that no UI language ships incomplete.
61. As a maintainer, I want the API to return stable error codes with parameters, so that every error is translated by the frontend.
62. As a maintainer, I want the TypeScript API client generated from FastAPI's schema with a drift check in CI, so that frontend and backend never disagree silently.
63. As a maintainer, I want CI to reject dependencies outside the licence tiers, so that the software stays within PolyForm Noncommercial's terms.

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

**Configuration directory.** Read-only and secret-free ([ADR 0009](../adr/0009-instance-configuration-as-validated-files.md)). Every path is fixed by the platform, so no key names a file ([Instance configuration keys and contacts](https://github.com/spippoli/tart/issues/85)):

```
instance.toml
vocabularies/expression_types.toml
vocabularies/surface_types.toml
vocabularies/decision_reasons.toml
vocabularies/notice_reasons.toml
texts/about.md
texts/editorial_guidelines.md
texts/contribution_policy.md
texts/terms.md
texts/privacy.md
identity/logo.light.svg
identity/logo.dark.svg
identity/favicon.svg
geography/boundary.geojson
map/style.light.json
map/style.dark.json
map/…                      fonts, glyphs, sprites, overlay GeoJSON
```

The two map style files and their assets follow [Map style ownership: Instance theme vs style file](https://github.com/spippoli/tart/issues/37). The PMTiles extract is not in the directory: `tart tiles update` writes it to a data volume.

**`instance.toml`** groups its keys in tables, so validation errors name a dotted path (`identity.accent.dark`). Values below are illustrative; Rome's are in [Instance configuration](#instance-configuration).

```toml
config_version = 1

[identity]
name = "…"                   # Content language
description = "…"            # Content language
logo = { light = "identity/logo.light.svg", dark = "identity/logo.dark.svg", alt = "…" }
favicon = "identity/favicon.svg"
accent = { light = "#…", dark = "#…" }

[operator]
name = "…"                   # legal name, not translated

[contacts]
general = "…"                # optional
dsa = "…"                    # DSA Art. 11–12; also Reply-To of legal emails
dsa_languages = ["it", "en"] # ISO 639-1; not tied to the UI languages
privacy = "…"                # GDPR requests

[languages]
content = "it"
ui = ["it", "en"]            # the first one is the default UI language

[geography]
country = "IT"
place_name = "…"             # Content language
time_zone = "Europe/Rome"
boundary = "geography/boundary.geojson"
default_view = { center = [12.4964, 41.9028], zoom = 12 }   # [lon, lat]

[map]
attribution = [{ text = "© OpenStreetMap", url = "https://www.openstreetmap.org/copyright" }]

[community]
registration = "open"
min_age = 14
self_approval = true
draft_expiry_days = 90

[media]
max_upload_mb = 25
public_rendition_max_px = 2048   # long edge

[licenses]
data = "CC-BY-SA-4.0"
files = ["CC-BY-SA-4.0", "CC-BY-4.0", "CC0-1.0"]   # the first one is the default
data_attribution = "…"       # optional, Content language (Operations and portability)

[terms]
version = 1
```

- `identity.logo` and `identity.favicon` hold the fixed paths and are validated against them; only the alt text varies.
- Contacts are email addresses; the same address may appear under several keys. There is no separate legal contact: legal emails set `Reply-To` to `contacts.dsa`, because statements of reasons, Notice decisions, and contesting are DSA duties.
- `licenses.data` and every entry of `licenses.files` come from the platform's list of SPDX identifiers; `files` is non-empty and has no duplicates, and its order is the order of the licence choice in the upload form.
- `terms.version` is an integer the Operator bumps only for a change that needs new acceptance; wording fixes keep the version, and their history is the configuration repository's history. Acceptance is specified by the Contribution and moderation spec.

**Environment variables.** Every secret and all infrastructure wiring: database URL, public base URL, storage choice and S3 credentials, SMTP settings, session key, PMTiles volume path. Caddy receives `max_upload_mb` through the environment as well.

**Loading and validation.**
- Only FastAPI's image (`api` and `worker`) reads the directory, with `tomllib`, into Pydantic models at startup.
- Invalid configuration stops the service and reports **every** error, not only the first. Unknown keys are errors.
- `tart config check` runs the same validation on the files alone, so it runs in the configuration repository's CI without a database. `tart config check --database` adds the checks that need the database (a vocabulary key in use but absent from the files, and a `terms.version` lower than the highest version already accepted), reading the database URL from the environment; the deploy procedure uses it. Startup always runs both. The database checks also print two **warnings**, which never fail: no User holds the Moderator role, or `self_approval = false` and fewer than two Users hold it ([#93](https://github.com/spippoli/tart/issues/93)). A JSON Schema exported from the models supports editors.
- No hot reload: a change needs a restart.
- The map style rules are checked in Python; full MapLibre style-spec conformance is left to `gl-style-validate` in CI, so the `api` image carries no Node. The style itself, its endpoint, and the archive layers are specified by the Discovery spec.
- `config_version` starts at 1 and is bumped by any platform release that changes the configuration's shape. A mismatch stops the service and points to the release notes. There is no automatic migration.
- Checks that go beyond the shape: an accent value (light or dark) that fails WCAG AA contrast against its own theme's backgrounds ([ADR 0009](../adr/0009-instance-configuration-as-validated-files.md)) and map fills ([ADR 0017](../adr/0017-map-cartography-style.md)); a map style that breaks the rules listed in [ADR 0009](../adr/0009-instance-configuration-as-validated-files.md) (both files present with the same sources and layer ids, the `metadata.tart:*` keys and insertion layer, no dash or pattern properties, root-relative asset paths to existing files, overlays at most 1 MB, fill and text contrast); a missing vocabulary label for any enabled UI language ([ADR 0008](../adr/0008-single-content-language-and-prefixed-ui-languages.md)); an enabled UI language the platform image doesn't contain; an empty map attribution list ([ADR 0016](../adr/0016-licence-policy-for-map-assets-and-data.md)); a missing terms of use, privacy policy, DSA contact, DSA contact language, privacy contact, or Operator name; an empty or duplicated file licence list, or a licence outside the platform's list; a vocabulary with no entry that is not retired; a vocabulary file using the reserved key `duplicate`; a vocabulary key used in the database but absent from the files; a `terms.version` lower than the highest version already accepted.

**Open vocabularies** (Expression type, Surface type, Decision message reasons, Notice reasons): each entry has an immutable `key` (what the database stores), one label per enabled UI language, an optional description, and a `retired` flag. Entries are never deleted; a retired entry stays displayed and filterable on existing records but is not selectable in new Submissions. Each vocabulary keeps at least one entry that is not retired. The platform ships the brief's §9 list for Expression types and the [ADR 0013](../adr/0013-hide-not-delete-for-legal-removals.md) defaults for Notice reasons (`artwork_copyright`, `file_copyright`, `personal_data`, `illegal_content`, `other`) as starting vocabularies; code reasons over none of these keys ([Instance configuration keys and contacts](https://github.com/spippoli/tart/issues/85)).

Each vocabulary file is a list of entries; the list order is the display order, so there is no order field:

```toml
[[entries]]
key = "mural"
label = { it = "Murale", en = "Mural" }
description = { it = "…", en = "…" }   # optional
retired = false                        # optional, default false
```

**The "duplicate" Decision message reason** is a platform entry outside `decision_reasons.toml`, because code uses it in the pending-duplicates flow ([#42](https://github.com/spippoli/tart/issues/42)). Its key `duplicate` is reserved: the database stores it like any reason, its labels are platform UI messages, it cannot be retired, it is listed after the configured reasons, and a vocabulary file that uses the key fails validation.

**Closed vocabularies** stay in the platform because code reasons over them: Condition, History event types, Submission status, Attribution certainty, Uncertain date precision and qualifier. Their labels are platform UI messages.

**No custom fields.** Configurability stops at vocabularies; an Instance cannot add fields to the core model.

**Public subset.** The SvelteKit frontend never reads the directory. It gets the public subset of the configuration (identity, Operator name, contacts, languages, geography, map attribution, vocabularies with labels, registration mode, licences, terms version, Operator texts) from an API endpoint and caches it.

**Operator texts** are Markdown in the Content language. They are not moderated and have no Revisions; their history is the configuration repository's history.

### 2. Authentication and sessions

**Sign-in** ([ADR 0005](../adr/0005-passwordless-in-app-auth.md)):
- The User enters an email and receives a one-time code: 6 digits, valid 10 minutes, with attempt limits and rate limits per email and per IP.
- Optional passkeys through `py_webauthn`, added and removed on the Account page.
- No passwords and no social login in the MVP.
- The page is `/<ui-language>/accedi` (`/en/sign-in`) and offers email code and passkey. Its registration text depends on the `registration` mode.

**Registration.**
- `open`: anyone who meets the minimum age may register.
- `invite`: only invited people may register. Moderators issue **Invitations** in the Moderation area and the Operator with `tart invites create <email>`. An Invitation is bound to one email address, single-use, and expires after 14 days (platform constant); it is redeemed by registering with the ordinary email code at that address, and creates a User without any role ([Moderation roles and permissions](https://github.com/spippoli/tart/issues/43)). The Invitations list and email are specified by the Contribution and moderation and Notifications specs.
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

**Roles.** Roles live in TART's database whatever the authentication method. In the MVP the only role is Moderator; the Operator is not a User role. The Operator grants, revokes, and lists it through the CLI. Roles are checked on every request, so a revocation takes effect on the next request, open sessions included; past decisions, Moderation notes, and issued Invitations stay attributed to the former Moderator. No role is special-cased in code for bootstrapping. The `self_approval` key (default `false`) decides whether a Moderator may decide on their own Submission; what the role may do, and the self-review rules, are specified by the Contribution and moderation spec ([Moderation roles and permissions](https://github.com/spippoli/tart/issues/43)).

**Access rules owned by the shell** ([#15](https://github.com/spippoli/tart/issues/15)):
- An anonymous user who triggers a contribution action goes to sign-in with `?next=` and returns there afterwards.
- On `/<ui-language>/moderazione`, an anonymous user is sent to sign-in; a signed-in User without the Moderator role gets an explanatory 403.
- There are no public User profiles.

**Account** (`/it/account`, `/en/account`): display name (may be a pseudonym; it is what public Revisions pages show, [#14](https://github.com/spippoli/tart/issues/14)), preferred UI language (initially the UI language of the page the User registered from; also used for the User's emails, [ADR 0008](../adr/0008-single-content-language-and-prefixed-ui-languages.md)), passkeys, email, and account deletion. The deletion flow (erasing email and credentials, a stable pseudonym, deleting drafts, retracting open Submissions) is specified by the Rights and legal actions spec ([ADR 0013](../adr/0013-hide-not-delete-for-legal-removals.md)). My contributions (`/it/account/contributi`) belongs to the Contribution and moderation spec.

**Email.** A generic SMTP adapter configured through the environment, with Mailpit in development (Compose profile). Emails are rendered by the `worker` from the backend message catalogue in the recipient's preferred UI language, or the Instance's default UI language if that language has been disabled. A sign-in code to an address with no User yet uses the UI language of the sign-in page. The language of every other email is specified by the Notifications spec ([ADR 0008](../adr/0008-single-content-language-and-prefixed-ui-languages.md), [Notifications](https://github.com/spippoli/tart/issues/44)). Reliable delivery is critical: if email is down, nobody without a passkey can sign in ([ADR 0005](../adr/0005-passwordless-in-app-auth.md)).

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
1. Detect the file type from its content (magic bytes), not from its name or declared type. Accepted types are a platform constant: JPEG, PNG, WebP, AVIF, HEIC, and PDF ([#88](https://github.com/spippoli/tart/issues/88)). GIF and TIFF are refused. Animated WebP or AVIF is accepted, and only its first frame is kept.
2. Enforce size and pixel limits, fully decode the file, and reject it if decoding fails. The pixel limit is a platform constant of 100 megapixels, enforced as an error (Pillow's decompression-bomb guard, tightened); a larger image is refused with a translatable error code asking for a smaller image ([#88](https://github.com/spippoli/tart/issues/88)).
3. Read the EXIF capture date and GPS **as suggestions only**, returned to the Submission form to prefill the Observed date and a map pin ([ADR 0012](../adr/0012-per-file-licence-with-rights-basis.md)). They are never stored as a Location: the artwork location is not the submitter's location.
4. Strip GPS and device identifiers from the stored original. The original stays private.
5. Images: apply EXIF orientation and produce WebP renditions with Pillow, with no EXIF, XMP, or IPTC metadata. HEIC is decoded with `pi-heif` (decode-only); AVIF is decoded by Pillow itself. There are three renditions, sized by their long edge ([#88](https://github.com/spippoli/tart/issues/88)):
   - **thumbnail**, 480 px (lists and the panel);
   - **view**, 1280 px (record pages);
   - **large**, the public rendition cap set in the Instance configuration ([ADR 0012](../adr/0012-per-file-licence-with-rights-basis.md)).

   480 and 1280 are platform constants. A rendition is never upscaled: when the original, or the cap, is smaller than a size, that rendition takes the smaller value.
6. PDFs: render a first-page preview with `pypdfium2`, under the same pixel limit, and derive the same three renditions from it.
7. PyMuPDF (AGPL) and libvips are excluded ([ADR 0004](../adr/0004-mvp-tech-stack.md), [ADR 0011](../adr/0011-provisional-software-license.md)).

The per-file fields a Submitter fills in (Observed date, **Rights basis**, **Creator credit**, licence from the allowlist) are specified by the Contribution and moderation spec ([#27](https://github.com/spippoli/tart/issues/27)); a link is linked, never uploaded.

**Lifecycle of uploaded files.**
- Draft media are server-side and private, and never public ([#5](https://github.com/spippoli/tart/issues/5)).
- A draft never edited is discarded after 24 hours ([#15](https://github.com/spippoli/tart/issues/15)).
- An abandoned draft expires after `draft_expiry_days`, and its media are deleted ([#5](https://github.com/spippoli/tart/issues/5)).
- The worker also cleans up abandoned uploads ([ADR 0004](../adr/0004-mvp-tech-stack.md)): an upload never attached to a draft is deleted 24 hours after it was uploaded, by a sweep that runs hourly. A file rejected during processing is deleted at once; only its error code reaches the form ([#88](https://github.com/spippoli/tart/issues/88)).
- Media of approved Documentation items are never deleted except by a Purge ([ADR 0013](../adr/0013-hide-not-delete-for-legal-removals.md)).

**Serving.** Files are streamed by the app with an authorisation check: an approved, non-withdrawn Documentation item's renditions are public; pending media are visible only to their Submitter and to Moderators; originals are never public. PMTiles are served by Caddy from the data volume (Discovery spec).

**Caching** ([#88](https://github.com/spippoli/tart/issues/88)). Files are immutable but their visibility is not: a Withdrawal or a legal action must take a public image down. So caching stays short:
- Public renditions and previews: `Cache-Control: public, max-age=3600` with an ETag, so a takedown reaches intermediate caches within an hour.
- Draft, pending, and other non-public media: `Cache-Control: private, no-store`.
- The reference stack has no CDN. An Operator may put one in front only if it honours these headers and never extends their lifetime; the Operator documentation says so.

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
- **Theme**: light and dark logo variants, and an accent with a light and a dark value, each checked against its own theme. The map follows the UI theme ([ADR 0017](../adr/0017-map-cartography-style.md)).

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
| `tart config check [--database]` | Runs the startup validation of the files and reports every error; `--database` adds the checks that need the database | This spec |
| `tart users grant moderator <email>` | Grants the Moderator role, creating the User if needed | This spec |
| `tart users revoke moderator <email>` | Removes the Moderator role, effective on the next request | This spec |
| `tart users list --role moderator` | Lists the Users holding the role | This spec |
| `tart invites create <email>` | Creates an Invitation; the email uses the Instance's default UI language | This spec; Contribution and moderation |
| `tart tiles update` | Extracts the boundary plus 2 km into a versioned PMTiles file and swaps it in | Discovery |
| `tart upgrade`, `tart config migrate`, `tart backup run\|verify\|restore`, `tart jobs failed\|retry`, `tart dump` | Upgrades with forward-only migrations, configuration migration, backups, failed worker jobs, and the public Data dump | Operations and portability |
| `tart purge <legal-action-id> --ground … --reference …` | Permanently erases what a Withdrawal or Redaction hides, only when the law requires it | Rights and legal actions |
| `tart users anonymise-credits <user>`, `tart documentation anonymise-credit <id>` | Anonymises Creator credits on request | Rights and legal actions |
| User data export | Produces the Art. 15 and Art. 20 exports on request | Rights and legal actions |

The export command name is left to the Rights and legal actions spec. `tart tiles update` runs the go-pmtiles binary bundled in the `api` image ([Basemap tile pipeline per Instance](https://github.com/spippoli/tart/issues/38)).

### Topology and stack

As in [ADR 0004](../adr/0004-mvp-tech-stack.md): a monorepo (`backend/`, `frontend/`, `deploy/`); services `caddy`, `frontend`, `api`, `worker`, `db` (PostgreSQL + PostGIS from the upstream image, unmodified), and `mailpit` in development only. Alembic migrations run only from `tart upgrade`, in a one-shot container; `api` and `worker` refuse to start when the database revision differs from the code's head ([ADR 0020](../adr/0020-backups-replay-erasures-and-forward-only-upgrades.md), [#45](https://github.com/spippoli/tart/issues/45)). Reference sizing is 4 GB RAM minimum, 8 GB recommended. Backups, upgrades, and monitoring belong to the Operations and portability spec.

## Testing Decisions

A good test exercises a module through its external interface and asserts observable behaviour (an HTTP response, a stored object, a rendered page, an error list), never internal calls. The repository has no code yet, so there is no prior art; these seams are the first.

- **Configuration loader**: a directory and an environment in, a validated configuration or a complete error list out (pytest). Fixtures: Rome's configuration as a valid case; one directory per failure (unknown key, wrong `config_version`, missing label, low-contrast accent, empty attribution, missing legal text, missing contact, reserved key `duplicate`, a vocabulary with every entry retired, empty licence list). The same fixtures run through `tart config check`; the database checks run through `tart config check --database` against a test database.
- **Authentication and sessions**: through the HTTP API with FastAPI's test client and an email adapter that captures messages. Covers code expiry and attempt limits, registration under each `registration` mode, session revocation on sign-out, and the CSRF rules (missing custom header, foreign `Origin`).
- **Storage**: one contract test suite run against both adapters (put, streamed get with byte ranges, delete, quarantine vs permanent). How the S3 adapter is exercised in CI is left to implementation.
- **Media pipeline**: worker jobs fed fixture files (JPEG with GPS EXIF, rotated JPEG, HEIC, AVIF, animated WebP, PNG, GIF, PDF, an image over 100 megapixels, a truncated file, a decompression bomb, a file whose extension lies). Asserts on the stored outputs: no GPS or device identifiers in the original, no metadata in renditions, orientation applied, the rendition cap respected, rejections with error codes.
- **Shell**: Playwright with axe over the shell pages in every enabled UI language, at desktop and mobile widths: root redirect order, switcher, disabled-language 404, `lang` on content, keyboard-only navigation of the Menu button and user menu.
- **CI checks** ([ADR 0004](../adr/0004-mvp-tech-stack.md), [ADR 0011](../adr/0011-provisional-software-license.md), [ADR 0016](../adr/0016-licence-policy-for-map-assets-and-data.md)): missing message keys (frontend and backend), OpenAPI client drift, the dependency licence allow-list, and the third-party asset manifest.

## Acceptance criteria

**Instance configuration**
1. With Rome's configuration directory and a complete environment, `api` and `worker` start; `tart config check` exits successfully.
2. A configuration with several errors stops startup and lists all of them; `tart config check` prints the same list and exits with a failure status.
3. An unknown key, a `config_version` different from the platform's, a missing vocabulary label for an enabled UI language, an enabled UI language missing from the image, an empty map attribution list, or a missing terms of use, privacy policy, or DSA contact each fail validation.
4. An accent value below WCAG AA contrast against its own theme's background, or against that theme's map fills ([ADR 0017](../adr/0017-map-cartography-style.md)), fails validation.
5. A missing `map/style.dark.json`, a style whose sources or layer ids differ between light and dark, a missing `metadata.tart:insert-archive-below` layer, a `line-dasharray`, or an asset path that does not exist each fail validation.
6. Removing a vocabulary key that the database uses fails startup; marking it `retired` succeeds, and the value still displays on existing records.
7. The configuration directory contains no secret; every secret and connection setting is read from the environment.
8. The frontend reads configuration only through the public API endpoint, and that endpoint exposes no environment value.
9. Changing a configuration file has no effect until a restart.

**Authentication and sessions**
10. Requesting a code sends a 6-digit code by email; it is rejected after 10 minutes and after the attempt limit; repeated requests are rate-limited per email and per IP.
11. Under `open`, a new email can register after a self-declared minimum-age confirmation; under `closed`, it cannot; under any mode, no manual approval step exists.
12. A User can add a passkey on the Account page and then sign in with it.
13. The session cookie is `HttpOnly`, `Secure`, and `SameSite=Lax`; after sign-out, the same session ID is rejected on the next request.
14. A state-changing API request without the required custom header, or with a foreign `Origin`, is refused.
15. Server-rendered pages show the signed-in state, because SvelteKit forwards the cookie to FastAPI.
16. An anonymous contribution action leads to sign-in with `?next=` and returns to the original page afterwards.
17. `/it/moderazione` sends an anonymous user to sign-in and answers a signed-in non-Moderator with a translated, explanatory 403; the Moderation menu entry appears only for Moderators.
18. `tart users grant moderator <email>` gives the role to an existing User, or creates the User with the role; after `tart users revoke moderator <email>`, that User's next request in an open session is refused on Moderation pages; `tart users list --role moderator` lists exactly the holders.
19. Under `invite`, an address with a pending, unexpired Invitation can register with the email code and gets no role; an address without one, or with an expired or used Invitation, cannot.
20. A sign-in code to an address with no User is written in the sign-in page's UI language; a new User's preferred UI language is the language of the page they registered from.

**Storage and media**
21. With either storage adapter, an uploaded file is stored privately and can be fetched only through the app.
22. An upload above `max_upload_mb` is refused by Caddy and by the app with a translatable error code.
23. A file whose content is not a supported type, or that fails to decode, is rejected regardless of its extension.
24. After processing, the stored original has no GPS or device identifiers, renditions carry no EXIF, XMP, or IPTC metadata, and EXIF orientation is applied.
25. No public rendition exceeds the configured resolution cap; the original is never served publicly.
26. The EXIF capture date and GPS reach the Submission form only as prefilled suggestions, and no Location is stored from them unless the Submitter places it.
27. A PDF upload produces a first-page preview. Images and previews get thumbnail (480 px), view (1280 px), and large (cap) renditions by long edge, none upscaled; an image above 100 megapixels, a GIF, or a TIFF is refused with a translatable error code.
28. Draft and pending media are served only to their Submitter and to Moderators; a never-edited draft is discarded after 24 hours, and an abandoned draft's media are deleted after `draft_expiry_days`; an upload never attached to a draft is deleted within 25 hours, and a rejected file at once. Public renditions are served with `public, max-age=3600`, everything else with `private, no-store`.

**i18n shell**
29. `/` redirects by cookie, then `Accept-Language`, then the Instance default; every other page is under a UI-language prefix.
30. A disabled UI language prefix answers 404; the switcher lists only enabled UI languages and keeps the current page.
31. Every page carries `hreflang` alternates for the enabled UI languages and an `x-default`.
32. No user-facing string is hardcoded: navigation, buttons, labels, validation messages, statuses, errors, `aria-label`s, and empty states come from the message catalogue, and a missing key fails the build.
33. Content in the Content language is marked with its `lang` (and `dir`) when the UI language differs; Operator texts on About pages likewise.
34. Dates and numbers use `Intl` with the UI language and the Instance time zone.
35. The header shows the Instance logo (with its alt text) and archive name; the footer shows "Powered by TART" linking to the About TART page, the Data licence, contacts, and legal links; the browser title reads `<Page> — <Archive name>`.
36. On narrow screens the navigation opens from a labelled "Menu" button; no shell function depends on hover.
37. Shell pages pass axe with no WCAG 2.2 AA violations, in every enabled UI language, in light and dark themes, at desktop and mobile widths; every control is keyboard-operable with a visible focus indicator; no state is conveyed by colour alone.
38. Emails are rendered in the recipient's preferred UI language from the backend catalogue.

**CI**
39. CI fails on a missing message key, on drift between the OpenAPI schema and the generated client, on a dependency outside the licence tiers of [ADR 0011](../adr/0011-provisional-software-license.md), and on a third-party asset without a manifest entry ([ADR 0016](../adr/0016-licence-policy-for-map-assets-and-data.md)).

**Configuration keys and contacts** ([Instance configuration keys and contacts](https://github.com/spippoli/tart/issues/85))
40. `instance.toml` with the tables and keys of [Instance configuration](#1-instance-configuration) loads; a file moved away from its fixed path fails validation.
41. The default UI language is the first entry of `languages.ui`; the default file licence is the first entry of `licenses.files`, and the upload form lists the licences in that order.
42. A vocabulary whose every entry is retired, or a vocabulary file containing the key `duplicate`, fails validation; the decision form lists the configured reasons in file order followed by the platform's "duplicate" reason in the UI language.
43. `tart config check` without `--database` succeeds with no database reachable; with `--database`, it also fails on a vocabulary key in use but absent from the files and on a `terms.version` lower than the highest version already accepted, and startup fails on the same.
44. A missing `operator.name`, `contacts.dsa`, `contacts.dsa_languages`, or `contacts.privacy` fails validation; `contacts.general` may be absent.
45. With no User holding the Moderator role, or with `self_approval = false` and one Moderator, startup and `tart config check --database` print a warning and still succeed ([Operator as decider and Moderator self-review](https://github.com/spippoli/tart/issues/93)).

## Instance configuration

Keys and paths are fixed by [ADR 0009](../adr/0009-instance-configuration-as-validated-files.md) and [Instance configuration keys and contacts](https://github.com/spippoli/tart/issues/85); dotted keys are in `instance.toml`. "Not decided" means the decisions give no value for Rome.

| Setting | Key or path | Rome |
|---|---|---|
| Configuration shape version | `config_version` | `1` |
| Archive name (Content language) | `identity.name` | Not decided (see Open items) |
| Short description (Content language) | `identity.description` | Not decided |
| Logo, light and dark, with alt text | `identity/logo.light.svg`, `identity/logo.dark.svg`, `identity.logo.alt` | Not decided |
| Favicon | `identity/favicon.svg` | Not decided |
| Accent colour, light and dark values | `identity.accent.light`, `identity.accent.dark` | Not decided |
| Operator name (required) | `operator.name` | Not decided |
| General contact (optional) | `contacts.general` | Not decided |
| DSA contact and its languages (required); `Reply-To` of legal emails | `contacts.dsa`, `contacts.dsa_languages` | Not decided |
| Privacy contact (required) | `contacts.privacy` | Not decided |
| Content language | `languages.content` | `it` |
| Enabled UI languages, default first | `languages.ui` | `["it", "en"]` |
| Country (ISO 3166-1) | `geography.country` | `IT` |
| Place name (Content language) | `geography.place_name` | Not decided |
| Boundary polygon | `geography/boundary.geojson` | Not decided |
| Default map view | `geography.default_view` (`center` as `[lon, lat]`, `zoom`) | Not decided |
| Time zone | `geography.time_zone` | `Europe/Rome` |
| Map styles and assets | `map/style.light.json`, `map/style.dark.json`, `map/` | The [ADR 0017](../adr/0017-map-cartography-style.md) reference style (Discovery spec) |
| Map attribution (`{text, url}` list, non-empty) | `map.attribution` | `© OpenStreetMap` → `https://www.openstreetmap.org/copyright` |
| Registration mode | `community.registration` | `open` |
| Minimum age (self-declared) | `community.min_age` | `14` |
| Self-review | `community.self_approval` | `true` at launch; `false` once at least two Moderators are active (Operator checklist) |
| Draft expiry | `community.draft_expiry_days` | `90` (platform default) |
| Maximum upload size | `media.max_upload_mb`, and Caddy's environment | `25` (platform default) |
| Public image rendition cap (long edge, px) | `media.public_rendition_max_px` | Not decided |
| Data licence (SPDX) | `licenses.data` | `CC-BY-SA-4.0` |
| Licences allowed for files, default first | `licenses.files` | `["CC-BY-SA-4.0", "CC-BY-4.0", "CC0-1.0"]` |
| Data dump attribution (optional) | `licenses.data_attribution` | Operations and portability spec |
| Terms version | `terms.version` | `1` at launch |
| Expression types | `vocabularies/expression_types.toml` | The brief's §9 starting vocabulary; Rome's labels not decided |
| Surface types | `vocabularies/surface_types.toml` | Not decided (the brief's §9 list covers Expression types only) |
| Decision message reasons | `vocabularies/decision_reasons.toml`, plus the platform's `duplicate` | Not decided |
| Notice reasons | `vocabularies/notice_reasons.toml` | The [ADR 0013](../adr/0013-hide-not-delete-for-legal-removals.md) defaults; Rome's labels not decided |
| About, editorial guidelines, contribution policy | `texts/about.md`, `texts/editorial_guidelines.md`, `texts/contribution_policy.md` | Not written yet |
| Terms of use, privacy policy (required) | `texts/terms.md`, `texts/privacy.md` | Not written yet (drafting is out of scope) |

Environment (names set by implementation and documented for Operators): database URL, public base URL, storage choice, S3 endpoint, bucket, and credentials (Rome: Hetzner Object Storage), SMTP settings, session key, PMTiles volume path, and the upload limit for Caddy.

**Platform constants, not configuration**: one-time code length (6) and lifetime (10 minutes), code attempt limits, rate limits, session lifetime, Invitation expiry (14 days), the basemap extract buffer (2 km), the closed vocabularies, the authentication method, and "Powered by TART".

## Out of Scope

- A configuration UI and creating an Instance through the interface (Journey F).
- Custom metadata fields on Archive records; only vocabularies are configurable.
- Passwords, social login, and external identity providers (the interface allows one later).
- In-app role management; roles are granted, revoked, and listed through the CLI.
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
1. **Archive name.** [ADR 0009](../adr/0009-instance-configuration-as-validated-files.md) requires the archive name in the Content language (`it`), but the only name on record is the English "Rome Urban Art Archive" (brief §4, spec index). Rome's Italian archive name is not decided. Owner: [Rome Instance values](https://github.com/spippoli/tart/issues/86).
2. Rome's short description, place name, logo, favicon, accent colour, boundary polygon, default map view, Operator name, general, DSA, and privacy contacts with the DSA contact's languages, and public image rendition cap are not decided (the spec index lists most of them). Owner: [Rome Instance values](https://github.com/spippoli/tart/issues/86).
3. Rome's Surface type entries, Decision message reasons, and Italian and English labels for the starting Expression types and Notice reasons are not decided. Owner: [Rome Instance values](https://github.com/spippoli/tart/issues/86).

**Configuration shape**
4. **Key names.** Answered by [Instance configuration keys and contacts](https://github.com/spippoli/tart/issues/85): tables and keys in [Instance configuration](#1-instance-configuration), fixed file paths, vocabulary files as ordered lists of entries.
5. **File licence keys.** Answered by [Instance configuration keys and contacts](https://github.com/spippoli/tart/issues/85): `licenses.data` and `licenses.files`, whose first entry is the default; `contribution_license` is gone.
6. **Privacy contact.** Answered by [Instance configuration keys and contacts](https://github.com/spippoli/tart/issues/85): `contacts.privacy` is required; legal emails reply to `contacts.dsa`, which comes with `contacts.dsa_languages`.
7. **Notice reasons.** Answered by [Instance configuration keys and contacts](https://github.com/spippoli/tart/issues/85): a fourth open vocabulary, `vocabularies/notice_reasons.toml`, starting from the ADR 0013 defaults.
8. **Terms versioning.** Answered by [Instance configuration keys and contacts](https://github.com/spippoli/tart/issues/85): an integer `terms.version`, bumped by the Operator; it may not go below the highest version already accepted.
9. **The backgrounds the accent is checked against.** UI design tokens are out of scope, so the light and dark background colours used in the startup contrast check are not defined yet. Owner: [Map rendering details, style endpoint and theme](https://github.com/spippoli/tart/issues/98).
10. **`tart config check` and the database.** Answered by [Instance configuration keys and contacts](https://github.com/spippoli/tart/issues/85): the files alone by default; `--database` adds the database checks; startup runs both.
11. **Map style ownership.** Answered by [Map style ownership: Instance theme vs style file](https://github.com/spippoli/tart/issues/37): the Instance ships two finished style files; see [Instance configuration](#1-instance-configuration).

**Authentication and accounts**
12. **Invite mode.** Answered by [Moderation roles and permissions](https://github.com/spippoli/tart/issues/43): Moderators in the UI and the Operator with `tart invites create`; email-bound, single-use, 14 days; see Registration.
13. **Role revocation.** Answered by [Moderation roles and permissions](https://github.com/spippoli/tart/issues/43): `tart users revoke moderator <email>`, effective on the next request; see Roles.
14. **Platform constant values**: code attempt limit, rate-limit thresholds, and session lifetime (absolute and idle) are not decided. Owner: [Security constants and abuse protection](https://github.com/spippoli/tart/issues/84).
15. **Registration data**: whether a display name is required at registration (and its default) and whether display names must be unique are not decided. The initial preferred UI language is answered by [Notifications](https://github.com/spippoli/tart/issues/44): the language of the page the User registered from. Owner: [Accounts: registration, email change, deletion and export](https://github.com/spippoli/tart/issues/87).
16. **Email change**: the Account page lists the email, but the change flow (for example, confirming the new address with a code) is not decided. Owner: [Accounts: registration, email change, deletion and export](https://github.com/spippoli/tart/issues/87).
17. **Language of a sign-in email to an unregistered address.** Answered by [Notifications](https://github.com/spippoli/tart/issues/44): the sign-in page's UI language.

**Media**
18. **Accepted file types.** Answered by [Media types, renditions and caching](https://github.com/spippoli/tart/issues/88): JPEG, PNG, WebP, AVIF, HEIC, and PDF; no GIF or TIFF; first frame only of animated images. HEIC stays subject to legal review ([ADR 0011 §9](../adr/0011-provisional-software-license.md)); see [Storage and media pipeline](#3-storage-and-media-pipeline).
19. **Renditions.** Answered by [Media types, renditions and caching](https://github.com/spippoli/tart/issues/88): three WebP renditions by long edge (480 px, 1280 px, and the Instance cap), never upscaled; a 100-megapixel limit, enforced as an error; see [Storage and media pipeline](#3-storage-and-media-pipeline).
20. **Upload limit scope**: whether `max_upload_mb` applies per file or per request is not stated. Owner: [Security constants and abuse protection](https://github.com/spippoli/tart/issues/84).
21. **Abandoned uploads.** Answered by [Media types, renditions and caching](https://github.com/spippoli/tart/issues/88): deleted 24 hours after upload by an hourly sweep; rejected files at once.
22. **Caching.** Answered by [Media types, renditions and caching](https://github.com/spippoli/tart/issues/88): `public, max-age=3600` with an ETag for public renditions, `private, no-store` otherwise; no CDN in the reference stack, and an Operator's CDN must honour the headers.

**Shell**
23. **Theme selection**: whether the light/dark theme follows `prefers-color-scheme` only or also offers a toggle is not decided. Owner: [Map rendering details, style endpoint and theme](https://github.com/spippoli/tart/issues/98).
24. **Abuse protection**: rate limiting of Submissions and Notices and spam protection under `open` registration may add to this spec. Owner: [Security constants and abuse protection](https://github.com/spippoli/tart/issues/84).

### Recommendations for implementers

- Accept only same-origin relative paths in `?next=`, so the sign-in return cannot be used as an open redirect.
- Per-container memory use is unmeasured and is an explicit risk to Rome's €20/month target ([ADR 0004](../adr/0004-mvp-tech-stack.md)); measure it on the first running build.
- SvelteKit 3.0 was released on 2026-10-01: pin versions and expect ecosystem documentation to lag.
- The CLI needs the configuration and the database, so shipping it in the `api` image (run with `docker compose exec` or `run`) is the natural choice; packaging is not decided.
