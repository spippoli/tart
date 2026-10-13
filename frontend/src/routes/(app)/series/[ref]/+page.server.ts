import type { PlaceView } from '#lib/archive/records.ts';
import { loadRecord, vocabularies } from '#lib/server/records.ts';
import type { PageServerLoad } from './$types';

/** A Series page (archive-records spec, Other record pages). */
export const load: PageServerLoad = async (event) => ({
	place: await loadRecord<PlaceView>(event, 'series'),
	...vocabularies(event)
});
