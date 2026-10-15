import type { ArtworkView } from '#lib/archive/records.ts';
import { mapSettings } from '#lib/server/map-settings.ts';
import { loadRecord, vocabularies } from '#lib/server/records.ts';
import type { PageServerLoad } from './$types';

/** The Artwork page (archive-records spec, Public record pages). */
export const load: PageServerLoad = async (event) => ({
	artwork: await loadRecord<ArtworkView>(event, 'artwork'),
	...vocabularies(event),
	...mapSettings(event.locals)
});
