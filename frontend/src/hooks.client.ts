import { baseLocale, isLocale, overwriteGetLocale } from '#lib/paraglide/runtime.js';

// The server chose the UI language of this page and wrote it into <html lang>;
// a change of language is a full page load (the language switcher).
overwriteGetLocale(() => {
	const language = document.documentElement.lang;
	return isLocale(language) ? language : baseLocale;
});
