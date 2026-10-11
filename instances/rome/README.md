# Rome's Instance configuration

The configuration directory of the Rome Urban Art Archive, TART's reference
Instance ([Foundations spec, Instance configuration](../../docs/spec/foundations.md#instance-configuration)).
It is secret-free: secrets and infrastructure come from the environment
(`deploy/.env.example`). Point `CONFIG_DIR` at this directory to run it, and validate
it with `tart config check`; the backend tests load it as the loader's valid case
with Rome's real values.

## Launch values

Some values are facts only the real Rome Operator has
([Rome's launch values](../../docs/spec/foundations.md#romes-launch-values)). Until
launch they are obviously fictional placeholders, marked `LAUNCH VALUE` in
`instance.toml`:

- `operator.name`: the legal name of the operating association;
- `contacts.general`, `contacts.dsa`, `contacts.privacy`: role addresses on the
  archive's own domain (here on `example.org`);
- `identity/logo.*.svg` and `identity/favicon.svg`: a provisional wordmark, below.

The Operator texts in `texts/` are not written yet: each one says so in its first
line. Drafting the terms of use and the privacy policy is out of scope of the
platform.

## Identity

Until a designed logo exists, the logo is a provisional typographic wordmark: the
archive name set in Noto Sans Bold (SIL Open Font License 1.1, no Reserved Font
Name) and converted to paths, in the map ink of each theme (`#2A2521` light,
`#EAE2D5` dark). The favicon is a letter "R" in `#7A2E1C` on `#F3EEE2`, from the same
font.

## Map

The map style files (`map/style.light.json`, `map/style.dark.json`) and their assets
are not here yet: Rome's style comes with the Discovery tickets.

## Licences

The TART software licence does not cover this directory. The boundary in
`geography/` is OpenStreetMap data under the ODbL (see `geography/README.md`).
