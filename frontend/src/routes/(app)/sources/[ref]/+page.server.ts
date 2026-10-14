import type { SourceView } from '#lib/archive/records.ts';
import { loadRecord, vocabularies } from '#lib/server/records.ts';
import type { PageServerLoad } from './$types';

/** The Source page (archive-records spec, Other record pages). */
export const load: PageServerLoad = async (event) => ({
	source: await loadRecord<SourceView>(event, 'source'),
	...vocabularies(event)
});
