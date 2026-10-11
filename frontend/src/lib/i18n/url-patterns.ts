/**
 * Translated pathnames of the UI languages (ADR 0008, ADR 0010).
 *
 * Every UI language is URL-prefixed, and path segments are UI strings: each page
 * has one path per platform UI language. SvelteKit routes are the de-localized
 * (English, unprefixed) paths; `reroute` maps `/it/informazioni` to `/about`, and
 * `localizeHref` maps back. Paraglide reads this table at build time, so it lists
 * every platform UI language; an Instance enables a subset at runtime.
 *
 * Pages owned by later specs add their rows here.
 */

type PlatformLanguage = 'it' | 'en';

/** De-localized path → its path, without the language prefix, per UI language. */
const pages: Record<string, Record<PlatformLanguage, string>> = {
	'/archive': { it: '/archivio', en: '/archive' },
	'/artists': { it: '/artisti', en: '/artists' },
	'/contribute': { it: '/contribuisci', en: '/contribute' },
	'/sign-in': { it: '/accedi', en: '/sign-in' },
	'/account': { it: '/account', en: '/account' },
	'/moderation': { it: '/moderazione', en: '/moderation' },
	'/about': { it: '/informazioni', en: '/about' },
	'/about/guidelines': { it: '/informazioni/linee-guida', en: '/about/guidelines' },
	'/about/contribution-policy': {
		it: '/informazioni/policy-contributi',
		en: '/about/contribution-policy'
	},
	'/about/terms': { it: '/informazioni/termini', en: '/about/terms' },
	'/about/privacy': { it: '/informazioni/privacy', en: '/about/privacy' },
	'/about/contact': { it: '/informazioni/contatti', en: '/about/contact' },
	'/about/data-licence': { it: '/informazioni/licenza-dati', en: '/about/data-licence' },
	'/about/tart': { it: '/informazioni/tart', en: '/about/tart' }
};

const languages: PlatformLanguage[] = ['it', 'en'];

export interface UrlPattern {
	pattern: string;
	localized: [PlatformLanguage, string][];
}

/** Specific pages first; the catch-all only adds the prefix to everything else. */
export const urlPatterns: UrlPattern[] = [
	...Object.entries(pages).map(([pattern, paths]) => ({
		pattern,
		localized: languages.map((language): [PlatformLanguage, string] => [
			language,
			`/${language}${paths[language]}`
		])
	})),
	{
		pattern: '/:path(.*)?',
		localized: languages.map((language): [PlatformLanguage, string] => [
			language,
			`/${language}/:path(.*)?`
		])
	}
];
