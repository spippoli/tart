import { redirect } from '@sveltejs/kit';
import { signInHref } from '#lib/auth/next.ts';
import { STATUSES, type Status } from '#lib/contribution/words.ts';
import { api, onBehalfOf } from '#lib/server/api.ts';
import { signInAgain } from '#lib/server/contribution.ts';
import type { PageServerLoad } from './$types';

/**
 * My contributions (Contribution and moderation spec, Contribute hub and My contributions):
 * the User's Submissions, drafts included, filterable by status with `?status=`. An
 * anonymous user goes to sign-in and comes back.
 */
export const load: PageServerLoad = async (event) => {
	if (!event.locals.user) redirect(303, signInHref(event.url));
	const asked = event.url.searchParams.get('status');
	const status = STATUSES.find((each) => each === asked) as Status | undefined;
	const { data, response } = await api().GET('/api/contributions', {
		params: { query: { status } },
		headers: onBehalfOf(event)
	});
	if (response.status === 401) signInAgain(event);
	if (!data) throw new Error(`contributions: ${response.status}`);
	return { submissions: data.items, status: status ?? null };
};
