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
	'/moderation/invitations': { it: '/moderazione/inviti', en: '/moderation/invitations' },
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

/**
 * Record routes (archive-records spec, Public record pages): the kind's segment, then
 * the record's `{id}-{slug}` (or bare id), then its `/revisions` subpage. The indexes
 * of Artists, Sites, Areas, and Series are the bare segment.
 */
const records: Record<string, Record<PlatformLanguage, string>> = {
	'/artworks': { it: '/opere', en: '/artworks' },
	'/artists': { it: '/artisti', en: '/artists' },
	'/locations': { it: '/superfici', en: '/locations' },
	'/sites': { it: '/luoghi', en: '/sites' },
	'/areas': { it: '/aree', en: '/areas' },
	'/series': { it: '/serie', en: '/series' },
	'/sources': { it: '/fonti', en: '/sources' },
	'/documents': { it: '/documenti', en: '/documents' }
};

/** The report form of Rights and legal actions, which every record page links to. */
pages['/report'] = { it: '/segnala', en: '/report' };

const revisions: Record<PlatformLanguage, string> = { it: 'revisioni', en: 'revisions' };

for (const [route, paths] of Object.entries(records)) {
	const each = (suffix: (language: PlatformLanguage) => string) =>
		Object.fromEntries(
			Object.entries(paths).map(([language, path]) => [
				language,
				path + suffix(language as PlatformLanguage)
			])
		) as Record<PlatformLanguage, string>;
	pages[`${route}/:ref/revisions`] = each((language) => `/:ref/${revisions[language]}`);
	pages[`${route}/:ref`] = each(() => '/:ref');
	pages[route] = paths;
}

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
