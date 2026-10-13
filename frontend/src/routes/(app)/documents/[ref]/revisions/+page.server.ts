import type { RevisionsView } from '#lib/archive/records.ts';
import { loadRevisions, vocabularies } from '#lib/server/records.ts';
import type { PageServerLoad } from './$types';

/** The `/revisions` subpage (archive-records spec, Public record pages). */
export const load: PageServerLoad = async (event) => ({
	view: await loadRevisions<RevisionsView>(event, 'documentation_item'),
	...vocabularies(event)
});
