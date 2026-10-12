export type Theme = 'light' | 'dark';

/** The colours the archive layers and the legend read from a served style. */
export interface Tokens {
	'map.paper': string;
	'map.ink': string;
	'marker.ink': string;
	'map.label.district': string;
	/** The Instance accent of this theme, which the API adds. */
	'marker.accent': string;
}

/** Why a map cannot be shown: no WebGL2, a style that fails to load, or no tile extract. */
export type Unavailable = 'webgl2' | 'style' | 'tiles_missing';

/** A served style: a MapLibre style document with TART's metadata. */
export interface Style {
	version: number;
	metadata: { 'tart:tokens': Tokens; 'tart:insert-archive-below': string } & Record<
		string,
		unknown
	>;
	[key: string]: unknown;
}

export type StyleResult = { style: Style } | { unavailable: Exclude<Unavailable, 'webgl2'> };

/** The style endpoint of a theme (Discovery spec, Map style ownership and serving). */
export function styleUrl(theme: Theme): string {
	return `/api/map/style/${theme}.json`;
}

/**
 * Fetches the style of `theme`. The endpoint answers `503 tiles_missing` when the
 * style uses the local basemap and there is no extract; any other failure, or a
 * document without TART's metadata, is a style that fails to load.
 */
export async function fetchStyle(
	theme: Theme,
	fetcher: typeof fetch = fetch
): Promise<StyleResult> {
	let response: Response;
	try {
		response = await fetcher(styleUrl(theme), { headers: { accept: 'application/json' } });
	} catch {
		return { unavailable: 'style' };
	}
	const body: unknown = await response.json().catch(() => undefined);
	if (
		response.status === 503 &&
		(body as { code?: unknown } | undefined)?.code === 'tiles_missing'
	) {
		return { unavailable: 'tiles_missing' };
	}
	if (!response.ok || !isStyle(body)) return { unavailable: 'style' };
	return { style: body };
}

function isStyle(body: unknown): body is Style {
	const tokens = (body as Style | undefined)?.metadata?.['tart:tokens'];
	return typeof tokens === 'object' && tokens !== null;
}

/** The UI theme, which follows `prefers-color-scheme` only (Foundations spec). */
export const DARK_SCHEME = '(prefers-color-scheme: dark)';
