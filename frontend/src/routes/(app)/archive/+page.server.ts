import { loadDiscovery } from '#lib/server/discovery.ts';
import type { PageServerLoad } from './$types';

/** The Archive view (Discovery spec, Explore and Archive views): all matching Artworks, by page. */
export const load: PageServerLoad = (event) => loadDiscovery(event, 'archive');
