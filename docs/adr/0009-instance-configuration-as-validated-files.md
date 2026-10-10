# Instance configuration as validated files; vocabularies, not schema

An Instance is configured from a read-only directory of files that describes what the archive *is*, while environment variables describe where and how it runs. The main file `instance.toml` sits alongside separate vocabulary files, the Operator's Markdown texts (About, editorial guidelines, contribution policy, terms of use, privacy policy), the logo, a map style, and a GeoJSON boundary. Environment variables hold every secret and all infrastructure wiring: database URL, public base URL, storage choice and S3 credentials, SMTP, session key, and the PMTiles volume path. The directory holds no secrets, so it is identical across staging and production and can be versioned in a public repository (e.g. `tart-rome-config`). Configurability stops at vocabularies: an Instance chooses its Expression types, Surface types, and Decision message reasons, but cannot add fields to the core model. We chose files because the MVP has no configuration UI (Journey F is out of scope), and we chose vocabularies over custom fields because only one Instance exists. Custom fields would ripple into search, filters, field-changeset moderation (ADR 0007), and schema changes on live data.

## Decisions

- **Format**: TOML, read with Python's standard `tomllib`. It has no implicit typing (YAML's `no` → `false`) and, unlike JSON, it allows comments.
- **Single reader**: only FastAPI (`api` and `worker`) reads the directory. It validates the files with Pydantic models at startup. The SvelteKit frontend gets the public subset from an API endpoint and caches it.
- **Fail fast**: invalid configuration stops the service and reports every error, not just the first. Unknown keys are errors. `tart config check` runs the same validation before a deploy, and a JSON Schema exported from the models gives editors autocompletion. There is no hot reload; a change needs a restart.
- **Versioning**: `config_version` (starting at 1) is bumped by any platform release that changes the configuration's shape. A mismatch stops the service and points to the release notes. There is no automatic migration.
- **Open vocabularies** (Expression type, Surface type, Decision message reasons): each entry has an immutable `key`, which is what the database stores, plus one label per enabled UI language (ADR 0008), an order, and an optional description. Entries are never deleted. They are marked `retired`, which keeps them displayed and filterable on existing records but not selectable in new Submissions. Startup fails if a key in use is missing. The platform ships the brief's §9 vocabulary as a starting point.
- **Closed vocabularies** stay in the platform because code reasons over them: Condition, History event types, Submission status, Attribution certainty, and Uncertain date precision and qualifier.
- **Geography**: country (ISO 3166-1), the place name in the Content language, a GeoJSON boundary polygon, the default map view, and the time zone. A new or changed Location geometry outside the boundary is rejected with an error code. The boundary also bounds the map.
- **Map**: a MapLibre style file in the directory that references tiles by URL, plus an attribution list of `{text, url}` entries that may not be empty (amended by ADR 0016). Only the map module reads the style (ADR 0004). The PMTiles file lives in a data volume, not in the directory.
- **Identity**: archive name and short description in the Content language; SVG logo with light and dark variants and alt text; favicon; one accent colour whose WCAG AA contrast against the light and dark backgrounds is checked at startup; general and DSA contact points. "Powered by TART" is rendered by the platform and is not a configuration key.
- **Community and legal**: `registration` is `open`, `invite`, or `closed` (no manual account approval). `data_license` and `contribution_license` come from a platform-defined list of SPDX identifiers. `min_age` sets the minimum age to register. Terms of use, privacy policy, and a DSA contact are required.
- **Operational settings**: only `draft_expiry_days` (default 90) and `max_upload_mb` (default 25; Caddy receives the same value through the environment). Security parameters (one-time code lifetime and attempts, rate limits, session lifetime) are platform constants that configuration cannot weaken.
- **Roles are data, not configuration**: the Operator assigns them with a CLI command (`tart users grant moderator <email>`, creating the User if needed). No role is special-cased in code for bootstrapping.
- **Not configurable in the MVP**: the authentication method (only the built-in one ships, ADR 0005) and external integrations (none).

## Considered Options

- **Everything in environment variables**: flat strings fit vocabularies with per-language labels, Markdown texts, and polygons poorly, and they mix secrets with publishable configuration.
- **YAML**: more familiar, but its implicit typing causes silent misconfiguration, and Python has no standard-library parser for it.
- **Configuration in the database, edited in an admin UI**: this is Journey F, which is out of scope. It would also require auditing changes to configuration.
- **Custom typed metadata fields** (text, number, enum, boolean on Artworks, stored as JSONB and edited as ordinary field changesets): the likely future direction, deferred until a second Instance needs it.

## Consequences

- Archive content, including Areas such as Rome's rioni, is not configuration. It enters the archive only through Submissions. Seeding Areas from an official dataset would be bulk import, which is out of scope.
- About, editorial guidelines, and policies are Operator texts in the Content language. They are not moderated and have no Revisions; their history is the configuration repository's history.
- Removing a vocabulary entry is always a retirement, so archive records never lose their values.
- An Operator upgrading TART may have to edit configuration by hand, following the release notes.
