import type { ArtistView } from '#lib/archive/records.ts';
import { loadRecord, vocabularies } from '#lib/server/records.ts';
import type { PageServerLoad } from './$types';

/** The Artist page (archive-records spec, Other record pages). */
export const load: PageServerLoad = async (event) => ({
	artist: await loadRecord<ArtistView>(event, 'artist'),
	...vocabularies(event)
});
