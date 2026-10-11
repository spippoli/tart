/**
 * Locale-aware formatting (ADR 0008): `Intl` with the UI language and, for dates,
 * the Instance's explicit time zone, never the server's or the browser's.
 * Uncertain dates have their own module, `$lib/archive/uncertain-date`.
 */

export interface FormatContext {
	/** The UI language. */
	locale: string;
	/** The Instance time zone (IANA name), `geography.time_zone`. */
	timeZone: string;
}

export function formatNumber(value: number, { locale }: Pick<FormatContext, 'locale'>): string {
	return new Intl.NumberFormat(locale).format(value);
}

/** A date and time, as in a Revision or a Submission round. */
export function formatDateTime(
	instant: Date | string,
	{ locale, timeZone }: FormatContext
): string {
	return new Intl.DateTimeFormat(locale, {
		dateStyle: 'long',
		timeStyle: 'short',
		timeZone
	}).format(new Date(instant));
}

/** A language's name in the UI language, for any tag (not only UI languages). */
export function languageName(tag: string, { locale }: Pick<FormatContext, 'locale'>): string {
	return new Intl.DisplayNames(locale, { type: 'language' }).of(tag) ?? tag;
}

/** A list in the UI language: "italiano e inglese", "Italian and English". */
export function formatList(items: string[], { locale }: Pick<FormatContext, 'locale'>): string {
	return new Intl.ListFormat(locale, { type: 'conjunction' }).format(items);
}
