import type { LocationView } from '#lib/archive/records.ts';
import { loadRecord, vocabularies } from '#lib/server/records.ts';
import type { PageServerLoad } from './$types';

/** The Location page (archive-records spec, Other record pages). */
export const load: PageServerLoad = async (event) => ({
	location: await loadRecord<LocationView>(event, 'location'),
	...vocabularies(event)
});
