import type { DocumentationItemView } from '#lib/archive/records.ts';
import { loadRecord, vocabularies } from '#lib/server/records.ts';
import type { PageServerLoad } from './$types';

/** The Documentation item page: a minimal permalink, for citation (archive-records spec). */
export const load: PageServerLoad = async (event) => ({
	item: await loadRecord<DocumentationItemView>(event, 'documentation_item'),
	...vocabularies(event)
});
