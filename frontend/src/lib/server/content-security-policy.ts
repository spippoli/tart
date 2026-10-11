import type { Handle } from '@sveltejs/kit/hooks';
import type { PublicConfiguration } from './instance-config';

/**
 * The Content-Security-Policy of the frontend's responses.
 *
 * Pages fetch only from their own origin, plus the origins of the external `https`
 * tile sources of the Instance's map styles, which the API lists in the public
 * configuration (Discovery spec, Basemap tiles: External tiles). MapLibre loads
 * tiles, glyphs, and sprites with `fetch`, so `connect-src` is the directive that
 * governs them.
 */
export function contentSecurityPolicy(tileOrigins: readonly string[]): string {
	return ['connect-src', "'self'", ...tileOrigins].join(' ');
}

/**
 * A server hook that sets the policy on every response. When the configuration
 * cannot be read, the policy allows only the page's own origin.
 */
export function createContentSecurityPolicyHandle(
	readConfig: () => Promise<Pick<PublicConfiguration, 'map_tile_origins'>>
): Handle {
	return async ({ event, resolve }) => {
		const [tileOrigins, response] = await Promise.all([
			readConfig().then(
				(config) => config.map_tile_origins,
				() => []
			),
			resolve(event)
		]);
		response.headers.set('Content-Security-Policy', contentSecurityPolicy(tileOrigins));
		return response;
	};
}
