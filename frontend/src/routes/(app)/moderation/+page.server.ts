import { error } from '@sveltejs/kit';
import type { IndexPage } from '#lib/archive/records.ts';
import { KINDS, LABELS, SORTS } from '#lib/moderation/words.ts';
import { api, onBehalfOf } from '#lib/server/api.ts';
import { signInAgain } from '#lib/server/contribution.ts';
import { fetchView } from '#lib/server/records.ts';
import type { PageServerLoad } from './$types';

/**
 * The Moderation queue (Contribution and moderation spec, Queue): the Submissions awaiting
 * a decision, oldest first unless the order says otherwise, narrowed by the filters of the
 * query string. The Moderation layout has already turned away anonymous users and
 * non-Moderators; the API checks the role again on every request.
 */

const MAX_PAGES = 20;

/** Every Area, by name, for the Area filter. */
async function areasOf(event: Parameters<PageServerLoad>[0]) {
	const found: { id: number; name: string }[] = [];
	for (let page = 1; page <= MAX_PAGES; page++) {
		const { data } = await fetchView<IndexPage>(event, `/api/archive/areas?page=${page}`);
		if (!data) break;
		found.push(...data.items.map((each) => ({ id: each.id, name: each.name ?? String(each.id) })));
		if (found.length >= data.total || data.items.length === 0) break;
	}
	return found;
}

function number(raw: string | null): number | undefined {
	return raw !== null && /^\d{1,12}$/.test(raw) ? Number(raw) : undefined;
}

export const load: PageServerLoad = async (event) => {
	const query = event.url.searchParams;
	const sort = SORTS.find((each) => each === query.get('sort')) ?? SORTS[0];
	const label = LABELS.find((each) => each === query.get('label'));
	const kind = KINDS.find((each) => each === query.get('kind'));
	const submitter = number(query.get('submitter'));
	const area = number(query.get('area'));
	const outdated = { yes: true, no: false }[query.get('outdated') ?? ''];

	const [found, areas] = await Promise.all([
		api().GET('/api/moderation/queue', {
			params: { query: { sort, label, target_kind: kind, submitter, area, outdated } },
			headers: onBehalfOf(event)
		}),
		areasOf(event)
	]);
	if (found.response.status === 401) signInAgain(event);
	if (found.response.status === 403) error(403, { message: 'Forbidden', reason: 'moderator_only' });
	if (!found.data) throw new Error(`moderation queue: ${found.response.status}`);
	return {
		items: found.data.items,
		areas,
		filters: {
			sort,
			label: label ?? '',
			kind: kind ?? '',
			submitter: submitter === undefined ? '' : String(submitter),
			area: area === undefined ? '' : String(area),
			outdated:
				query.get('outdated') === 'yes' || query.get('outdated') === 'no'
					? (query.get('outdated') as string)
					: ''
		}
	};
};
