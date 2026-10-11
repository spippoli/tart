# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

TART is a collaborative platform for documenting and preserving the history of urban art. The first deployment is Rome, but the software is meant to be reused by independent local communities ("Rome Urban Art Archive — Powered by TART").

The design phase is complete and implementation is under way, ticket by ticket. The monorepo has `backend/` (FastAPI), `frontend/` (SvelteKit), and `deploy/` (Docker Compose); the MVP tech stack is decided in `docs/adr/0004-mvp-tech-stack.md` and `docs/adr/0005-passwordless-in-app-auth.md`.

## Sources of truth

When they disagree, the earlier one wins:

1. This file: language rules, architectural invariants, implementation principles.
2. The ADRs in `docs/adr/`: hard-to-reverse decisions.
3. `GLOSSARY.md`: vocabulary. A term in **bold** in a spec carries exactly its glossary meaning.
4. The feature specs in `docs/spec/`, starting from `docs/spec/index.md`: normative behaviour, numbered acceptance criteria, testing decisions, and the Instance configuration keys with Rome's values.
5. `README.md`: the original design brief. It is background; where a spec or ADR narrows it, the decision wins.

## Implementation workflow

- **Work comes from implementation tickets**: GitHub issues labelled `ready-for-agent` (or `ready-for-human`), each a sub-issue of one of the seven spec tracking issues. Each ticket names the spec sections it covers, the acceptance criteria it must satisfy, and the tickets that block it.
- **Take a ticket** only when every issue in its "Blocked by" list is closed and it has no assignee. Assign it to yourself before any work; the assignee is the claim. Work one ticket per session.
- **One ticket, one branch, one PR**, with `Closes #N`. Every numbered acceptance criterion listed in the ticket gets a test, following the spec's Testing Decisions; UI work also passes axe with no WCAG 2.2 AA violations in `it` and `en`.
- **The spec is the scope.** Build what the ticket's sections and criteria require, and nothing past the spec's Out of Scope. If the spec is wrong, ambiguous, or silent on something that matters, stop and propose a spec change as its own PR (with an ADR when the decision is hard to reverse) instead of deciding it in code. Recommendations for implementers and open items marked as implementation detail in a spec's Further Notes are yours to decide.
- **Keep the docs in step**: a new domain term goes into `GLOSSARY.md`; a new command goes into Commands below.

## Commands

Versions are pinned: Python 3.14 with uv 0.13, Node 24 LTS with pnpm 11 (`packageManager` in `frontend/package.json`). CI (`.github/workflows/ci.yml`) runs the lint and test commands below on every pull request.

Backend (run in `backend/`):

```sh
uv sync                    # install, including dev tools
uv run ruff check .        # lint
uv run ruff format .       # format (CI runs `--check`)
uv run pytest              # all tests
uv run pytest tests/test_health.py   # one file
uv run uvicorn tart.api.app:create_app --factory --reload   # dev server on :8000
```

Frontend (run in `frontend/`):

```sh
pnpm install
pnpm dev                   # dev server
pnpm lint                  # prettier --check and eslint
pnpm format                # prettier --write
pnpm check                 # svelte-check (type checking)
pnpm test:unit             # vitest
pnpm exec playwright install chromium   # once, before e2e
pnpm test:e2e              # Playwright with axe, against a production build
pnpm build
```

Full stack (run in `deploy/`; copy `.env.example` to `.env` and set `POSTGRES_PASSWORD` first):

```sh
docker compose up --build              # caddy, frontend, api, worker, db
docker compose --profile dev up --build   # also Mailpit, UI on :8025
docker compose down                    # add -v to drop the volumes
```

Caddy serves `https://localhost` with a local certificate and routes `/api/*` to `api`, everything else to `frontend`; `GET /api/health` answers `ok`.

## Language rules (mandatory)

- **Talk to the user in Italian**: questions, plans, progress updates, summaries.
- **Write all project documentation in English**: README, specs, ADRs, architecture docs.
- **Write all code in English**: identifiers, comments, code-level docs.
- **UI is i18n from day one**: Italian (`it`) is the default, English (`en`) is the second language, and more must be easy to add. Never hardcode user-facing strings in components; this includes labels, validation messages, statuses, errors, aria labels, and empty states. Use locale-aware formatting for dates and numbers. Keep translatable UI resources separate from domain data, and never assume content language (descriptions, sources, artist names) matches the UI language.

## Architectural invariants

These come from the brief and apply to any implementation:

- **Multi-instance, not Rome-specific.** Rome is the initial *configuration*. Geography (bounds, default map view), branding, languages, artwork categories, metadata fields, moderation roles, registration policy, and providers (auth, storage, map, email) must be configurable per deployment. Keep the TART platform identity separate from the local archive's identity.
- **Map-provider agnostic.** Don't couple the core to a specific map library or provider.
- **Submissions are not archive records.** Community contributions (new artworks, edits, history updates) go through a moderation lifecycle (draft → submitted → approved/rejected → revised/resubmitted). Only approved data becomes authoritative. Proposed data must never be shown as accepted fact.
- **Disappearance is never deletion.** Destroyed, covered, removed, or deteriorated artworks remain full archival records. Their condition is recorded as a history event.
- **Two separate histories.** An artwork's *physical history* (a timeline of documented events such as first documentation, damage, overpainting, removal, or attribution changes) is distinct from the *edit/audit history* of its database record.
- **Uncertainty is first-class data.** Support unknown, estimated, and approximate dates with a precision level; unknown, uncertain, and disputed attribution; approximate locations; and verified vs. community-provided information. Keep distinct dates for observed, submitted, and approved.
- **Artist ≠ user.** A registered user does not automatically own or control an artist record.
- **The artwork location is not the submitter's location.**
- **Scope covers all urban expression**: murals, graffiti, stencils, paste-ups, stickers, installations, and more. Don't model artworks as murals only.
- **No engagement mechanics**: no likes, followers, popularity ranking, or engagement feeds.
- **Accessibility target**: WCAG 2.2 AA. Nothing essential may depend on hover, and status must never be conveyed by color alone.

## Implementation principles

Follow these in order of priority; when they pull against each other, the earlier one wins:

- **KISS**: choose the simplest design that meets the current requirement.
- **YAGNI**: build what the brief, an ADR, or the issue at hand requires. Introduce an abstraction when a second concrete case exists. The per-deployment configurability listed above is a stated requirement, so it counts as concrete.
- **Separation of concerns**: keep domain rules, persistence, UI, i18n resources, and provider integrations in distinct modules.
- **Low coupling, high cohesion**: group code that changes together; depend on narrow interfaces across module boundaries.
- **SOLID where it earns its place**: apply a principle when it solves a concrete problem in front of you, typically dependency inversion at provider boundaries (auth, storage, map, email). Simple code stays simple.
- **Hexagonal architecture where the domain justifies it**: use ports and adapters around domain-rich areas (moderation lifecycle, physical history, attribution and uncertainty) and swappable providers. Thin CRUD and glue code talk to the framework directly.

## Licensing and rights

- Software, the TART brand (name and logo), local archive data, user-generated content, and the rights to artworks themselves are **separate concerns**. Don't assume the software license covers any of the others.
- The intended model is non-commercial and source-available. **Never call TART "Open Source"** unless the final license meets the OSI definition. Use "source-available" or "freely available for non-commercial use" instead.
- The software is provisionally licensed under PolyForm Noncommercial 1.0.0 (`LICENSE`); the Licensing Decision Record is `docs/adr/0011-provisional-software-license.md`. Don't change the license, add a dependency outside its licence tiers, or write custom license terms without a new decision record, and flag legal review where interpretation is needed.

## Content

Use realistic content relevant to Rome, but never invent historical claims about real artworks or artists. Mark sample records as fictional, and don't use lorem ipsum.

## Agent skills

### Issue tracker

Issues live in GitHub Issues for `spippoli/tart`, via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `GLOSSARY.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.
