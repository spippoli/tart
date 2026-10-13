import type { IndexPage } from '#lib/archive/records.ts';
import { loadIndex, vocabularies } from '#lib/server/records.ts';
import type { PageServerLoad } from './$types';

/** An index, by name (archive-records spec, Indexes). */
export const load: PageServerLoad = async (event) => ({
	index: await loadIndex<IndexPage>(event, 'artist'),
	...vocabularies(event)
});
