# One untranslated Content language per Instance; UI languages are platform-wide and prefixed

Only the user interface is multilingual. Each Instance declares one Content language (Rome: Italian) in which all archive content and the Instance's own texts (archive name, About page, editorial guidelines) are written; none of it is translated, and it is rendered with its own `lang` (and `dir`) whatever the UI language. Sources and textual Documentation items may carry their own language tag. UI languages belong to the platform: each ships complete in the single prebuilt frontend image, and an Instance enables a subset and picks a default in its configuration files. Every UI language is URL-prefixed (`/it/…`, `/en/…`); only the root `/` redirects, by cookie, then `Accept-Language`, then the Instance default. We chose this because translated content would need per-language variants, translation moderation, and staleness tracking that a volunteer community cannot sustain, and because Paraglide fixes its unprefixed base locale and locale list at compile time, so a runtime-configured unprefixed default would need either a frontend build per Instance or undocumented runtime patching.

## Considered Options

- **Per-field translation variants of domain content**, as the brief allows "where appropriate": rejected as too costly to moderate and keep in sync for the MVP.
- **Unprefixed default UI language** (`/…` for Italian, as ADR 0004 first stated): requires one frontend build per Instance, or mutating Paraglide's `urlPatterns` at startup, which is not a documented API.

## Consequences

- Configured vocabulary labels (Expression type, Surface type, Decision message reasons) are UI: the Instance supplies one label per enabled UI language, and configuration validation fails if any is missing.
- A UI language is added only at platform level, complete; CI fails on any missing message key. An Instance can enable only languages its platform image contains. There is no translation platform in the MVP.
- The API returns stable error codes with parameters, translated by the frontend. Emails are rendered by the worker from a backend message catalogue held to the same missing-key check.
- Dates, numbers, and distances use `Intl` with the UI language and the Instance's explicit time zone; each Uncertain date precision and qualifier combination has its own platform message.
- Registered Users have a preferred UI language, also used for their emails (amended by [Notifications](https://github.com/spippoli/tart/issues/44)). A User's initial preferred UI language is the UI language of the page they registered from. If the Instance later disables it, their emails fall back to the Instance's default UI language. People without an account get emails in the UI language of the page they acted from: a notifier in that of the Notice form, stored with the Notice, and a sign-in code to an unregistered address in that of the sign-in page. An Invitation uses the issuing Moderator's UI language, or the Instance default when issued from the Operator CLI. Content quoted in an email (record titles, Decision message free text) keeps its own language, while configured labels (Decision message and Notice reasons) are translated into the recipient's language.
- Styles use CSS logical properties and set `dir` from the start; right-to-left UI languages are not tested in the MVP.
