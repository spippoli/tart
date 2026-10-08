# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

TART is a collaborative platform for documenting and preserving the history of urban art. The first deployment is Rome, but the software is meant to be reused by independent local communities ("Rome Urban Art Archive — Powered by TART").

The repository is at the design stage: there is no source code, build system, test suite, or chosen tech stack yet. `README.md` contains the full design brief and is the source of truth for product requirements. Read the relevant sections before making product, architecture, or licensing decisions. When a stack is introduced, add its build/lint/test commands to this file.

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

## Licensing and rights

- Software, the TART brand (name and logo), local archive data, user-generated content, and the rights to artworks themselves are **separate concerns**. Don't assume the software license covers any of the others.
- The intended model is non-commercial and source-available. **Never call TART "Open Source"** unless the final license meets the OSI definition. Use "source-available" or "freely available for non-commercial use" instead.
- Don't pick or write a license silently. Candidates such as PolyForm Noncommercial and the Business Source License must be evaluated in a Licensing Decision Record, with legal review flagged where interpretation is needed.

## Content

Use realistic content relevant to Rome, but never invent historical claims about real artworks or artists. Mark sample records as fictional, and don't use lorem ipsum.

## Agent skills

### Issue tracker

Issues live in GitHub Issues for `spippoli/tart`, via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `GLOSSARY.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.
