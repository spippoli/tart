import { error } from '@sveltejs/kit';
import type { LayoutServerLoad } from './$types';

/**
 * Every page lives under the prefix of an enabled UI language (ADR 0008). The
 * error is thrown below the root layout so that the 404 page keeps the shell.
 */
export const load: LayoutServerLoad = ({ locals }) => {
	if (!locals.languageEnabled) error(404);
};
