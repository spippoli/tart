import { error, redirect } from '@sveltejs/kit';
import { signInHref } from '#lib/auth/next.ts';
import type { PageServerLoad } from './$types';

/**
 * The Moderation area (Foundations spec, access rules): an anonymous user goes to
 * sign-in and comes back; a signed-in User without the Moderator role gets an
 * explanatory 403. The role is read afresh on every request. The Contribution and
 * moderation spec fills the page.
 */
export const load: PageServerLoad = ({ locals, url }) => {
	if (!locals.user) redirect(303, signInHref(url));
	if (!locals.user.moderator) error(403, { message: 'Forbidden', reason: 'moderator_only' });
};
