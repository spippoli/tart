import { error, redirect } from '@sveltejs/kit';
import { signInHref } from '#lib/auth/next.ts';
import type { LayoutServerLoad } from './$types';

/**
 * The Moderation area (Foundations spec, access rules): an anonymous user goes to
 * sign-in and comes back; a signed-in User without the Moderator role gets an
 * explanatory 403. The role is read afresh on every request. The sub-navigation
 * lists only the pages that exist; the Invitations entry appears only under
 * `registration = invite` (Contribution and moderation spec, Invitations).
 */
export const load: LayoutServerLoad = ({ locals, url }) => {
	if (!locals.user) redirect(303, signInHref(url));
	if (!locals.user.moderator) error(403, { message: 'Forbidden', reason: 'moderator_only' });
	return { invitationsEnabled: locals.config.registration === 'invite' };
};
