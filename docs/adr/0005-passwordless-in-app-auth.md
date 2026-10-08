# Passwordless authentication built into the app

Users sign in with a one-time code sent by email (6 digits, valid 10 minutes, with attempt and rate limits per email and per IP), with optional passkeys via py_webauthn. There are no passwords and no social login in the MVP. Authentication lives inside FastAPI rather than in an external identity provider. Without passwords, the remaining surface is small enough to own. An external IdP (Authentik, Zitadel, Keycloak) would cost 0.5–2 GB of RAM on a €20/month server and add a second login UI that TART cannot translate or keep WCAG 2.2 AA compliant through its own pipeline.

## Session model

FastAPI owns the session: an opaque session ID stored in PostgreSQL (no JWT, so revocation is immediate), set as an `HttpOnly; Secure; SameSite=Lax` cookie on the single origin that Caddy serves. SvelteKit forwards the user's cookie when it calls FastAPI over the internal network during server rendering. CSRF protection combines `SameSite=Lax`, an `Origin` check on state-changing requests, and a required custom header on API calls.

## Considered Options

- **fastapi-users**: password-centric and in maintenance mode since 2026, with an unnamed successor.
- **Authentik / Zitadel / Keycloak**: well maintained, but heavy for the budget, with a foreign login UI. Zitadel is also AGPL.
- **Ory Kratos**: ships no UI, and guaranteed CVE fixes require an enterprise licence.
- **Email + password**: rejected to avoid password storage, reset flows, and credential stuffing.

## Consequences

- Reliable email delivery is critical: if email is down, nobody can sign in.
- Authentication sits behind an interface so a later Instance can plug in an external OIDC provider; only the built-in implementation ships in the MVP.
- Roles (Moderator and future tiers) live in TART's database whatever the authentication method.
