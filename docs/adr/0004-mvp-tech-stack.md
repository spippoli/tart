# MVP tech stack and reference topology

The MVP is a monorepo (`backend/`, `frontend/`, `deploy/`) built on FastAPI and PostgreSQL/PostGIS, with a SvelteKit server-rendered frontend, deployed as a six-service Docker Compose stack behind Caddy. We chose the simplest stack that meets server-rendered SEO for public archive pages, i18n from day one, WCAG 2.2 AA, a map-provider-agnostic core, and a Rome budget of at most €20/month excluding VAT and off-site backups. Research inputs: frontend framework (#9), media pipeline and storage (#10), and self-hostable authentication (#11).

## Decisions

- **Frontend**: SvelteKit 3 with adapter-node, Paraglide JS for i18n (unprefixed `it`, `/en/…`, translated pathnames, `hreflang` written once in the root layout), with pinned versions. A missing message key is a build error.
- **Map**: plain MapLibre GL JS and the `pmtiles` protocol, used only inside one app-level map module; no other code imports MapLibre. No framework wrapper.
- **API client**: `openapi-typescript` + `openapi-fetch`, generated from FastAPI's OpenAPI schema. CI fails on drift.
- **Backend**: FastAPI, SQLAlchemy 2.0 (async) with GeoAlchemy2, and Alembic migrations run at `api` startup.
- **Background jobs**: Procrastinate on PostgreSQL, in a separate `worker` container that shares the `api` image, with its own memory and time limits. It handles media derivatives, PDF previews, email delivery, and cleanup of abandoned uploads.
- **Storage**: a storage adapter with a local-filesystem implementation (the minimal default) and an S3-compatible implementation. The Rome reference uses Hetzner Object Storage. There is no self-hosted S3 server in the reference stack. All objects are private and served through the app, so hiding pending or withdrawn media is a database flag.
- **Uploads**: the browser streams multipart uploads to FastAPI, which writes to a quarantine area and enqueues processing. Uploads never pass through SvelteKit. Size limits are enforced by both Caddy and the app.
- **Media processing**: Pillow (WebP renditions, EXIF orientation applied, metadata stripped), pillow-heif for HEIC, pypdfium2 for PDF first-page previews. PyMuPDF (AGPL) and libvips are excluded.
- **Email**: a generic SMTP adapter configured per Instance. Mailpit in development.
- **Reverse proxy**: Caddy (automatic HTTPS, byte-range requests for same-origin PMTiles, routing, upload limits).
- **Tooling**: uv, ruff, pytest; pnpm, vitest, Playwright with axe; a dependency licence allow-list check in CI.

## Topology

| Service | Role |
|---|---|
| `caddy` | HTTPS, routes `/api/*` to `api` and everything else to `frontend`, serves PMTiles |
| `frontend` | SvelteKit Node server |
| `api` | FastAPI |
| `worker` | Procrastinate worker (same image as `api`) |
| `db` | PostgreSQL + PostGIS (current supported majors at implementation time) |
| `mailpit` | Development only, via a Compose profile |

Storage is a local volume or an external S3 bucket. Backups are outside the budget and are designed with operations.

Reference sizing: minimum profile 4 GB RAM, recommended 8 GB. Rome targets a Hetzner CX33 (4 vCPU / 8 GB) plus Object Storage, about €15/month excluding VAT and IPv4.

## Considered Options

- **Next.js 16 + next-intl**: the most mature i18n routing and largest ecosystem, rejected for the heavier conceptual model (RSC, caching rules) for volunteer maintainers. **Nuxt 4** is comparable but has a smaller community. **Astro** handles routing only and is weak for an app-heavy UI. A **Vite SPA** fails the SEO requirement.
- **MinIO**: archived in April 2026, with no maintained builds.
- **Celery**: needs a separate broker, which adds a service for no gain at this scale.

## Consequences

- SvelteKit 3.0 was released on 2026-10-01; expect lagging ecosystem docs. Pin versions.
- MapLibre v6 requires WebGL2, so the list-based browse path must be fully functional without the map.
- Per-container memory use is unmeasured. Measuring it on the first prototype is an explicit risk to the €20/month target.
- Licence notes for the Licensing Decision Record: PostGIS (GPL-2.0+) and the HEVC codecs bundled with pillow-heif.
