# Research: self-hostable authentication for FastAPI

- **Ticket**: [#11](https://github.com/spippoli/tart/issues/11) (parent map [#2](https://github.com/spippoli/tart/issues/2))
- **Date**: 2026-10-08. Maintenance data was read from GitHub on this date.
- **Status**: research only. The choice belongs to the "Tech stack decision" ticket.

## Question

What are the options for authentication in a FastAPI app that must be self-hostable, configurable per instance, and light enough for a small VPS? The ticket asks for a comparison of built-in libraries (e.g. fastapi-users, Authlib) and external identity providers (Keycloak, Authentik, Zitadel, Ory) on these criteria:

- email/password
- magic links
- OAuth providers
- role management
- footprint
- maintenance
- license

## Constraints from the project

- **One Instance per deployment** ([ADR 0001](../adr/0001-one-instance-per-deployment.md)). Users are local to their Instance, and no account is shared across Instances. So an external IdP would be one more service in every Instance's stack (or one realm per Instance), not a shared SSO hub.
- **Budget and deployment.** The reference target is a self-hostable Docker Compose stack, with Rome running on at most €20/month (map #2). PostgreSQL/PostGIS already runs in the stack.
- **Configurability.** The README lists "authentication configuration", "registration policy", "moderation roles", and "email" as per-deployment settings (README, "Platform" and "Community" configuration).
- **Domain.** A **User** is a registered account on an Instance. A **Moderator** is a role held by a User. A User never implies control over an Artist (`GLOSSARY.md`). Users must register to contribute (README, "User and moderation").
- **i18n.** Every user-facing screen, including login, registration, and recovery, must be translatable (it, en, and more).

## Findings by option

### A. In-app libraries

#### fastapi-users

- **Features**: register, login, reset password, and verify e-mail routes; social OAuth2 login; cookie or bearer transport; JWT, database, or Redis session strategies; SQLAlchemy async backend ([README](https://github.com/fastapi-users/fastapi-users)). Magic links and passkeys are not on the feature list.
- **Roles**: only `is_superuser` / `is_verified` flags in the base model. Moderator roles would be custom code.
- **Maintenance**: the README says: "**This project is now in maintenance mode.** ... we'll continue to provide security updates and dependency maintenance, no new features will be added." It also says a new toolkit "will ultimately supersede FastAPI Users", but that toolkit is not named or published. Latest release: v15.0.5 (2026-03-27). Last push: 2026-08-17.
- **License**: MIT.
- **Footprint**: none beyond the app. It depends on `pwdlib[argon2,bcrypt]`, `pyjwt`, `email-validator`, and `python-multipart` ([pyproject](https://github.com/fastapi-users/fastapi-users/blob/master/pyproject.toml)).
- **Related**: Fief, the same author's hosted or self-hosted auth server built on FastAPI Users, says it won't be "adding new features or fixing bugs in this codebase anymore" ([README](https://github.com/fief-dev/fief)). It is not a viable candidate.

#### Authlib (with httpx-oauth / pwdlib as building blocks)

- **Scope**: OAuth 1/2 and OpenID Connect client and server, plus JOSE. Starlette/FastAPI client integrations exist ([docs source](https://github.com/authlib/authlib/tree/main/docs/oauth2/client/web)). It is not a user-management library: there is no registration, password storage, recovery, or roles. Those would be our code.
- **Maintenance**: active. Latest release v1.8.0 (2026-08-30). Pushed 2026-10-08 ([repo](https://github.com/authlib/authlib)).
- **License**: BSD-3-Clause.
- **Related building blocks**:
  - [httpx-oauth](https://github.com/frankie567/httpx-oauth): MIT, v0.17.0 (2026-05-13), active. It is the OAuth client used by fastapi-users.
  - [pwdlib](https://github.com/frankie567/pwdlib): MIT, v0.3.1 (2026-08-12). It does Argon2/bcrypt hashing.
- **Implication**: a "build on libraries" path means TART owns registration, verification, recovery, magic-link tokens, session handling, rate limiting, and the security review of all of it. In exchange, the UI is fully i18n under TART's own control, and there are no extra containers.

### B. External identity providers (OIDC)

The FastAPI app would act as an OIDC client (e.g. via Authlib). The IdP would own credentials, the login/registration UI, recovery, and federation.

#### Keycloak

- **Features**: password login, self-registration toggle, social and OIDC/SAML identity brokering, WebAuthn/passkeys, realm and client roles, and groups.
- **Magic links**: not built in. Upstream "passwordless" means WebAuthn or OTP. Email magic links need the third-party Phase Two extension [p2-inc/keycloak-magic-link](https://github.com/p2-inc/keycloak-magic-link) ([Phase Two docs](https://phasetwo.io/docs/authentication/magic-links/)).
- **Footprint**: "The base memory usage for a Pod including caches of Realm data and 10,000 cached sessions is 1250 MB of RAM". CPU: 1 vCPU per 15 password logins/s ([sizing guide](https://www.keycloak.org/high-availability/multi-cluster/concepts-memory-and-cpu-sizing)). This is an HA sizing guide, so a tiny single node may run lower, but it is the only official figure. Production databases include PostgreSQL. The `dev-file` default is deprecated for production ([containers guide](https://www.keycloak.org/server/containers)).
- **Maintenance**: very active, with a frequent cadence. Latest 26.8.0 (2026-10-01), plus patch releases 26.7.3–26.7.5 in Aug–Sep 2026 ([releases](https://github.com/keycloak/keycloak/releases)). It is a CNCF project.
- **License**: Apache-2.0.

#### Authentik

- **Features**: flows and stages model; enrollment (self-registration) flows; social and OIDC sources; WebAuthn; groups and RBAC. The Email stage is documented for "email verification, account recovery, invitations, and similar flow steps where authentik should send a tokenized link". The stage page does not document using it as a passwordless magic-link login ([Email stage](https://docs.goauthentik.io/add-secure-apps/flows-stages/stages/email/)), so treat magic links as plausible but unverified.
- **Footprint**: "A host with at least 2 CPU cores and 2 GB of RAM" ([Docker Compose install](https://docs.goauthentik.io/install-config/install/docker-compose/)). The components are server, worker, and PostgreSQL ([architecture](https://docs.goauthentik.io/core/architecture/)). Redis was removed entirely in 2025.10, and Postgres takes about 50% more connections as a result ([2025.10 release notes](https://docs.goauthentik.io/releases/2025.10/), [blog](https://goauthentik.io/blog/2025-11-13-we-removed-redis/)).
- **Maintenance**: very active. Latest release version/2026.8.3 (2026-09-17) ([repo](https://github.com/goauthentik/authentik)).
- **License**: MIT for the core. The `authentik/enterprise/` directory is under a separate enterprise license, and `website/` is under CC BY-SA 4.0 ([LICENSE](https://github.com/goauthentik/authentik/blob/main/LICENSE)).

#### Zitadel

- **Features**: username/password, passkeys, external IdPs, and a "Register allowed" self-registration toggle. Email OTP is listed only as a second factor ([default settings](https://zitadel.com/docs/guides/manage/console/default-settings)). Roles are project roles with grants. Zitadel's own multi-tenancy (instances and organizations) is unnecessary given ADR 0001.
- **Footprint**: "ZITADEL itself requires approximately 512MB of RAM and can operate with less than one CPU core". The docs recommend 4 cores for password-hashing spikes in production ([production guide](https://zitadel.com/docs/self-hosting/manage/production)). The database is PostgreSQL. The Compose stack is the Zitadel API (Go) plus a separate Login UI (Next.js) plus PostgreSQL, behind Traefik ([Compose guide](https://zitadel.com/docs/self-hosting/deploy/compose)).
- **Maintenance**: very active. Latest v4.19.4 (2026-10-01) ([repo](https://github.com/zitadel/zitadel)).
- **License**: AGPL-3.0. This is relevant to TART's licensing work: running it unmodified as a separate service is a common pattern, but the interaction with TART's own non-commercial, source-available license should be noted in the Licensing Decision Record.

#### Ory Kratos (+ Keto for permissions)

- **Features**: headless identity API. Its flows are password, OIDC social sign-in, one-time "code" via recovery addresses, recovery link, verification, and 2FA ([self-service docs](https://www.ory.com/docs/kratos/self-service)). It ships **no UI**: the app "is responsible for rendering the actual Login and Registration HTML Forms" (same page). Roles are not part of Kratos. They belong in Ory Keto or the app.
- **Footprint**: a single Go binary. The supported databases include PostgreSQL ([README](https://github.com/ory/kratos)). No official RAM figure was found.
- **Maintenance and licensing caveat**: the code is Apache-2.0, but the README says the open-source distribution is for "unimportant workloads without SLAs". It says that "for guaranteed CVE fixes, current enterprise builds ... you need a valid Ory Enterprise License" ([README](https://github.com/ory/kratos)). The latest OSS release is v26.2.0 (2026-03-20), with a last push on 2026-07-29. That is a markedly slower public cadence than Keycloak, Authentik, or Zitadel.

#### Pocket ID (light-weight reference point, not in the ticket)

- **Features**: an OIDC-certified provider that is "passwordless ... primarily passkeys", with no passwords ([docs](https://pocket-id.org/docs/)). It added self-service signup ([PR #672](https://github.com/pocket-id/pocket-id/pull/672), 2025-06) and email login codes ([PR #457](https://github.com/pocket-id/pocket-id/pull/457), 2025-04).
- **Maintenance**: active. v2.18.0 (2026-10-04).
- **License**: BSD-2-Clause.
- **Fit**: there is no email/password login, which may exclude it for a broad community audience.

## Comparison

| Option | Email/password | Magic link | OAuth / social | Roles | Extra footprint | Maintenance (2026-10-08) | License |
|---|---|---|---|---|---|---|---|
| fastapi-users | Yes | No | Yes (httpx-oauth) | Flags only; custom | None | **Maintenance mode**: security fixes only | MIT |
| Authlib + pwdlib (DIY) | Build it | Build it | Yes (client) | Custom | None | Active | BSD-3 / MIT |
| Keycloak | Yes | Extension only | Yes, brokering | Rich (realm/client roles, groups) | JVM; 1250 MB/pod official HA baseline | Very active | Apache-2.0 |
| Authentik | Yes | Unverified (email-stage flows) | Yes | Groups/RBAC | Server + worker; min 2 CPU / 2 GB | Very active | MIT core + enterprise dir |
| Zitadel | Yes | No (email OTP as 2FA only) | Yes | Project roles | ~512 MB + Next.js login container | Very active | AGPL-3.0 |
| Ory Kratos | Yes | Code via email | Yes | None (Keto) | Small Go binary; **no UI** | OSS slower; CVE SLA behind enterprise license | Apache-2.0 (+ OEL) |
| Pocket ID | **No** (passkeys) | Email login code | No social federation found | Groups | Small | Active | BSD-2 |

## Analysis against TART's needs

1. **Footprint versus budget.** Keycloak (≥1.25 GB official baseline) and Authentik (2 CPU / 2 GB minimum) each claim a large share of a small VPS that must also run PostgreSQL/PostGIS, the API, the frontend, and tile serving. Zitadel is lighter (~512 MB) but adds a second web container. In-app libraries add nothing. The actual VPS size bought for €20/month is an assumption to verify in the stack decision.
2. **i18n and UX ownership.** With an IdP, the login, registration, recovery, and verification screens live in the IdP's theming and translation system, not in TART's i18n pipeline. Translation and WCAG 2.2 AA compliance of those screens become the IdP's responsibility, or TART's work in a foreign theming system. Kratos avoids this because TART renders the UI, but then TART builds every screen.
3. **Roles belong in TART.** The Moderator role and future role tiers are domain concepts tied to Submissions, self-moderation rules, and audit (see map: "Moderation roles in detail"). Under every option, the authoritative permission model will likely live in TART's database. The IdP role systems would at most carry a coarse flag. So rich IdP RBAC is a weak argument for an IdP.
4. **Per-instance configurability.** Social providers, the registration policy (open, invite, closed), and SMTP must be per-Instance settings. An IdP gives these as admin-console configuration. A library approach makes them TART configuration files, which is consistent with "Rome is configured from files".
5. **Maintenance risk.**
   - fastapi-users is stable but frozen, and has an announced but unnamed successor.
   - A DIY path on Authlib/pwdlib shifts security-critical code into TART.
   - Kratos's open-source tier explicitly lacks guaranteed CVE fixes.
   - Keycloak, Authentik, and Zitadel are the best-maintained, but are the heaviest.

## Strongest candidates (for the stack decision to weigh)

1. **In-app: fastapi-users (or a thin DIY layer on Authlib + pwdlib + httpx-oauth) with roles in TART's DB.** This option has zero extra services, full i18n and accessibility control, and file-based per-instance configuration. Its risks are the maintenance-mode status and owning magic-link and recovery security. The mitigation is to keep auth behind an adapter seam so it can be swapped later.
2. **External IdP: Authentik, or Zitadel if the AGPL is acceptable.** Both are actively maintained, PostgreSQL-only, and self-registration-capable, with mature social login. The cost is extra RAM, a second UI to theme and translate, and one more upgrade stream per Instance.
3. **Keycloak** is the most feature-complete and conservative choice. It is the heaviest, and needs a third-party extension for magic links.

Ory Kratos is the weakest fit for a volunteer-run community instance, because it has no UI and gates CVE SLAs behind its enterprise license. Pocket ID is ruled out if email/password is required.

## Open questions surfaced

- Is **email/password** required at all, or would magic link / email code + social + passkeys suffice? Dropping passwords simplifies the in-app option considerably.
- Which **social providers** (if any) should Rome enable, given privacy expectations and GDPR?
- How is the **VPS sized** (RAM/CPU) for €20/month, and what is the RAM budget per service? This decides whether a JVM- or Python-based IdP fits.
- Should **authentication be an adapter** (README lists auth among swappable providers), so an Instance can switch from built-in auth to an external OIDC IdP?
- What are the **AGPL implications** (Zitadel) for TART's licensing model? This is for the Licensing Decision Record.
- **Account deletion and GDPR data export** for Users, given that Revisions must keep attribution to a Submitter. This is a domain question independent of the auth choice.

## Sources

- fastapi-users: https://github.com/fastapi-users/fastapi-users
- Fief: https://github.com/fief-dev/fief
- Authlib: https://github.com/authlib/authlib
- httpx-oauth: https://github.com/frankie567/httpx-oauth
- pwdlib: https://github.com/frankie567/pwdlib
- Keycloak sizing: https://www.keycloak.org/high-availability/multi-cluster/concepts-memory-and-cpu-sizing
- Keycloak containers: https://www.keycloak.org/server/containers
- Keycloak releases: https://github.com/keycloak/keycloak/releases
- Keycloak magic link extension: https://github.com/p2-inc/keycloak-magic-link
- Authentik install: https://docs.goauthentik.io/install-config/install/docker-compose/
- Authentik architecture: https://docs.goauthentik.io/core/architecture/
- Authentik 2025.10 (Redis removal): https://docs.goauthentik.io/releases/2025.10/
- Authentik Email stage: https://docs.goauthentik.io/add-secure-apps/flows-stages/stages/email/
- Authentik license: https://github.com/goauthentik/authentik/blob/main/LICENSE
- Zitadel production: https://zitadel.com/docs/self-hosting/manage/production
- Zitadel Compose: https://zitadel.com/docs/self-hosting/deploy/compose
- Zitadel login settings: https://zitadel.com/docs/guides/manage/console/default-settings
- Ory Kratos README: https://github.com/ory/kratos
- Ory Kratos self-service flows: https://www.ory.com/docs/kratos/self-service
- Pocket ID: https://pocket-id.org/docs/ and https://github.com/pocket-id/pocket-id
