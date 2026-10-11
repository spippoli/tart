/**
 * UI language selection (ADR 0008).
 *
 * The platform ships its UI languages complete; an Instance enables a subset in
 * `languages.ui`, whose first entry is its default. Only the root `/` chooses a
 * language for the visitor; every other URL names its own.
 */

/** The cookie the language switcher sets, read only by the root redirect. */
export const LANGUAGE_COOKIE = 'ui_language';
export const LANGUAGE_COOKIE_MAX_AGE_SECONDS = 365 * 24 * 60 * 60;

interface Preferences {
	/** The language cookie, if any. */
	cookie: string | undefined;
	/** The `Accept-Language` request header, if any. */
	acceptLanguage: string | null;
	/** The Instance's enabled UI languages, default first. */
	enabled: readonly string[];
}

/** The `Accept-Language` ranges by descending quality, ignoring `q=0`. */
function acceptedRanges(header: string): string[] {
	return header
		.split(',')
		.map((part, index) => {
			const [range, ...parameters] = part.trim().split(';');
			const q = parameters
				.map((parameter) => parameter.trim())
				.find((parameter) => parameter.startsWith('q='));
			const quality = q === undefined ? 1 : Number(q.slice(2));
			return { range: range.trim().toLowerCase(), quality, index };
		})
		.filter(({ range, quality }) => range !== '' && quality > 0 && !Number.isNaN(quality))
		.sort((a, b) => b.quality - a.quality || a.index - b.index)
		.map(({ range }) => range);
}

function primarySubtag(tag: string): string {
	return tag.split('-')[0];
}

/** The root redirect's choice: the cookie, then `Accept-Language`, then the default. */
export function chooseLanguage({ cookie, acceptLanguage, enabled }: Preferences): string {
	if (cookie !== undefined && enabled.includes(cookie)) return cookie;
	for (const range of acceptedRanges(acceptLanguage ?? '')) {
		if (range === '*') break;
		const match =
			enabled.find((language) => language.toLowerCase() === range) ??
			enabled.find((language) => primarySubtag(language.toLowerCase()) === primarySubtag(range));
		if (match !== undefined) return match;
	}
	return enabled[0];
}

/** The writing direction of a language tag, for `dir` next to `lang`. */
export function textDirection(tag: string): 'ltr' | 'rtl' {
	const locale = new Intl.Locale(tag) as Intl.Locale & {
		getTextInfo?: () => { direction?: string };
		textInfo?: { direction?: string };
	};
	const direction = locale.getTextInfo?.().direction ?? locale.textInfo?.direction;
	return direction === 'rtl' ? 'rtl' : 'ltr';
}
