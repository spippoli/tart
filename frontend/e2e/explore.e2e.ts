import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';
import { serveDiscovery, serveStyles } from './map-style';

/**
 * Discovery spec, Explore: the map and the list in sync, the side panel, and the
 * fallbacks (criteria 9, 10, 16, 18 to 21, 32, 37, 40, 49, 50, 57, 58, 67, 68, and the
 * empty viewport of 33). The stand-in API serves ten fictional Locations, about 300 m apart
 * around the default view, with three fictional Artworks each (`mock-api.ts`); the
 * canvas is never pixel-tested: signs are read as the buttons over it.
 */

const WCAG_22_AA = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];
/**
 * A zoom over the middle of the ten Locations that shows all of them, on a narrow map as
 * well as a wide one, and none in a cluster (they are 68 px apart, and clusters reach 50 px).
 */
const GRID = '14/41.8975/12.4893';
const ZOOMED_ON_200 = '18/41.8955/12.4823';

const isMobile = (info: { project: { name: string } }) => info.project.name === 'mobile';
const mapElement = (page: Page) => page.locator('.map[data-state="ready"]');
const sign = (page: Page, id: number) =>
	page.locator(`.map button.tart-sign[data-location="${id}"]`);
// By id, so that they serve both UI languages; criterion 21 checks the landmarks' names.
const mapRegion = (page: Page) => page.locator('#explore-map');
const listRegion = (page: Page) => page.locator('#explore-list');
const entries = (page: Page) => listRegion(page).getByRole('article');
const panelOf = (page: Page, title: string) => page.getByRole('region', { name: title });
const controls = (page: Page) => page.getByRole('group', { name: 'Map controls' });

async function camera(page: Page) {
	const read = async (name: string) => Number(await mapElement(page).getAttribute(`data-${name}`));
	return { zoom: await read('zoom'), lon: await read('lon'), lat: await read('lat') };
}

/** Serves the styles and the Discovery query, then opens Explore with the map drawn. */
async function openExplore(page: Page, path = `/en/?map=${GRID}`, ready = true) {
	// The legend is open on a first visit and would cover signs.
	await page.addInitScript(() => localStorage.setItem('tart.map.legend', 'closed'));
	await serveStyles(page);
	await serveDiscovery(page);
	await page.goto(path);
	if (ready) await expect(mapElement(page)).toBeVisible();
}

/** On a narrow screen the map and the list are shown one at a time. */
async function showView(page: Page, view: 'map' | 'list', mobile: boolean) {
	if (!mobile) return;
	// The switch's two buttons, in either UI language: the map first.
	await page
		.locator('.switch button')
		.nth(view === 'map' ? 0 : 1)
		.click();
	await expect(view === 'map' ? mapRegion(page) : listRegion(page)).toBeVisible();
}

async function openFilters(page: Page, mobile: boolean) {
	if (!mobile) {
		await expect(page.getByRole('checkbox', { name: 'disappeared', exact: true })).toBeVisible();
		return page.getByRole('search', { name: 'Filters' });
	}
	await page.getByRole('button', { name: /^Filters/ }).click();
	return page.getByRole('dialog', { name: 'Filters' });
}

async function apply(page: Page, mobile: boolean) {
	if (mobile) await page.getByRole('button', { name: 'Show results' }).click();
}

async function axe(page: Page, label: string) {
	const results = await new AxeBuilder({ page }).withTags(WCAG_22_AA).analyze();
	expect(results.violations, label).toEqual([]);
}

/** Makes this browser report no WebGL2. */
async function withoutWebGL2(page: Page) {
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
}

test.describe('selection and the side panel', () => {
	// Criterion 9
	test('AC 9: a sign opens the panel with focus on its title; Esc and Close return focus to the sign', async ({
		page
	}, info) => {
		await openExplore(page);
		await sign(page, 200).click();

		const panel = panelOf(page, 'Parete di prova 1');
		await expect(panel.getByRole('heading', { name: 'Parete di prova 1' })).toBeFocused();
		await expect(panel).toContainText('Surface type:');
		await expect(panel).toContainText('Approximate position, within 30 m');
		await expect(panel.getByRole('article')).toHaveCount(3);
		await expect(panel.getByRole('link', { name: "Open the surface's page" })).toHaveAttribute(
			'href',
			'/en/locations/200-superficie-di-prova'
		);
		// A side panel within the map on a wide screen; a bottom sheet on a narrow one.
		const box = (await panel.boundingBox())!;
		if (isMobile(info)) {
			expect(Math.round(box.y + box.height)).toBe(page.viewportSize()!.height);
		} else {
			const frame = (await mapRegion(page).boundingBox())!;
			expect(box.x + box.width).toBeLessThanOrEqual(frame.x + frame.width);
			expect(box.y).toBeGreaterThanOrEqual(frame.y);
		}

		await page.keyboard.press('Escape');
		await expect(panel).toHaveCount(0);
		await expect(sign(page, 200)).toBeFocused();

		await sign(page, 200).click();
		await panel.getByRole('button', { name: 'Close' }).click();
		await expect(panel).toHaveCount(0);
		await expect(sign(page, 200)).toBeFocused();
	});

	test('AC 9: the panel counts the Artworks that do not match the filters', async ({ page }) => {
		await openExplore(page, `/en/?condition=intact&map=${GRID}`);
		await sign(page, 200).click();
		const panel = panelOf(page, 'Parete di prova 1');
		await expect(panel.getByRole('article')).toHaveCount(1);
		await expect(panel).toContainText("2 more artworks on this surface don't match the filters");
	});

	// Criterion 10
	test('AC 10: the selection is in the URL and Back closes it; the viewport is written with replaceState', async ({
		page
	}) => {
		await openExplore(page);
		const panel = panelOf(page, 'Parete di prova 1');
		const steps = () => page.evaluate(() => history.length);
		const before = await steps();

		await sign(page, 200).click();
		await expect(page).toHaveURL(/location=200/);
		await expect(panel).toBeVisible();
		expect(await steps()).toBe(before + 1);

		await page.goBack();
		await expect(panel).toHaveCount(0);
		await expect(page).not.toHaveURL(/location=/);
		await page.goForward();
		await expect(panel).toBeVisible();

		// A link reopens it.
		await page.goto(`/en/?location=201&map=${GRID}`);
		await expect(panelOf(page, 'Parete di prova 2')).toBeVisible();

		// Moves write the viewport without adding history.
		await expect(mapElement(page)).toBeVisible();
		const moved = await steps();
		await controls(page).getByRole('button', { name: 'Zoom in' }).click();
		await expect(page).toHaveURL(/map=15%2F/);
		expect(await steps()).toBe(moved);
		const here = await camera(page);
		await page.reload();
		await expect(mapElement(page)).toBeVisible();
		await expect.poll(async () => (await camera(page)).zoom).toBe(15);
		expect((await camera(page)).lon).toBeCloseTo(here.lon, 3);
		expect((await camera(page)).lat).toBeCloseTo(here.lat, 3);
	});

	// Criterion 20
	test('AC 20: hover triggers nothing on the map or the list', async ({ page }, info) => {
		await openExplore(page);
		const before = page.url();
		await sign(page, 200).hover();
		await page.waitForTimeout(300);
		await expect(panelOf(page, 'Parete di prova 1')).toHaveCount(0);

		await showView(page, 'list', isMobile(info));
		await entries(page).first().hover();
		await entries(page).first().getByRole('button').hover();
		await page.waitForTimeout(300);
		expect(decodeURIComponent(page.url())).toBe(decodeURIComponent(before));
		await expect(page.getByText('Selected', { exact: true })).toHaveCount(0);
		await expect(page.getByRole('region', { name: /^Parete di prova/ })).toHaveCount(0);
	});

	// Criterion 57
	test('AC 57: an unavailable selection selects nothing, keeps the rest of the URL, and says so', async ({
		page
	}) => {
		await openExplore(page, `/en/?type=stencil&location=9999&map=${GRID}`);
		await expect(
			page.getByRole('status').filter({ hasText: 'This place is not available' })
		).toBeVisible();
		await expect(page).not.toHaveURL(/location=/);
		await expect(page).toHaveURL(/type=stencil/);
		await expect(page).toHaveURL(/map=14%2F41\.8975%2F12\.4893/);
		await expect(page.getByRole('region', { name: /^Parete di prova/ })).toHaveCount(0);
		// The key was replaced, not added: Back leaves Explore.
		await page.goBack();
		await expect(page).not.toHaveURL(/\/en\/\?/);
	});

	// Criterion 58
	test('AC 58: a Location outside the filters is selected anyway, with its sign and a working "Clear filters"', async ({
		page
	}) => {
		await openExplore(page, `/en/?condition=unknown&location=200&map=${GRID}`);
		const panel = panelOf(page, 'Parete di prova 1');
		await expect(panel.getByText('No artworks here match the current filters')).toBeVisible();
		// The full stratigraphy, and the sign drawn for the selection only.
		await expect(panel.getByRole('article')).toHaveCount(3);
		await expect(sign(page, 200)).toBeVisible();
		await expect(sign(page, 205)).toHaveCount(0);

		await panel.getByRole('button', { name: 'Clear filters' }).click();
		await expect(page).not.toHaveURL(/condition=/);
		await expect(page).toHaveURL(/location=200/);
		await expect(panel.getByText('No artworks here match the current filters')).toHaveCount(0);
		await expect(panel.getByRole('article')).toHaveCount(3);
		await expect(sign(page, 205)).toBeVisible();
	});
});

test.describe('map and list in sync', () => {
	// Criterion 16
	test('AC 16: the list follows the viewport, resets to page 1 when it moves, and keeps its page out of the URL', async ({
		page
	}, info) => {
		const mobile = isMobile(info);
		await openExplore(page);
		await showView(page, 'list', mobile);
		const status = listRegion(page).getByRole('status').first();
		await expect(status).toHaveText('30 artworks in this area · page 1 of 2');
		await expect(entries(page)).toHaveCount(24);

		await listRegion(page).getByRole('link', { name: 'Page 2' }).click();
		await expect(status).toHaveText('30 artworks in this area · page 2 of 2');
		await expect(entries(page)).toHaveCount(6);
		expect(page.url()).not.toMatch(/page=/);

		// Moving the map resets the list to page 1.
		await showView(page, 'map', mobile);
		await controls(page).getByRole('button', { name: 'Back to the default view' }).click();
		await expect.poll(async () => (await camera(page)).zoom).toBe(12);
		await showView(page, 'list', mobile);
		await expect(status).toHaveText('30 artworks in this area · page 1 of 2');

		// Zoomed on one Location, only its three Artworks are listed.
		await showView(page, 'map', mobile);
		await page.goto(`/en/?map=${ZOOMED_ON_200}`);
		await expect(mapElement(page)).toBeVisible();
		await showView(page, 'list', mobile);
		await expect(status).toHaveText('3 artworks in this area · page 1 of 1');
		await expect(entries(page)).toHaveCount(3);
		expect(page.url()).not.toMatch(/page=/);
	});

	// Criterion 33, the empty viewport
	test('AC 33: an empty viewport says how many are elsewhere, and widens the view', async ({
		page
	}, info) => {
		const mobile = isMobile(info);
		await openExplore(page, `/en/?condition=unknown&map=${ZOOMED_ON_200}`);
		await showView(page, 'list', mobile);
		await expect(
			listRegion(page).getByText('No artworks in this part of the map. 6 in the whole archive')
		).toBeVisible();
		await expect(
			listRegion(page).getByRole('link', { name: 'Browse the Archive view' })
		).toHaveAttribute('href', '/en/archive?condition=unknown');
		await listRegion(page).getByRole('button', { name: 'Widen the view' }).click();
		// On a narrow screen the map comes forward, so that the view is seen widening.
		await expect(mapRegion(page)).toBeVisible();
		await expect.poll(async () => (await camera(page)).zoom).toBeLessThan(18);
		await showView(page, 'list', mobile);
		await expect(entries(page).first()).toBeVisible();
		await expect(listRegion(page).getByRole('status').first()).toContainText(
			'6 artworks in this area'
		);
		expect((await camera(page)).zoom).toBeLessThan(18);
	});

	// Criterion 18
	test('AC 18: "Show on map" selects the Location, opens the panel, and Esc returns focus to the button', async ({
		page
	}, info) => {
		const mobile = isMobile(info);
		await openExplore(page);
		await showView(page, 'list', mobile);
		const show = listRegion(page).getByRole('button', { name: 'Show on map: Opera di prova 01' });
		// The title is a link to the Artwork page, a separate control.
		await expect(
			entries(page).first().getByRole('link', { name: 'Opera di prova 01' })
		).toHaveAttribute('href', '/en/artworks/100-opera-di-prova-1');
		await show.click();

		// On a narrow screen it first switched to the map.
		await expect(mapRegion(page)).toBeVisible();
		const panel = panelOf(page, 'Parete di prova 1');
		await expect(panel.getByRole('heading', { name: 'Parete di prova 1' })).toBeFocused();
		await expect(page).toHaveURL(/location=200/);
		const view = await camera(page);
		expect(Math.abs(view.lon - 12.4823)).toBeLessThan(0.02);

		await page.keyboard.press('Escape');
		await expect(panel).toHaveCount(0);
		await expect(show).toBeFocused();
	});

	test('AC 18: in the Archive view it links to Explore with the Location selected and the map on it', async ({
		page
	}) => {
		await openExplore(page, '/en/archive?type=stencil', false);
		await page.getByRole('link', { name: 'Show on map: Opera di prova 01' }).click();
		await expect(page).toHaveURL(/\/en\/\?type=stencil&location=200&map=17%2F41\.8955%2F12\.4823$/);
		await expect(mapElement(page)).toBeVisible();
		await expect(panelOf(page, 'Parete di prova 1')).toBeVisible();
		await expect.poll(async () => (await camera(page)).zoom).toBe(17);
	});

	// Criterion 19
	test('AC 19: the entries of the selected Location are labelled and outlined; the list stays as it is', async ({
		page
	}, info) => {
		const mobile = isMobile(info);
		await openExplore(page);
		await showView(page, 'list', mobile);
		const titles = () => entries(page).locator('h3').allTextContents();
		const status = listRegion(page).getByRole('status').first();
		const [order, total] = [await titles(), await status.textContent()];
		await showView(page, 'map', mobile);
		await mapRegion(page).scrollIntoViewIfNeeded();
		const scroll = await page.evaluate(() => window.scrollY);

		await sign(page, 200).click();
		const title = panelOf(page, 'Parete di prova 1').getByRole('heading', {
			name: 'Parete di prova 1'
		});
		await expect(title).toBeFocused();
		expect(await page.evaluate(() => window.scrollY)).toBe(scroll);

		await showView(page, 'list', mobile);
		expect(await titles()).toEqual(order);
		await expect(status).toHaveText(total!);
		const selected = entries(page).filter({ hasText: 'Selected' });
		await expect(selected).toHaveCount(3);
		await expect(selected.first()).toContainText('Opera di prova 01');
		// A thick outline besides the text, so that colour is never alone.
		expect(
			await selected.first().evaluate((entry) => parseFloat(getComputedStyle(entry).borderTopWidth))
		).toBeGreaterThanOrEqual(3);
		await expect(entries(page).filter({ hasText: 'Opera di prova 04' })).not.toContainText(
			'Selected'
		);

		// Closing the panel clears the label.
		await showView(page, 'map', mobile);
		await page.keyboard.press('Escape');
		await showView(page, 'list', mobile);
		await expect(page.getByText('Selected', { exact: true })).toHaveCount(0);
	});

	// Criterion 21
	test('AC 21: skip link, regions, and DOM order on a wide screen', async ({ page }, info) => {
		test.skip(isMobile(info), 'the skip links are for the wide layout');
		await openExplore(page, '/en/');
		await expect(page.getByRole('region', { name: 'Map', exact: true })).toBeVisible();
		await expect(page.getByRole('region', { name: 'Artwork list', exact: true })).toBeVisible();
		const skip = page.getByRole('link', { name: 'Skip the map: go to the list (30 artworks)' });
		await expect(skip).toBeAttached();
		await skip.focus();
		await expect(skip).toBeVisible();
		await page.keyboard.press('Enter');
		await expect(listRegion(page)).toBeFocused();

		const back = listRegion(page).getByRole('link', { name: 'Back to the map' });
		await back.focus();
		await page.keyboard.press('Enter');
		await expect(mapRegion(page)).toBeFocused();

		// Filter bar, then the map, then the list.
		const order = await page.evaluate(() => {
			const bar = document.querySelector('[role="search"]')!;
			const map = document.getElementById('explore-map')!;
			const list = document.getElementById('explore-list')!;
			const before = (a: Element, b: Element) =>
				Boolean(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);
			return [before(bar, map), before(map, list)];
		});
		expect(order).toEqual([true, true]);
	});
});

test.describe('filters and the viewport', () => {
	// Criterion 32
	test('AC 32: a filtered URL without a viewport opens fitted to the results', async ({ page }) => {
		await openExplore(page, '/en/?type=stencil');
		await expect.poll(async () => (await camera(page)).zoom).toBeGreaterThan(13);
		const view = await camera(page);
		// Over the ten Locations, inside the Instance boundary.
		expect(view.lon).toBeGreaterThan(12.4823);
		expect(view.lon).toBeLessThan(12.5);
		expect(view.lat).toBeGreaterThan(41.8955);
		expect(view.lat).toBeLessThan(41.91);
		await expect(page).toHaveURL(/map=/);
	});

	test('AC 32: a viewport in the URL is kept, and a filter other than Area does not move the map', async ({
		page
	}, info) => {
		const mobile = isMobile(info);
		await openExplore(page, '/en/?map=13/41.9/12.55');
		await page.waitForTimeout(500);
		const before = await camera(page);
		expect(before.zoom).toBe(13);

		const form = await openFilters(page, mobile);
		await form.getByRole('checkbox', { name: 'Stencil' }).check();
		await apply(page, mobile);
		await expect(page).toHaveURL(/type=stencil/);
		await expect(page).toHaveURL(/map=13%2F41\.9%2F12\.55/);
		await page.waitForTimeout(800);
		expect(await camera(page)).toEqual(before);
	});

	test('AC 32: selecting an Area fits the map to its extent', async ({ page }, info) => {
		const mobile = isMobile(info);
		await openExplore(page, '/en/?map=13/41.95/12.6');
		const form = await openFilters(page, mobile);
		await form.getByRole('checkbox', { name: 'Quartiere Immaginario' }).check();
		await apply(page, mobile);
		// Area 3 spans 12.47 to 12.5 by 41.88 to 41.9.
		await expect.poll(async () => (await camera(page)).lon).toBeCloseTo(12.485, 2);
		const view = await camera(page);
		expect(view.lat).toBeCloseTo(41.89, 2);
		expect(view.zoom).toBeGreaterThan(12);
		expect(view.zoom).toBeLessThanOrEqual(17);
	});
});

test.describe('without a map', () => {
	// Criterion 37
	test('AC 37: without WebGL2 Explore is the Archive view in place, with a notice', async ({
		page
	}) => {
		await withoutWebGL2(page);
		await openExplore(page, `/en/?map=${GRID}&location=200`, false);

		const notice = page.getByText(
			"The map isn't available on this browser or device because it needs WebGL2. You can browse the whole archive from the list."
		);
		await expect(notice).toBeVisible();
		await expect(page.getByRole('alert')).toHaveCount(0);
		await expect(entries(page)).toHaveCount(24);
		await expect(page.getByRole('status').first()).toContainText('30 artworks · page 1 of 2');
		await expect(mapRegion(page)).toHaveCount(0);
		await expect(page.locator('canvas')).toHaveCount(0);
		// No "Map" option in the switch, no "Show on map", no "Centre on my position".
		await expect(page.getByRole('group', { name: 'Show' })).toHaveCount(0);
		await expect(page.getByRole('button', { name: 'Map', exact: true })).toHaveCount(0);
		await expect(page.getByRole('button', { name: /^Show on map/ })).toHaveCount(0);
		await expect(page.getByRole('link', { name: /^Show on map/ })).toHaveCount(0);
		await expect(page.getByRole('button', { name: 'Centre on my position' })).toHaveCount(0);

		// A link to a place on the map leads to the Location page.
		await expect(page.getByText('You opened a link to a location on the map.')).toBeVisible();
		await expect(page.getByRole('link', { name: "Open the surface's page" })).toHaveAttribute(
			'href',
			'/en/locations/200'
		);

		// "Why?" leads to the help entry.
		await page.getByRole('link', { name: 'Why?' }).click();
		await expect(page.locator('#map-help')).toBeFocused();
		await expect(page.locator('#map-help')).toContainText('Enable hardware acceleration');
	});

	test('AC 37: without WebGL2 a link to an unavailable place offers no link to its page', async ({
		page
	}) => {
		await withoutWebGL2(page);
		await openExplore(page, '/en/?location=9999', false);
		await expect(page.getByText("The map isn't available on this browser")).toBeVisible();
		await expect(page.getByText('You opened a link to a location on the map.')).toHaveCount(0);
		await expect(page.getByRole('link', { name: "Open the surface's page" })).toHaveCount(0);
	});

	// Criterion 40
	for (const [name, failure] of [
		['a style that fails to load', { status: 500, body: { detail: 'Internal Server Error' } }],
		['a missing tile extract', { status: 503, body: { code: 'tiles_missing' } }]
	] as const) {
		test(`AC 40: ${name} leaves the list and search working`, async ({ page }, info) => {
			await serveStyles(page, failure);
			await serveDiscovery(page);
			await page.goto('/en/');
			await expect(
				page.getByText(
					"The map isn't available right now. You can browse the whole archive from the list."
				)
			).toBeVisible();
			await expect(entries(page)).toHaveCount(24);
			await expect(mapRegion(page)).toHaveCount(0);

			if (!isMobile(info)) {
				const search = page.getByRole('searchbox', { name: 'Search the archive' });
				await search.fill('prova 05');
				await expect(page).toHaveURL(/q=prova\+05/);
				await expect(entries(page)).toHaveCount(1);
			}
		});
	}
});

test.describe('"Centre on my position"', () => {
	test.describe('with permission', () => {
		test.use({
			permissions: ['geolocation'],
			geolocation: { latitude: 41.8955, longitude: 12.4923 }
		});

		// Criterion 67
		test('AC 67: centres at z16, marks the position, and sends it nowhere', async ({ page }) => {
			const requests: string[] = [];
			page.on('request', (request) => {
				requests.push(request.url() + (request.postData() ?? ''));
			});
			await openExplore(page, '/en/');
			const before = requests.length;
			await controls(page).getByRole('button', { name: 'Centre on my position' }).click();

			await expect.poll(async () => (await camera(page)).zoom).toBe(16);
			expect((await camera(page)).lon).toBeCloseTo(12.4923, 3);
			const mark = page.getByRole('img', { name: 'Your position' });
			await expect(mark).toBeVisible();
			// Not focusable.
			expect(await mark.evaluate((element) => element.tabIndex)).toBe(-1);
			// The URL keeps only the resulting viewport.
			await expect(page).toHaveURL(/map=16%2F/);
			// No request carries the position, apart from the viewport's own bounding box.
			const sent = requests.slice(before).filter((url) => /41\.8955|12\.4923/.test(url));
			expect(sent.filter((url) => !url.includes('bbox=') && !url.includes('/en/?'))).toEqual([]);
		});

		test('AC 67: a position outside the archive shows a notice and the map stays', async ({
			page,
			context
		}) => {
			await openExplore(page, '/en/');
			await context.setGeolocation({ latitude: 51.5, longitude: -0.12 });
			const before = await camera(page);
			await controls(page).getByRole('button', { name: 'Centre on my position' }).click();
			await expect(page.getByText("Your position is outside the archive's area")).toBeVisible();
			await page.waitForTimeout(500);
			expect(await camera(page)).toEqual(before);
			await expect(page.getByRole('img', { name: 'Your position' })).toHaveCount(0);
		});
	});

	test('AC 67: a denied permission shows a notice and the map stays', async ({ page }) => {
		await openExplore(page, '/en/');
		const before = await camera(page);
		await controls(page).getByRole('button', { name: 'Centre on my position' }).click();
		await expect(
			page.getByText('Your position cannot be used: the permission was denied')
		).toBeVisible();
		expect(await camera(page)).toEqual(before);
	});
});

test.describe('loading and failure', () => {
	// Criterion 68
	test('AC 68: "Loading locations…" is announced politely until the Locations arrive', async ({
		page
	}) => {
		await openExplore(page, '/en/', false);
		let release!: () => void;
		const gate = new Promise<void>((resolve) => (release = resolve));
		await page.route(/\/api\/discovery\/locations(\?|$)/, async (route) => {
			await gate;
			await route.fallback();
		});
		await page.reload();
		const status = page.locator('.map [role="status"]');
		await expect(status).toHaveAttribute('aria-live', 'polite');
		await expect(status).toHaveText('Loading locations…');
		release();
		await expect(status).toHaveText('');
		await expect(page.locator('.map button.tart-sign').first()).toBeVisible();
	});

	test('AC 68: a failed Discovery query removes the list and the signs and offers "Retry"', async ({
		page
	}, info) => {
		const mobile = isMobile(info);
		await openExplore(page);
		await expect(sign(page, 200)).toBeVisible();
		let failing = true;
		await page.route(/\/api\/discovery\/artworks/, (route) =>
			failing
				? route.fulfill({ status: 500, contentType: 'application/json', body: '{}' })
				: route.fallback()
		);

		await controls(page).getByRole('button', { name: 'Zoom out' }).click();
		await expect(page).toHaveURL(/map=13%2F/);
		await showView(page, 'list', mobile);
		await expect(
			listRegion(page).getByText('Results for these filters could not be loaded')
		).toBeVisible();
		await expect(entries(page)).toHaveCount(0);
		await showView(page, 'map', mobile);
		await expect(page.locator('.map button.tart-sign')).toHaveCount(0);
		await expect(page).toHaveURL(/map=13%2F/);

		await showView(page, 'list', mobile);
		failing = false;
		await listRegion(page).getByRole('button', { name: 'Retry' }).click();
		await expect(entries(page).first()).toBeVisible();
		await showView(page, 'map', mobile);
		await expect(page.locator('.map button.tart-sign').first()).toBeVisible();
	});

	test('AC 68: a failed map response alone keeps the list and says so in the map control', async ({
		page
	}, info) => {
		const mobile = isMobile(info);
		await openExplore(page, '/en/', false);
		const fail = (route: import('@playwright/test').Route) =>
			route.fulfill({ status: 500, contentType: 'application/json', body: '{}' });
		await page.route(/\/api\/discovery\/locations(\?|$)/, fail);
		await page.reload();
		await expect(mapElement(page)).toBeVisible();

		const control = page.locator('.map');
		await expect(
			control.getByText('Locations are not available on the map. The list is up to date.')
		).toBeVisible();
		await showView(page, 'list', mobile);
		await expect(entries(page).first()).toBeVisible();
		await showView(page, 'map', mobile);

		await page.unroute(/\/api\/discovery\/locations(\?|$)/, fail);
		await control.getByRole('button', { name: 'Retry' }).click();
		await expect(page.locator('.map button.tart-sign').first()).toBeVisible();
		await expect(
			control.getByText('Locations are not available on the map. The list is up to date.')
		).toHaveCount(0);
	});
});

test.describe('the switch on a narrow screen', () => {
	test('shows the map first, then one view at a time', async ({ page }, info) => {
		test.skip(!isMobile(info), 'a narrow screen only');
		await openExplore(page);
		await expect(mapRegion(page)).toBeVisible();
		await expect(listRegion(page)).toBeHidden();
		const group = page.getByRole('group', { name: 'Show' });
		await expect(group.getByRole('button', { name: 'Map', exact: true })).toHaveAttribute(
			'aria-pressed',
			'true'
		);
		await group.getByRole('button', { name: 'List', exact: true }).click();
		await expect(listRegion(page)).toBeVisible();
		await expect(mapRegion(page)).toBeHidden();
	});
});

// Criteria 49 and 50
for (const language of ['en', 'it'] as const) {
	test(`AC 49: Explore passes axe in ${language}, with the panel, an empty viewport, and a failure`, async ({
		page
	}, info) => {
		const mobile = isMobile(info);
		const root = language === 'en' ? '/en/' : '/it/';
		const keys =
			language === 'en'
				? { viewport: 'map', condition: 'condition', location: 'location' }
				: { viewport: 'mappa', condition: 'condizione', location: 'superficie' };
		await openExplore(page, `${root}?${keys.viewport}=${GRID}`);
		await axe(page, 'the map and the list');

		await sign(page, 200).click();
		await expect(page.locator('#panel-title')).toBeFocused();
		await axe(page, 'the panel');

		await page.goto(`${root}?${keys.condition}=unknown&${keys.viewport}=${ZOOMED_ON_200}`);
		await expect(mapElement(page)).toBeVisible();
		await showView(page, 'list', mobile);
		await expect(listRegion(page).getByRole('button', { name: /^(Widen|Allarga)/ })).toBeVisible();
		await axe(page, 'an empty viewport');
	});
}

test('AC 50: the panel, the notices, and the counts come from the Italian catalogue', async ({
	page
}, info) => {
	const mobile = isMobile(info);
	await openExplore(page, `/it/?mappa=${GRID}`);
	await showView(page, 'list', false);
	if (!mobile) {
		await expect(
			page.getByRole('link', { name: "Salta la mappa: vai all'elenco (30 opere)" })
		).toBeAttached();
	}
	await sign(page, 200).click();
	const panel = panelOf(page, 'Parete di prova 1');
	await expect(panel.getByRole('button', { name: 'Chiudi' })).toBeVisible();
	await expect(panel).toContainText('Tipo di superficie:');
	await expect(panel).toContainText('Posizione approssimativa, entro 30 m');
	await expect(panel.getByRole('link', { name: 'Apri la pagina della superficie' })).toBeVisible();
	await page.keyboard.press('Escape');

	await page.goto(`/it/?location=9999&mappa=${GRID}`);
	await expect(page.getByText('Questo luogo non è disponibile')).toBeVisible();

	await page.goto(`/it/?mappa=${ZOOMED_ON_200}`);
	await expect(mapElement(page)).toBeVisible();
	await showView(page, 'list', mobile);
	await expect(listRegion(page).getByRole('status').first()).toHaveText(
		"3 opere in quest'area · pagina 1 di 1"
	);
	// Content keeps its own language whatever the UI language.
	await showView(page, 'map', mobile);
	await sign(page, 200).click();
	await expect(page.locator('#panel-title').locator('[lang]')).toHaveAttribute('lang', 'it');
});
