import { loadDiscovery } from '#lib/server/discovery.ts';
import { mapSettings } from '#lib/server/map-settings.ts';
import type { PageServerLoad } from './$types';

// The homepage of a UI language is its bare prefix with a slash: `/it/`, `/en/`.
export const trailingSlash = 'always';

/** What the Explore map needs from the public configuration. */
export const load: PageServerLoad = async (event) => ({
	...(await loadDiscovery(event, 'explore')),
	...mapSettings(event.locals)
});
