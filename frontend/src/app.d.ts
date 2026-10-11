// See https://svelte.dev/docs/kit/types#app.d.ts
// for information about these interfaces
import type { PublicConfiguration } from '#lib/server/instance-config.ts';
import type { Locale } from '#lib/paraglide/runtime.js';

declare global {
	/** Replaced at build time by Vite `define`; read it through `$lib/version`. */
	const __TART_VERSION__: string;

	namespace App {
		// interface Error {}
		interface Locals {
			/** The public Instance configuration, read from the API. */
			config: PublicConfiguration;
			/** The UI language of the page: its prefix, or the Instance default. */
			locale: Locale;
			/** False when the URL has no prefix of an enabled UI language: the page answers 404. */
			languageEnabled: boolean;
		}
		// interface PageData {}
		// interface PageState {}
		// interface Platform {}
	}
}

export {};
