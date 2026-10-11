import type { createApiClient } from '../api/client';
import type { components } from '../api/schema';

/** The public subset of the Instance configuration, from `GET /api/config` (ADR 0009). */
export type PublicConfiguration = components['schemas']['PublicConfiguration'];

type ApiClient = ReturnType<typeof createApiClient>;

/** How long a read configuration is reused before the API is asked again. */
export const CACHE_MILLISECONDS = 60_000;

/**
 * Returns a function that reads the public configuration from the API and caches it.
 *
 * The frontend never reads the configuration directory. The API loads it only at
 * startup, so the cache only has to outlive a request, and expires so that a
 * restarted `api` with a changed configuration is picked up within a minute.
 */
export function createInstanceConfigReader(
	client: ApiClient,
	now: () => number = Date.now
): () => Promise<PublicConfiguration> {
	let cached: { value: Promise<PublicConfiguration>; until: number } | undefined;

	return () => {
		if (cached !== undefined && now() < cached.until) return cached.value;
		const value = client.GET('/api/config').then(({ data, response }) => {
			if (data === undefined) {
				throw new Error(`GET /api/config answered ${response.status}`);
			}
			return data;
		});
		// A failed read is not cached: the next call asks again.
		value.catch(() => {
			if (cached?.value === value) cached = undefined;
		});
		cached = { value, until: now() + CACHE_MILLISECONDS };
		return value;
	};
}
