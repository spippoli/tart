import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';
import { serveLocations, serveStyles, TOKENS } from './map-style';

/**
 * The map module on Explore (Discovery spec, Map controls, legend, attribution;
 * Explore without WebGL2 or JavaScript). The canvas is never pixel-tested: the
 * camera after each move is read from the map's `data-*` attributes.
 */

const WCAG_22_AA = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];
// The fictional configuration's default view and boundary box (e2e/fixtures/config.json).
const DEFAULT_VIEW = { lon: 12.4823, lat: 41.8955, zoom: 12 };
const BOUNDARY = { west: 12.23, south: 41.65, east: 12.86, north: 42.14 };

const map = (page: Page) => page.locator('.map[data-state="ready"]');

async function camera(page: Page) {
	const element = map(page);
	const read = async (name: string) => Number(await element.getAttribute(`data-${name}`));
	return {
		zoom: await read('zoom'),
		lon: await read('lon'),
		lat: await read('lat'),
		bearing: await read('bearing'),
		pitch: await read('pitch')
	};
}

async function openExplore(page: Page, path = '/en/') {
	await serveStyles(page);
	await serveLocations(page);
	await page.goto(path);
	await expect(map(page)).toBeVisible();
}

test('the map loads its style and worker without errors', async ({ page }) => {
	const errors: string[] = [];
	page.on('console', (message) => {
		if (message.type() === 'error') errors.push(message.text());
	});
	page.on('pageerror', (error) => errors.push(error.message));
	await openExplore(page);
	await page
		.getByRole('group', { name: 'Map controls' })
		.getByRole('button', { name: 'Zoom in' })
		.click();
	await expect.poll(async () => (await camera(page)).zoom).toBe(13);
	expect(errors).toEqual([]);
});

test.describe('AC 12: pan and zoom without dragging', () => {
	test('zoom, the four pan buttons, and the reset to the default view', async ({ page }) => {
		await openExplore(page);
		const controls = page.getByRole('group', { name: 'Map controls' });
		const start = await camera(page);
		expect(start).toMatchObject({ zoom: DEFAULT_VIEW.zoom, bearing: 0, pitch: 0 });
		expect(start.lon).toBeCloseTo(DEFAULT_VIEW.lon, 4);

		await controls.getByRole('button', { name: 'Zoom in' }).click();
		await expect.poll(async () => (await camera(page)).zoom).toBe(13);
		await controls.getByRole('button', { name: 'Zoom out' }).click();
		await expect.poll(async () => (await camera(page)).zoom).toBe(12);

		const moves = [
			['Move east', 'lon', 1],
			['Move west', 'lon', -1],
			['Move north', 'lat', 1],
			['Move south', 'lat', -1]
		] as const;
		for (const [name, axis, sign] of moves) {
			const before = (await camera(page))[axis];
			await controls.getByRole('button', { name }).click();
			await expect.poll(async () => Math.sign((await camera(page))[axis] - before)).toBe(sign);
		}

		await controls.getByRole('button', { name: 'Zoom in' }).click();
		await controls.getByRole('button', { name: 'Move east' }).click();
		await controls.getByRole('button', { name: 'Back to the default view' }).click();
		await expect
			.poll(async () => {
				const { zoom, lon, lat } = await camera(page);
				return [zoom, +lon.toFixed(4), +lat.toFixed(4)];
			})
			.toEqual([DEFAULT_VIEW.zoom, DEFAULT_VIEW.lon, DEFAULT_VIEW.lat]);
	});

	test('the keyboard still moves the map, but never rotates or tilts it', async ({ page }) => {
		await openExplore(page);
		const canvas = page.getByRole('region', { name: /^Interactive map/ });
		await canvas.focus();

		const before = await camera(page);
		await page.keyboard.press('ArrowRight');
		await expect.poll(async () => (await camera(page)).lon).toBeGreaterThan(before.lon);
		for (const key of ['Shift+ArrowLeft', 'Shift+ArrowRight', 'Shift+ArrowUp', 'Shift+ArrowDown']) {
			await page.keyboard.press(key);
		}
		await page.waitForTimeout(600);
		expect(await camera(page)).toMatchObject({ bearing: 0, pitch: 0 });
	});

	test('moves are instant under reduced motion, and animated otherwise', async ({ page }) => {
		// The zoom right after a click on Zoom in, before any animation frame could run.
		const zoomRightAfterClick = () =>
			page.evaluate(async () => {
				const button = [...document.querySelectorAll('button')].find((element) =>
					element.textContent?.includes('Zoom in')
				)!;
				button.click();
				await Promise.resolve();
				return Number(document.querySelector<HTMLElement>('.map[data-state]')!.dataset.zoom);
			});

		await openExplore(page);
		expect(await zoomRightAfterClick()).toBe(12);

		await page.emulateMedia({ reducedMotion: 'reduce' });
		await page.reload();
		await expect(map(page)).toBeVisible();
		expect(await zoomRightAfterClick()).toBe(13);
	});
});

test('AC 64: no map pans beyond the boundary box plus 2 km or zooms beyond z19', async ({
	page
}) => {
	// About fifty clicks, each followed by a map render: more than 30 s on a CI mobile profile.
	test.slow();
	await openExplore(page);
	await page.emulateMedia({ reducedMotion: 'reduce' });
	await page.reload();
	await expect(map(page)).toBeVisible();
	const controls = page.getByRole('group', { name: 'Map controls' });

	for (let step = 0; step < 10; step++) {
		await controls.getByRole('button', { name: 'Zoom in' }).click();
	}
	await expect.poll(async () => (await camera(page)).zoom).toBe(19);

	await controls.getByRole('button', { name: 'Back to the default view' }).click();
	for (let step = 0; step < 12; step++) {
		await controls.getByRole('button', { name: 'Move east' }).click();
		await controls.getByRole('button', { name: 'Move north' }).click();
	}
	// 2 km is about 0.024° of longitude and 0.018° of latitude here.
	const { lon, lat } = await camera(page);
	expect(lon).toBeLessThan(BOUNDARY.east + 0.025);
	expect(lat).toBeLessThan(BOUNDARY.north + 0.019);

	for (let step = 0; step < 8; step++) {
		await controls.getByRole('button', { name: 'Zoom out' }).click();
	}
	const zoomedOut = await camera(page);
	expect(zoomedOut.lon).toBeGreaterThan(BOUNDARY.west);
	expect(zoomedOut.lon).toBeLessThan(BOUNDARY.east);
	expect(zoomedOut.zoom).toBeGreaterThan(8);
});

test.describe('AC 13: the legend', () => {
	const legendLines = [
		'Solid square: at least one artwork is present',
		'Dotted square with a question mark: condition unknown',
		'Dashed square: the artworks have disappeared',
		'Second outline: more than one artwork on the same surface',
		'Circle: a group of nearby places, with the number of artworks',
		'Hatched area: an approximate position'
	];

	test('is open on the first visit, closed afterwards, and remembers the choice', async ({
		page
	}) => {
		await openExplore(page);
		const legend = page.getByRole('button', { name: 'Legend' });
		await expect(legend).toHaveAttribute('aria-expanded', 'true');
		await expect(page.locator('.legend li')).toHaveText(legendLines);

		await page.reload();
		await expect(map(page)).toBeVisible();
		await expect(legend).toHaveAttribute('aria-expanded', 'false');
		await expect(page.getByText(legendLines[0])).toBeHidden();

		await legend.click();
		await expect(page.getByText(legendLines[0])).toBeVisible();
		await page.reload();
		await expect(legend).toHaveAttribute('aria-expanded', 'true');
	});

	test('draws every sign from the Instance style, with translated text', async ({ page }) => {
		await page.emulateMedia({ colorScheme: 'light' });
		await openExplore(page, '/it/');
		const signs = page.locator('.legend svg');
		await expect(signs).toHaveCount(6);
		await expect(page.locator('.legend [data-sign="present"] path').first()).toHaveAttribute(
			'fill',
			TOKENS.light['marker.ink']
		);
		await expect(page.locator('.legend [data-sign="disappeared"] path').first()).toHaveAttribute(
			'stroke',
			TOKENS.light['marker.accent']
		);
		await expect(page.getByRole('button', { name: 'Legenda' })).toBeVisible();
		await expect(page.getByText("Quadrato pieno: almeno un'opera è presente")).toBeVisible();
	});

	test('works when localStorage is unavailable', async ({ page }) => {
		await page.addInitScript(() => {
			Object.defineProperty(window, 'localStorage', {
				get() {
					throw new DOMException('denied', 'SecurityError');
				}
			});
		});
		await openExplore(page);
		const legend = page.getByRole('button', { name: 'Legend' });
		await expect(legend).toHaveAttribute('aria-expanded', 'true');
		await legend.click();
		await expect(legend).toHaveAttribute('aria-expanded', 'false');
		await page.reload();
		await expect(legend).toHaveAttribute('aria-expanded', 'true');
	});
});

test('AC 14: the configured attribution, as untranslated links behind a translated toggle', async ({
	page
}) => {
	for (const [path, toggle] of [
		['/en/', 'Show or hide the map credits'],
		['/it/', 'Mostra o nascondi i crediti della mappa']
	]) {
		await openExplore(page, path);
		const credit = page.getByRole('link', { name: '© OpenStreetMap' });
		await expect(credit).toHaveAttribute('href', 'https://www.openstreetmap.org/copyright');
		// MapLibre's toggle is the <summary> of a <details>: focusable and operable by keyboard.
		const toggleControl = page.locator(`summary[aria-label="${toggle}"]`);
		const details = page.locator('details.maplibregl-ctrl-attrib');
		await toggleControl.focus();
		await expect(toggleControl).toBeFocused();
		const open = await details.evaluate((element) => (element as HTMLDetailsElement).open);
		await page.keyboard.press('Enter');
		await expect
			.poll(() => details.evaluate((element) => (element as HTMLDetailsElement).open))
			.toBe(!open);
	}
});

test('AC 15, AC 71: the map and the UI follow the system colour scheme without a reload', async ({
	page
}) => {
	await page.emulateMedia({ colorScheme: 'light' });
	await openExplore(page);
	const present = page.locator('.legend [data-sign="present"] path').first();
	await expect(present).toHaveAttribute('fill', TOKENS.light['marker.ink']);
	await page.evaluate(() => ((window as unknown as { notReloaded: boolean }).notReloaded = true));

	const darkStyle = page.waitForRequest('**/api/map/style/dark.json');
	await page.emulateMedia({ colorScheme: 'dark' });
	await darkStyle;
	await expect(present).toHaveAttribute('fill', TOKENS.dark['marker.ink']);
	await expect(page.locator('body')).toHaveCSS('background-color', 'rgb(18, 18, 18)');
	await expect(map(page)).toBeVisible();
	expect(
		await page.evaluate(() => (window as unknown as { notReloaded?: boolean }).notReloaded)
	).toBe(true);
	// There is no theme toggle.
	await expect(page.getByRole('button', { name: /theme|tema/i })).toHaveCount(0);
});

test.describe('the map reports itself unavailable', () => {
	test('without WebGL2', async ({ page }) => {
		await page.addInitScript(() => {
			const getContext = HTMLCanvasElement.prototype.getContext;
			HTMLCanvasElement.prototype.getContext = function (
				this: HTMLCanvasElement,
				type: string,
				...rest: unknown[]
			) {
				return type === 'webgl2' ? null : getContext.call(this, type as '2d', ...(rest as []));
			} as typeof getContext;
		});
		const styleRequests: string[] = [];
		page.on('request', (request) => {
			if (request.url().includes('/api/map/style/')) styleRequests.push(request.url());
		});
		await serveStyles(page);
		await page.goto('/en/');
		await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
		await expect(page.getByRole('region', { name: 'Map' })).toHaveCount(0);
		await expect(page.locator('canvas')).toHaveCount(0);
		expect(styleRequests).toEqual([]);
	});

	for (const [name, failure] of [
		['when the tile extract is missing', { status: 503, body: { code: 'tiles_missing' } }],
		['when the style fails to load', { status: 500, body: { detail: 'Internal Server Error' } }],
		[
			'when MapLibre rejects the style',
			{ status: 200, body: { version: 7, metadata: { 'tart:tokens': TOKENS.light } } }
		]
	] as const) {
		test(name, async ({ page }) => {
			await serveStyles(page, failure);
			const loaded = page.waitForResponse('**/api/map/style/*.json');
			await page.goto('/en/');
			await loaded;
			await expect(page.getByRole('region', { name: 'Map' })).toHaveCount(0);
			await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
		});
	}

	test('without JavaScript there is no map', async ({ browser }) => {
		const context = await browser.newContext({ javaScriptEnabled: false });
		const page = await context.newPage();
		await page.goto('/en/');
		await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
		await expect(page.getByRole('region', { name: 'Map' })).toHaveCount(0);
		await context.close();
	});
});

for (const path of ['/it/', '/en/']) {
	for (const colorScheme of ['light', 'dark'] as const) {
		test(`the map on ${path} passes axe in the ${colorScheme} theme`, async ({ page }) => {
			await page.emulateMedia({ colorScheme });
			await openExplore(page, path);
			await expect(page.locator('.legend ul')).toBeVisible();
			const results = await new AxeBuilder({ page }).withTags(WCAG_22_AA).analyze();
			expect(results.violations).toEqual([]);
		});
	}
}
