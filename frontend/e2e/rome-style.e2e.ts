import type { Route } from '@playwright/test';
import { expect, test } from './test';
import { readFileSync } from 'node:fs';
import { signShapes, SMALL_SIGN_SIZE, type SignKind } from '../src/lib/map/signs';
import type { Tokens } from '../src/lib/map/style';
import { serveLocations } from './map-style';

/**
 * Rome's reference style (Discovery spec, Cartography; ADR 0017).
 *
 * Criterion 62: at 12 px, at 1x pixel density, in greyscale, in both themes, the
 * present, unknown, and disappeared signs are told apart, over every fill of the
 * style. Each sign is drawn as the legend draws it (`Sign.svelte`), from the style's
 * tokens and the Instance accent, which the API adds when it serves the style.
 *
 * The `font-faces` path: the pinned MapLibre draws the style's labels from its Goudy
 * font files, on the Explore page and under its Content-Security-Policy.
 */

const ROME = new URL('../../instances/rome/', import.meta.url);
const KINDS: SignKind[] = ['present', 'unknown', 'disappeared'];
const FILLS = ['map.paper', 'map.block', 'map.park', 'map.water'];

/** Two signs are told apart when this share of their pixels differ in greyscale... */
const MIN_DIFFERENT_SHARE = 0.15;
/** ...each by at least this much luminance, out of 1. */
const MIN_LUMINANCE_STEP = 0.25;

const romeStyle = (theme: 'light' | 'dark') =>
	JSON.parse(readFileSync(new URL(`map/style.${theme}.json`, ROME), 'utf8'));

function tokens(theme: 'light' | 'dark'): Tokens {
	const style = romeStyle(theme);
	const accent = /^accent = \{ light = "(#\w{6})", dark = "(#\w{6})" \}$/m.exec(
		readFileSync(new URL('instance.toml', ROME), 'utf8')
	);
	if (!accent) throw new Error('instance.toml has no accent');
	return {
		...style.metadata['tart:tokens'],
		'marker.accent': accent[theme === 'light' ? 1 : 2]
	};
}

function svg(kind: SignKind, colours: Tokens, size: number): string {
	const paths = signShapes(kind, colours, size).map(
		(shape) =>
			`<path d="${shape.d}" fill="${shape.fill ?? 'none'}" stroke="${shape.stroke ?? 'none'}"` +
			` stroke-width="${shape.strokeWidth ?? 0}" stroke-dasharray="${shape.dash?.join(' ') ?? 'none'}"` +
			` stroke-linecap="${shape.dash || !shape.fill ? 'round' : 'butt'}"/>`
	);
	return `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">${paths.join('')}</svg>`;
}

test.use({ deviceScaleFactor: 1 });

for (const theme of ['light', 'dark'] as const) {
	test(`the three signs are told apart at 12 px in greyscale, ${theme} theme (criterion 62)`, async ({
		page
	}) => {
		const colours = tokens(theme);
		const size = SMALL_SIGN_SIZE;
		expect(size).toBe(12);
		const cells = FILLS.flatMap((fill) =>
			KINDS.map(
				(kind) =>
					`<div data-fill="${fill}" data-kind="${kind}" style="background:${colours[fill as keyof Tokens]}">` +
					svg(kind, colours, size) +
					'</div>'
			)
		);
		await page.setContent(
			`<style>body{margin:0;display:flex;flex-wrap:wrap;filter:grayscale(1)}` +
				`div{width:${size}px;height:${size}px;line-height:0}</style>${cells.join('')}`
		);

		for (const fill of FILLS) {
			const grey: Record<string, number[]> = {};
			for (const kind of KINDS) {
				const shot = await page.locator(`[data-fill="${fill}"][data-kind="${kind}"]`).screenshot();
				grey[kind] = await page.evaluate(async (png) => {
					const image = await createImageBitmap(
						await (await fetch(`data:image/png;base64,${png}`)).blob()
					);
					const canvas = new OffscreenCanvas(image.width, image.height);
					const context = canvas.getContext('2d')!;
					context.drawImage(image, 0, 0);
					const { data } = context.getImageData(0, 0, image.width, image.height);
					const values = [];
					for (let i = 0; i < data.length; i += 4) values.push(data[i] / 255);
					return values;
				}, shot.toString('base64'));
			}
			for (const [a, b] of [
				['present', 'unknown'],
				['present', 'disappeared'],
				['unknown', 'disappeared']
			]) {
				const different = grey[a].filter(
					(value, i) => Math.abs(value - grey[b][i]) >= MIN_LUMINANCE_STEP
				).length;
				expect(
					different / grey[a].length,
					`${a} and ${b} on ${fill}: share of pixels that differ in greyscale`
				).toBeGreaterThanOrEqual(MIN_DIFFERENT_SHARE);
			}
		}
	});
}

/**
 * Rome's style as the API serves it, cut down to what needs no tiles: the background
 * and the overlay layers, the overlay replaced by one fictional ruin at the default
 * view, its label shown at every zoom.
 */
function servedWithoutTiles(theme: 'light' | 'dark', origin: string) {
	const style = romeStyle(theme);
	const keep = ['background', 'overlay-ruins', 'overlay-walls', 'overlay-ruin-labels'];
	const [lon, lat] = [12.4823, 41.8955];
	return {
		...style,
		glyphs: origin + style.glyphs,
		'font-faces': Object.fromEntries(
			Object.entries(style['font-faces'] as Record<string, string>).map(([name, url]) => [
				name,
				origin + url
			])
		),
		metadata: {
			...style.metadata,
			'tart:insert-archive-below': 'overlay-ruin-labels',
			'tart:tokens': tokens(theme)
		},
		sources: {
			overlay: {
				type: 'geojson',
				data: {
					type: 'Feature',
					properties: { kind: 'ruin', name: 'Rovina di prova (fittizia)' },
					geometry: {
						type: 'Polygon',
						coordinates: [
							[
								[lon - 0.004, lat - 0.003],
								[lon + 0.004, lat - 0.003],
								[lon + 0.004, lat + 0.003],
								[lon - 0.004, lat + 0.003],
								[lon - 0.004, lat - 0.003]
							]
						]
					}
				}
			}
		},
		layers: style.layers
			.filter((layer: { id: string }) => keep.includes(layer.id))
			.map((layer: { minzoom?: number }) => ({ ...layer, minzoom: 0 }))
	};
}

test("the map draws its labels from the style's font files", async ({ page, baseURL }) => {
	const problems: string[] = [];
	page.on('console', (message) => {
		// The software renderer's own performance notes are not the map's problems.
		if (message.text().startsWith('[.WebGL-')) return;
		if (message.type() === 'error' || message.type() === 'warning') problems.push(message.text());
	});
	page.on('pageerror', (error) => problems.push(error.message));
	await serveLocations(page);
	await page.route('**/api/map/style/*.json', (route: Route) =>
		route.fulfill({
			contentType: 'application/json',
			body: JSON.stringify(
				servedWithoutTiles(
					route.request().url().endsWith('/dark.json') ? 'dark' : 'light',
					new URL(baseURL!).origin
				)
			)
		})
	);
	// The cluster counts are drawn in Noto Sans, from the glyphs the Instance ships.
	await page.route('**/map/glyphs/**', (route: Route) => {
		const { pathname } = new URL(route.request().url());
		return route.fulfill({
			contentType: 'application/x-protobuf',
			body: readFileSync(new URL(decodeURIComponent(pathname).replace('/map/', 'map/'), ROME))
		});
	});
	await page.route('**/map/fonts/*.ttf', (route: Route) =>
		route.fulfill({
			contentType: 'font/ttf',
			body: readFileSync(
				new URL(`map/fonts/${new URL(route.request().url()).pathname.split('/').pop()}`, ROME)
			)
		})
	);
	const italic = page.waitForResponse('**/map/fonts/SortsMillGoudy-Italic.ttf');

	await page.goto('/en/');
	await expect(page.locator('.map[data-state="ready"]')).toBeVisible();
	expect((await italic).status()).toBe(200);
	await expect
		.poll(() =>
			page.evaluate(() =>
				[...document.fonts].some(
					(face) => face.family.startsWith('maplibre-gl-font-face') && face.status === 'loaded'
				)
			)
		)
		.toBe(true);
	expect(problems).toEqual([]);
});
