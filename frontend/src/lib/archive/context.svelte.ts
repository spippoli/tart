import { page } from '$app/state';
import { getLocale } from '#lib/paraglide/runtime.js';
import { vocabularyLabels } from './records';

/**
 * What a record page formats with: the UI language, the Instance time zone, the
 * Content language, and the labels of the open vocabularies (from the page's data).
 */
export function archiveContext() {
	const locale = getLocale();
	const data = page.data as {
		timeZone: string;
		contentLanguage: string;
		expressionTypes?: { key: string; label: Record<string, string> }[];
		surfaceTypes?: { key: string; label: Record<string, string> }[];
	};
	return {
		locale,
		timeZone: data.timeZone,
		dates: { locale, timeZone: data.timeZone },
		contentLanguage: data.contentLanguage,
		expressionType: vocabularyLabels(data.expressionTypes ?? [], locale),
		surfaceType: vocabularyLabels(data.surfaceTypes ?? [], locale),
		separator: ', '
	};
}
