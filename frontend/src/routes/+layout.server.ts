import type { LayoutServerLoad } from './$types';

/** What the shell needs on every page, error pages included. */
export const load: LayoutServerLoad = ({ locals }) => {
	const { config, locale, user } = locals;
	return {
		locale,
		enabledLanguages: config.languages.ui,
		contentLanguage: config.languages.content,
		timeZone: config.geography.time_zone,
		identity: config.identity,
		dataLicence: config.licenses.data,
		user: user && { displayName: user.display_name, moderator: user.moderator }
	};
};
