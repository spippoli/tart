import type { Reroute } from '@sveltejs/kit/hooks';
import { deLocalizeUrl } from '#lib/paraglide/runtime.js';

/** `/it/informazioni` renders the `/about` route (see `$lib/i18n/url-patterns`). */
export const reroute: Reroute = ({ url }) => deLocalizeUrl(url).pathname;
