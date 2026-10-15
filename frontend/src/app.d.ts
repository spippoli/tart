// See https://svelte.dev/docs/kit/types#app.d.ts
// for information about these interfaces
import type { PublicConfiguration } from '#lib/server/instance-config.ts';
import type { Locale } from '#lib/paraglide/runtime.js';
import type { components } from './lib/api/schema';

declare global {
	/** Replaced at build time by Vite `define`; read it through `$lib/version`. */
	const __TART_VERSION__: string;

	namespace App {
		interface Error {
			message: string;
			/** Why access was refused, for an explanatory error page. */
			reason?: 'moderator_only';
		}
		interface Locals {
			/** The signed-in User, or null; read from the API on every request. */
			user: components['schemas']['SignedInUser'] | null;
			/** The public Instance configuration, read from the API. */
			config: PublicConfiguration;
			/** The UI language of the page: its prefix, or the Instance default. */
			locale: Locale;
			/** False when the URL has no prefix of an enabled UI language: the page answers 404. */
			languageEnabled: boolean;
		}
		// interface PageData {}
		interface PageState {
			/** Explore: the selection was opened in this session, so closing it goes back. */
			opened?: boolean;
		}
		// interface Platform {}
	}
}

export {};
