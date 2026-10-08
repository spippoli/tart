# Research: frontend framework for TS + MapLibre + i18n with FastAPI

- **Ticket**: [#9](https://github.com/spippoli/tart/issues/9) (parent map: [#2](https://github.com/spippoli/tart/issues/2))
- **Date**: 2026-10-08
- **Status**: research input, not a decision. The choice belongs to the "Tech stack decision" ticket.

## Question

Which TypeScript frontend approach (SvelteKit, Next.js, Astro with islands, Vite SPA, or others) best fits:

- a FastAPI + PostgreSQL/PostGIS backend (decided, see #2);
- MapLibre GL JS + PMTiles for self-hosted tiles (decided, see #2);
- i18n from day one: `it` default, `en` second, extensible; locale-aware formatting; localized routes (`CLAUDE.md`, README §14);
- WCAG 2.2 AA, nothing essential on hover, no color-only status (README §20);
- SEO for public archive pages (Artwork, Artist, Site, Area pages);
- a self-hostable Docker Compose stack on a VPS within €20/month for the Rome Instance;
- long-term maintainability by a small, volunteer-friendly community?

Also: compare i18n libraries for the shortlisted options and check dependency license compatibility.

## Short answer

1. **Rendering model matters more than the framework brand.** Public archive pages need server-rendered HTML with per-locale URLs and `hreflang`. A pure Vite SPA fails the SEO criterion for database-driven pages, and FastAPI cannot render the TypeScript UI itself. So the realistic shape is **a Node SSR frontend container next to the FastAPI container**, with the frontend calling FastAPI through a client generated from FastAPI's OpenAPI 3.1 schema.
2. **Strongest fit: SvelteKit + Paraglide JS (+ `svelte-maplibre-gl` or plain MapLibre).** Paraglide is SvelteKit's officially recommended i18n add-on. It supports localized URLs (`/en/...` with an unprefixed default locale), translated pathnames, plurals via `Intl.PluralRules`, and `Intl`-based number/date formatting. adapter-node gives a plain `node build` server that fits Docker Compose and needs no vendor-specific cache layer. The Svelte compiler emits about 40 `a11y_*` warnings at build time. **Main risk:** SvelteKit 3.0.0 shipped on 2026-10-01, a week before this research, with many breaking changes (Vite 8, TypeScript 6, Node ≥ 22.17, `$lib` → `#lib`). Third-party guides and examples will lag for a few months.
3. **Strong alternative: Next.js 16 + next-intl.** This is the most mature i18n routing story: `localePrefix: 'as-needed'`, localized `pathnames`, and automatic `hreflang` `Link` headers. It has the biggest ecosystem (`@vis.gl/react-maplibre`), and self-hosting with `next start` is officially documented. **Costs:** a heavier runtime and more conceptual surface (RSC, caching, static vs dynamic rendering rules) for volunteer maintainers. Static rendering with next-intl also needs extra setup (`next/root-params` or `setRequestLocale` + `generateStaticParams`).
4. **Viable but a weaker fit: Astro 7 with islands (+ Paraglide).** Astro is good for content pages. But TART is application-heavy (map/list sync, Submission forms, moderation comparison), and Astro's built-in i18n handles routing only, with no UI message library. Custom locale paths require `output: "server"`. Astro has been owned by Cloudflare since January 2026. It stays MIT and deployable anywhere, but it is worth watching.
5. **Also viable: Nuxt 4 + @nuxtjs/i18n (Vue).** It has a complete i18n/SEO feature set (`useLocaleHead` for `hreflang`, canonical, `og:locale`). It is not in the ticket's list but is a credible equal to Next.js. Like Next.js, it is backed by Vercel (NuxtLabs joined in July 2025).
6. **Licenses:** every candidate framework, i18n library, and map library checked is MIT, BSD-3-Clause, or MIT/Apache-2.0. These are permissive and compatible with any source-available license TART might pick (e.g. PolyForm Noncommercial), provided their notices are kept. The real licensing constraint on the map side is **data**, not code: OpenStreetMap-derived basemap tiles (Protomaps) are ODbL Produced Works and require OSM attribution.

## Versions and maintenance status (npm registry, 2026-10-08)

Source: `https://registry.npmjs.org/<package>` (`dist-tags.latest`, `license`, `time`, `peerDependencies`, `engines`).

| Package | Latest | License | Released | Notes |
|---|---|---|---|---|
| `@sveltejs/kit` | 3.0.1 | MIT | 2026-10-06 | 3.0.0 on 2026-10-01; peers: `svelte ^5.57.1`, `vite ^8.0.12`, `typescript ^6`; Node ≥ 22.17 |
| `svelte` | 5.57.2 | MIT | 2026-10-06 | |
| `@sveltejs/adapter-node` | 6.0.0 | MIT | 2026-10-01 | requires Kit 3 |
| `@inlang/paraglide-js` | 2.26.0 | MIT | 2026-10-06 | peers: `vite >=5`, `typescript >=5.6` |
| `svelte-i18n` | 4.0.1 | MIT | 2024-10-21 | no release in ~2 years |
| `svelte-maplibre-gl` (MIERUNE) | 2.2.1 | MIT OR Apache-2.0 | 2026-08-15 | peer `maplibre-gl ^5.19 \|\| ^6` |
| `next` | 16.4.0 | MIT | 2026-10-06 | |
| `react` | 19.3.0 | MIT | 2026-09-09 | |
| `next-intl` | 4.14.9 | MIT | 2026-10-02 | peers Next 12–16 |
| `react-intl` (FormatJS) | 12.1.4 | BSD-3-Clause | 2026-10-05 | |
| `i18next` / `react-i18next` | 26.4.2 / 17.0.16 | MIT | 2026-09 / 2026-10 | |
| `@lingui/core` | 6.9.0 | MIT | 2026-10-01 | |
| `@vis.gl/react-maplibre` | 8.1.3 | MIT | 2026-09-02 | peer `maplibre-gl >=4` |
| `astro` | 7.3.8 | MIT | 2026-10-08 | Node ≥ 22.12 |
| `@astrojs/node` | 11.1.7 | MIT | 2026-10-06 | |
| `nuxt` / `@nuxtjs/i18n` / `vue-i18n` | 4.6.0 / 10.6.0 / 11.4.13 | MIT | 2026-07…10 | |
| `vite` | 8.3.4 | MIT | 2026-10-08 | |
| `maplibre-gl` | 6.13.0 | BSD-3-Clause | 2026-10-06 | v6: ESM-only, WebGL2 required |
| `pmtiles` | 4.5.0 | BSD-3-Clause | 2026-08-10 | |
| `@hey-api/openapi-ts` | 0.99.0 | MIT | 2026-06-22 | pre-1.0 |
| `openapi-typescript` | 7.13.0 | MIT | 2026-02-11 | |

All candidates are actively released, except `svelte-i18n`.

## Cross-cutting findings (framework-independent)

### MapLibre GL JS v6 and PMTiles

- MapLibre GL JS is at v6. v6 is **ESM-only**: UMD/CSP bundles are gone, and `<script>` tags must use `type="module"`. **WebGL1 support was removed, so WebGL2 is now required.** The build targets ES2022. Sources: [MapLibre docs](https://maplibre.org/maplibre-gl-js/docs/), [CHANGELOG 6.0.0](https://github.com/maplibre/maplibre-gl-js/blob/main/CHANGELOG.md).
  - *Implication:* the map needs a non-WebGL fallback for devices without WebGL2. A synchronized list view is required anyway by README §15 and WCAG; it should be a first-class way to browse, not a degraded mode.
- Under a strict Content Security Policy, MapLibre needs `worker-src 'self'` and `img-src data: blob: 'self'`, or an explicit `setWorkerUrl`. For Vite-based SSR frameworks (the docs name Astro and TanStack Start), add `ssr: { noExternal: ['maplibre-gl'] }` when the CommonJS entry is resolved on the server. Next.js ≥ 15 handles worker minification properly. Source: [MapLibre docs](https://maplibre.org/maplibre-gl-js/docs/).
- The map must be client-only in every framework (WebGL in the browser). SSR frameworks still render the page shell, Artwork details, and lists on the server. Only the map island hydrates.
- PMTiles in MapLibre: `npm install pmtiles`, then `maplibregl.addProtocol("pmtiles", protocol.tile)` **once** at app root, and use `pmtiles://https://…` source URLs. Source: [Protomaps: PMTiles for MapLibre](https://docs.protomaps.com/pmtiles/maplibre).
- Serving PMTiles needs **HTTP Range requests**. Cross-origin serving needs CORS that allows `GET`/`HEAD`, allows the `Range` and `If-Match` headers, and exposes `ETag`. Caddy (`file_server`) or nginx (with `OPTIONS` preflight handling) are documented options. Source: [Protomaps: Cloud storage](https://docs.protomaps.com/pmtiles/cloud-storage). This is a reverse-proxy concern, independent of the frontend framework. Serving tiles same-origin from the Compose stack's proxy avoids CORS entirely.
- The Protomaps basemap is an **ODbL Produced Work; OpenStreetMap attribution is required**. Regional extracts use `pmtiles extract` with `--maxzoom` to control size (the planet is about 120 GB at z0–15). Source: [Protomaps: Basemap downloads](https://docs.protomaps.com/basemaps/downloads).
- Framework wrappers: `svelte-maplibre-gl` (Svelte 5, MIT/Apache-2.0, peer `maplibre-gl ^6`, [repo](https://github.com/MIERUNE/svelte-maplibre-gl)) and `@vis.gl/react-maplibre` (MIT, peer `maplibre-gl >=4`). For all frameworks, plain imperative MapLibre inside one component is also realistic, and it limits wrapper lock-in. That fits the "map-provider agnostic" invariant: wrap MapLibre behind an app-level map module either way.

### FastAPI integration

- FastAPI emits **OpenAPI 3.1**. Its docs recommend generating a TypeScript client with **Hey API** (`npx @hey-api/openapi-ts -i …/openapi.json -o src/client`) or OpenAPI Generator. They also recommend `generate_unique_id_function` to get clean method names. Source: [FastAPI: Generating SDKs](https://fastapi.tiangolo.com/advanced/generate-clients/).
- This works identically for every candidate, so it is not a differentiator. Risk: `@hey-api/openapi-ts` is pre-1.0 (0.99.0). `openapi-typescript` (7.x, types only) is a stable lower-level alternative.
- Architecture for SSR candidates: the browser talks to the frontend server, and the frontend server talks to FastAPI on the internal Compose network (server-side `load` / server components). Browser-side calls (e.g. map viewport queries) can go straight to FastAPI through the same reverse proxy. Auth/session ownership (frontend cookie vs FastAPI token) still needs a decision. See "New questions" below.

### Hosting footprint

- Every SSR option adds **one Node process** (a container) next to FastAPI, PostgreSQL/PostGIS, and the reverse proxy. Node ≥ 22.12 is required by Astro 7, and Node ≥ 22.17 by SvelteKit 3.
- SvelteKit adapter-node: `node build`, configured by env vars (`PORT`, `HOST`, `BODY_SIZE_LIMIT` default 512K, which matters for image uploads if they proxy through SvelteKit, `SHUTDOWN_TIMEOUT`, …). It precompresses assets (`.br`/`.gz`) and drains gracefully on SIGTERM. Compression is best left to the reverse proxy. Source: [SvelteKit adapter-node](https://svelte.dev/docs/kit/adapter-node).
- Next.js `next start`: image optimization, Proxy (middleware), ISR, and caching work self-hosted with zero config on **a single instance with persistent disk**. Multi-instance deployments need a shared cache handler, `NEXT_SERVER_ACTIONS_ENCRYPTION_KEY`, and `deploymentId`. nginx must disable buffering for streaming. On glibc, `sharp` image optimization may need memory-allocator tuning. Source: [Next.js: Self-hosting](https://nextjs.org/docs/app/guides/self-hosting) (docs v16.4.0).
- No primary source publishes comparable memory figures. Measure RAM on a prototype before committing to a VPS tier.

## Framework-by-framework

### SvelteKit 3 (+ Svelte 5)

- **i18n:** Paraglide JS is installed with `npx sv add paraglide`. The Svelte CLI sets up the Vite plugin, the `reroute` and `handle` hooks, and `lang`/`dir` in `app.html` ([Svelte CLI: paraglide](https://svelte.dev/docs/cli/paraglide), [Paraglide: SvelteKit](https://paraglidejs.com/sveltekit)). Strategy chain example: `['url', 'cookie', 'baseLocale']`.
- **Localized routes:** with the URL strategy, the base locale is unprefixed (`/about`) and others are prefixed (`/en/about`). `urlPatterns` map canonical paths to translated pathnames (e.g. `/about` → `/ueber-uns`), and `localizeHref()` builds links ([Paraglide: i18n routing](https://paraglidejs.com/i18n-routing)). The docs note SvelteKit "needs every locale prefixed" in some setups and add an explicit root pattern. Validate `it`-unprefixed + `/en/` with a prototype.
- **SEO:** the Paraglide docs do not generate `hreflang` alternates. They must be written in a layout (easy: iterate locales × `localizeHref`). Prerendering works (`prerender = true`), but archive pages are database-driven and would be SSR.
- **Formatting:** messages support variants and plurals (`Intl.PluralRules`, ordinals), plus gender-like selectors ([Variants](https://paraglidejs.com/variants)). The `number`, `datetime`, `plural`, and `relativetime` formatters wrap `Intl.*` and use the current locale. Set an explicit `timeZone` for stable SSR/CSR output ([Formatting](https://paraglidejs.com/formatting)).
- **Message format:** the docs show the inlang message format (JSON). ICU/i18next file formats via plugins were not confirmed in the pages read, so verify before relying on them with external translation tools.
- **Type safety and bundle size:** a compiler emits tree-shakable, typed message functions. A missing key is a build error, which helps enforce "never hardcode strings".
- **Accessibility:** the Svelte compiler emits about 40 `a11y_*` warnings (e.g. `a11y_missing_attribute`, `a11y_positive_tabindex`) at build time ([Compiler warnings](https://svelte.dev/docs/svelte/compiler-warnings)). These help but don't replace axe/Playwright checks and manual testing.
- **Maintenance:** very active (Kit 3.0.1 on 2026-10-06). **Risk:** the 3.0 major is one week old. Breaking changes: Vite 8 (`^8.0.12`), TypeScript 6, Node ≥ 22.17, removal of `$app/stores`, `$lib` → `#lib`, `svelte.config.js` no longer supported, external redirects forbidden by default ([kit releases](https://github.com/sveltejs/kit/releases)). Paraglide's docs examples still use older syntax in places (`<slot>`), so expect some docs lag. Avoid `svelte-i18n` (last release 2024-10-21).

### Next.js 16 (+ React 19)

- **i18n:** next-intl provides `localePrefix` `'always' | 'as-needed' | 'never'` (`as-needed` = unprefixed default locale) and localized `pathnames` (e.g. `/de/über-uns` → internal `/[locale]/about`). Its middleware/Proxy adds **automatic `hreflang` alternate `Link` headers with `x-default`** ([routing configuration](https://next-intl.dev/docs/routing/configuration)). Messages use ICU syntax.
- **Static rendering:** without extra setup, next-intl reads the locale from a header and **forces dynamic rendering**. To stay static, use `next/root-params` (default in Next 16.3+) or the legacy `setRequestLocale` in every layout and page, plus `generateStaticParams` ([routing setup](https://next-intl.dev/docs/routing/setup)).
- **Maps:** `@vis.gl/react-maplibre` (MIT, peer `maplibre-gl >=4`). The Protomaps docs show the React `addProtocol`-once pattern in `useEffect` ([Protomaps](https://docs.protomaps.com/pmtiles/maplibre)).
- **Self-hosting:** officially documented. Single-instance `next start` works without extra config, with caveats for multi-instance, CDN, and streaming ([Self-hosting](https://nextjs.org/docs/app/guides/self-hosting)).
- **Maintenance:** very active, largest ecosystem and hiring pool. Governance is a single vendor (Vercel). The App Router/RSC/caching model is the steepest learning curve of the candidates, which matters for long-term community maintenance.
- **Alternatives within React:** React Router 8 (framework mode) or TanStack Start (`@tanstack/react-start` 1.168, peer Vite ≥ 7) are lighter SSR options. They have no first-party i18n routing, so they would pair with Paraglide, Lingui, or react-intl. They were not evaluated in depth.

### Astro 7 (islands)

- **i18n:** the built-in i18n is **routing only**: `prefixDefaultLocale` (default `false` → unprefixed default locale), `fallback` with redirect/rewrite, and `getRelativeLocaleUrl()` / `getAbsoluteLocaleUrlList()`. It does not translate UI strings, and it has no per-page translated slugs (only custom locale *prefixes*, which need `output: "server"` and no prerendered pages) ([Astro i18n](https://docs.astro.build/en/guides/internationalization/)). A message library such as Paraglide must be added.
- **Fit:** great for mostly-static, content-first pages with small interactive islands. TART's core flows are app-like: the map/list sync, multi-step Submission forms with upload, moderation diff views, and auth-gated areas. In Astro these become large framework islands (Svelte/React via `@astrojs/svelte` 9 / `@astrojs/react` 7), adding a second component model.
- **Maintenance/governance:** the Astro team joined Cloudflare (January 2026). Astro stays MIT with open governance and supports non-Cloudflare targets ([Astro blog](https://astro.build/blog/joining-cloudflare/)). `@astrojs/node` 11 provides self-hosted SSR.

### Vite SPA (React/Svelte/Vue, client-only)

- This is the simplest hosting option: static files served by the reverse proxy, with no Node runtime.
- **It fails the SEO requirement** for database-driven public pages unless something else renders HTML. Adding a separate prerender/SSR layer, or rendering public pages from FastAPI with Jinja, would split the UI into two stacks and two i18n systems. That conflicts with "a consistent internationalization mechanism" (README §14).
- It is reasonable only if SEO were dropped as a requirement, which the ticket does not allow.

### Nuxt 4 (Vue), not in the original list

- `@nuxtjs/i18n` 10 offers prefix strategies, custom route paths, and `useLocaleHead()` for `lang`, `hreflang` alternates (with catch-all), canonical, and `og:locale` ([SEO guide](https://i18n.nuxtjs.org/docs/guide/seo)). This is the most "batteries-included" SEO feature set seen.
- Governance: NuxtLabs joined Vercel in July 2025. Nuxt and Nitro remain MIT with open governance ([Vercel blog](https://vercel.com/blog/nuxtlabs-joins-vercel)).
- It is a credible equal to Next.js. It is not in the ticket's shortlist, so it is mentioned for completeness.

## Comparison against the ticket's criteria

| Criterion | SvelteKit + Paraglide | Next.js + next-intl | Astro + Paraglide | Vite SPA | Nuxt + @nuxtjs/i18n |
|---|---|---|---|---|---|
| FastAPI fit (OpenAPI client, separate API) | Good | Good | Good | Good | Good |
| MapLibre + PMTiles | Good (client component; `svelte-maplibre-gl` supports v6) | Good (`@vis.gl/react-maplibre`) | Good (island; needs `ssr.noExternal`) | Best (no SSR concerns) | Good (client-only component) |
| i18n: unprefixed `it` + `/en/` | Yes (URL strategy) | Yes (`as-needed`) | Yes (`prefixDefaultLocale: false`) | Client-side only | Yes (`prefix_except_default`) |
| Translated pathnames | Yes (`urlPatterns`) | Yes (`pathnames`) | No (prefix only) | n/a | Yes (custom paths) |
| `hreflang` / SEO helpers | Manual in layout | Automatic `Link` headers | Helpers for URLs, manual tags | No | `useLocaleHead()` |
| Locale-aware formatting | `Intl` via message formatters | ICU + `Intl` (use-intl) | via Paraglide | via lib | vue-i18n |
| SEO for DB-driven pages | SSR | SSR / static | SSR | **Fails** | SSR |
| Build-time a11y linting | Compiler `a11y_*` warnings | ESLint plugin (not built in) | Partial (depends on island framework) | Depends | ESLint plugin |
| Self-hosting on small VPS | `node build`, simple | `next start`, simple for single instance; more knobs | `@astrojs/node`, simple | Static, simplest | Nitro node server |
| Maintainability for volunteers | Small API surface; **Kit 3 just released** | Largest ecosystem; most complex model | Two component models for app-heavy UI | Simple, but SEO gap | Mid |
| Dependency licenses | MIT | MIT / BSD-3 | MIT | MIT | MIT |

## Dependency license compatibility

- All checked packages are **MIT**, **BSD-3-Clause** (`maplibre-gl`, `pmtiles`, `react-intl`), or **MIT OR Apache-2.0** (`svelte-maplibre-gl`). These are permissive. They allow use and redistribution inside a non-commercial, source-available product as long as copyright/license notices are preserved (e.g. in a `THIRD_PARTY_NOTICES` file or the bundle's license comments). No copyleft (GPL/AGPL) packages appeared among top-level candidates.
- Only top-level packages were checked (registry metadata). The **transitive** tree was not audited. Recommendation for the implementation phase: add an automated license check (e.g. a license-checker step in CI with an allow-list of MIT/BSD/ISC/Apache-2.0/0BSD) once a stack is chosen.
- **Data licenses differ from code licenses:** OSM-derived PMTiles basemaps are ODbL Produced Works and need visible OpenStreetMap attribution on the map. This is separate from the software license, consistent with the brief's §7 separation of software, data, and content.
- Per `CLAUDE.md`, nothing here implies TART itself is "Open Source". TART's own license remains for the Licensing Decision Record.

## Risks

1. **SvelteKit 3 is one week old** (3.0.0 on 2026-10-01). Ecosystem libraries (Paraglide docs, wrappers, examples) may lag. Mitigation: a prototype spike before the decision, and pinned versions.
2. **WebGL2 is now required by MapLibre v6.** Some old devices will see no map. The list/catalogue view must provide full functionality without the map (also a WCAG concern: a WebGL canvas is not a keyboard-accessible list of Artworks).
3. **Map accessibility is framework-independent.** The MapLibre docs page does not cover accessibility. Keyboard-operable markers, non-color condition/uncertainty encoding, and a list alternative must be designed in the map experience ticket.
4. **Vendor governance:** Next.js and Nuxt are Vercel-backed, Astro is Cloudflare-owned, and several Svelte core maintainers, including its creator, are employed by Vercel. All are MIT and self-hostable today. No option is vendor-neutral, so prefer the one whose self-hosted path is simplest.
5. **`@hey-api/openapi-ts` is pre-1.0.** Its generated client API may change between minor versions. Pin it, or use `openapi-typescript` for types only.
6. **Paraglide message file format:** the inlang JSON format was confirmed. Compatibility with external translation tools (ICU/PO/XLIFF) was not confirmed in the docs read. This matters if community translators use a tool like Weblate. (next-intl's dependency list includes PO/JSON formatters, which suggests PO support there, but this was not verified in docs.)

## New questions surfaced (candidate tickets)

- **Auth/session boundary between the SSR frontend and FastAPI:** who owns the session cookie, CSRF, and how server-side `load` calls authenticate to FastAPI on the internal network.
- **Translator workflow:** which file format and tool community translators will use (Weblate, Crowdin, plain PRs), which constrains the i18n library's message format.
- **Map fallback without WebGL2**, and the accessible non-map browsing path (overlaps the map experience ticket).
- **Reverse proxy choice (Caddy vs nginx)** for Range/CORS on PMTiles, HTTPS, streaming, and upload size limits.
- **Memory budget per container** on the target VPS. This needs a measurement spike (Node SSR + FastAPI + PostGIS + proxy).

## Sources

- npm registry metadata, retrieved 2026-10-08: `https://registry.npmjs.org/<package>`
- SvelteKit releases: https://github.com/sveltejs/kit/releases
- SvelteKit adapter-node: https://svelte.dev/docs/kit/adapter-node
- Svelte CLI paraglide add-on: https://svelte.dev/docs/cli/paraglide
- Svelte compiler warnings: https://svelte.dev/docs/svelte/compiler-warnings
- Paraglide JS + SvelteKit: https://paraglidejs.com/sveltekit
- Paraglide i18n routing: https://paraglidejs.com/i18n-routing
- Paraglide variants: https://paraglidejs.com/variants
- Paraglide formatting: https://paraglidejs.com/formatting
- next-intl routing configuration: https://next-intl.dev/docs/routing/configuration
- next-intl routing setup (static rendering): https://next-intl.dev/docs/routing/setup
- Next.js self-hosting (v16.4.0): https://nextjs.org/docs/app/guides/self-hosting
- Astro i18n routing: https://docs.astro.build/en/guides/internationalization/
- Astro joins Cloudflare: https://astro.build/blog/joining-cloudflare/
- NuxtLabs joins Vercel: https://vercel.com/blog/nuxtlabs-joins-vercel
- @nuxtjs/i18n SEO: https://i18n.nuxtjs.org/docs/guide/seo
- MapLibre GL JS docs: https://maplibre.org/maplibre-gl-js/docs/
- MapLibre GL JS changelog: https://github.com/maplibre/maplibre-gl-js/blob/main/CHANGELOG.md
- Protomaps PMTiles for MapLibre: https://docs.protomaps.com/pmtiles/maplibre
- Protomaps cloud storage (Range/CORS): https://docs.protomaps.com/pmtiles/cloud-storage
- Protomaps basemap downloads/license: https://docs.protomaps.com/basemaps/downloads
- svelte-maplibre-gl: https://github.com/MIERUNE/svelte-maplibre-gl
- FastAPI generating SDKs: https://fastapi.tiangolo.com/advanced/generate-clients/
