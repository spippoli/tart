import AxeBuilder from '@axe-core/playwright';
import type { Locator, Page } from '@playwright/test';
import { expect, test } from './test';
import { readFileSync } from 'node:fs';
import { serveLocations, serveStyles } from './map-style';

/**
 * Explore's map, the archive layers (Discovery spec, The map: signs, stack, clusters,
 * geometries), over the fictional Locations in `fixtures/map/locations.json`:
 * criteria 1, 2, 3, 5, 6, 7, 8, 11, 60, and 61. The canvas is never read for pixels:
 * the signs and clusters are the focusable buttons over it, and the geometries and
 * hatched areas it draws are on the map container's `data-*` attributes.
 *
 * Locations 1 to 9 lie within about 90 m of the default view's centre, so that all are
 * in view at z17 (MapLibre's zoom, where a pixel is about 0.44 m), and Location 22 (an
 * approximate point) 250 m south of it, alone at z15.
 */
const WCAG_22_AA = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];

const fixture = JSON.parse(
	readFileSync(new URL('fixtures/map/locations.json', import.meta.url), 'utf8')
) as { locations: { properties: { id: number; point: [number, number] } }[] };

/** Where a position falls on the page, from the map's camera (Web Mercator, 512 px tiles). */
async function project(page: Page, [lon, lat]: [number, number]) {
	const element = map(page);
	const read = async (name: string) => Number(await element.getAttribute(`data-${name}`));
	const world = 512 * 2 ** (await read('zoom'));
	const x = (longitude: number) => ((longitude + 180) / 360) * world;
	const y = (latitude: number) =>
		(0.5 - Math.log(Math.tan(Math.PI / 4 + (latitude * Math.PI) / 360)) / (2 * Math.PI)) * world;
	const box = (await canvas(page).boundingBox())!;
	return {
		x: box.x + box.width / 2 + x(lon) - x(await read('lon')),
		y: box.y + box.height / 2 + y(lat) - y(await read('lat'))
	};
}

const map = (page: Page) => page.locator('.map[data-state="ready"]');
const canvas = (page: Page) => page.locator('.map .canvas');
const buttons = (page: Page) => page.locator('.map button.tart-sign');

async function zoomTo(page: Page, zoom: number, language = 'en') {
	const [controls, label] =
		language === 'it' ? ['Comandi della mappa', 'Ingrandisci'] : ['Map controls', 'Zoom in'];
	const zoomIn = page.getByRole('group', { name: controls }).getByRole('button', { name: label });
	const zoomNow = async () => Number(await map(page).getAttribute('data-zoom'));
	for (let current = await zoomNow(); current < zoom; current++) {
		await zoomIn.click();
		await expect
			.poll(async () => Number(await map(page).getAttribute('data-zoom')))
			.toBe(current + 1);
	}
}

async function openExplore(page: Page, zoom = 12) {
	await serveStyles(page);
	await serveLocations(page);
	await page.goto('/en/');
	await expect(map(page)).toBeVisible();
	await zoomTo(page, zoom);
}

/** The sign buttons of Locations 1 to 9 by their accessible names, in the fixture's words. */
const NAMES = {
	1: 'Location, 1 artwork: 1 present',
	2: 'Location, 3 artworks: 1 present, 2 disappeared',
	3: 'Location, 1 artwork: 1 unknown',
	4: 'Location, 1 artwork: 1 disappeared',
	5: 'Location, 1 artwork: 1 present, approximate position',
	6: 'Location, 1 artwork: 1 unknown, approximate position',
	7: 'Location, 2 artworks: 1 present, 1 unknown',
	8: 'Location, 2 artworks: 1 unknown, 1 disappeared',
	9: 'Location, 2 artworks: 2 disappeared, approximate position'
};

const sign = (page: Page, name: string): Locator =>
	page.locator('.map button.tart-sign').and(page.getByRole('button', { name, exact: true }));

test('AC 1, 2, and 7: one focusable sign per Location, named by counts, at least 24 px', async ({
	page
}) => {
	await openExplore(page, 17);
	await expect(buttons(page)).toHaveCount(9);
	for (const name of new Set(Object.values(NAMES))) {
		await expect(sign(page, name).first()).toBeVisible();
	}
	// Solid if any is present, else dotted if any is unknown, else dashed.
	await expect(sign(page, NAMES[1])).toHaveAttribute('data-sign', 'present-single-normal');
	await expect(sign(page, NAMES[3])).toHaveAttribute('data-sign', 'unknown-single-normal');
	await expect(sign(page, NAMES[7])).toHaveAttribute('data-sign', 'present-stack-normal');
	await expect(sign(page, NAMES[8])).toHaveAttribute('data-sign', 'unknown-stack-normal');
	await expect(sign(page, NAMES[4])).toHaveAttribute('data-sign', 'disappeared-single-normal');
	await expect(sign(page, NAMES[2])).toHaveAttribute('data-sign', 'present-stack-normal');
	for (const button of await buttons(page).all()) {
		const box = (await button.boundingBox())!;
		expect(box.width).toBeGreaterThanOrEqual(24);
		expect(box.height).toBeGreaterThanOrEqual(24);
	}
});

test('AC 3: only a Location with more than one matching Artwork shows the stack', async ({
	page
}) => {
	await openExplore(page, 17);
	const stacked = page.locator('.map button.tart-sign[data-sign*="-stack-"]');
	await expect(stacked).toHaveCount(4);
	expect(
		(await stacked.evaluateAll((all) => all.map((b) => b.getAttribute('aria-label')))).sort()
	).toEqual([NAMES[2], NAMES[7], NAMES[8], NAMES[9]].sort());
	await expect(page.locator('.map button.tart-sign[data-sign*="-single-"]')).toHaveCount(5);
});

test('AC 8 and 61: an approximate point has a smaller sign and, from z15 unclustered, its hatch', async ({
	page
}) => {
	await openExplore(page, 14);
	await expect(canvas(page)).toHaveAttribute('data-hatched', '');
	await zoomTo(page, 15);
	// Location 22 is alone at z15; Location 5 is clustered with its neighbours.
	await expect(canvas(page)).toHaveAttribute('data-hatched', '22');
	await zoomTo(page, 17);
	await expect(canvas(page)).toHaveAttribute('data-hatched', '5');
	// Only a point with a radius is hatched; the others say it in words and keep the sign.
	await expect(sign(page, NAMES[6])).toHaveAttribute('data-sign', 'unknown-single-small');
	await expect(sign(page, NAMES[5])).toHaveAttribute('data-sign', 'present-single-small');
	await expect(sign(page, NAMES[9])).toHaveAttribute('data-sign', 'disappeared-stack-small');
	await expect(canvas(page)).not.toHaveAttribute('data-hatched', /\b(6|9)\b/);
});

test.describe('AC 5: clusters', () => {
	const CLUSTER = 'Cluster of 15 artworks in 10 Locations; activate to zoom in';

	test('up to z16 nearby Locations form a neutral, focusable cluster; from z17 none', async ({
		page
	}) => {
		await openExplore(page, 12);
		const cluster = page.getByRole('button', { name: CLUSTER });
		await expect(cluster).toBeVisible();
		await expect(cluster).toHaveAttribute('data-sign', 'cluster');
		await expect(buttons(page)).toHaveCount(1);
		await zoomTo(page, 17);
		await expect(page.locator('.map button[data-sign="cluster"]')).toHaveCount(0);
	});

	test('a click zooms to the expansion zoom', async ({ page }) => {
		await openExplore(page, 12);
		// On a narrow screen the legend, open on the first visit, covers the cluster.
		const legend = page.getByRole('button', { name: 'Legend' });
		if ((await legend.getAttribute('aria-expanded')) === 'true') await legend.click();
		await page.getByRole('button', { name: CLUSTER }).click();
		await expect
			.poll(async () => Number(await map(page).getAttribute('data-zoom')))
			.toBeGreaterThan(12);
	});

	for (const key of ['Enter', 'Space']) {
		test(`${key} zooms to the expansion zoom`, async ({ page }) => {
			await openExplore(page, 12);
			await page.getByRole('button', { name: CLUSTER }).focus();
			await page.keyboard.press(key);
			await expect
				.poll(async () => Number(await map(page).getAttribute('data-zoom')))
				.toBeGreaterThan(12);
		});
	}
});

test('AC 6 and 60: from z17 lines and polygons draw their geometry by prevailing group', async ({
	page
}) => {
	await openExplore(page, 16);
	await expect(canvas(page)).toHaveAttribute('data-geometries', '');
	await zoomTo(page, 17);
	// Location 7 is a line (present), 8 a polygon (unknown), 9 a polygon (disappeared).
	await expect(canvas(page)).toHaveAttribute(
		'data-geometries',
		'7:present 8:unknown 9:disappeared'
	);
	// The sign of a line sits on the line, and of a U-shaped polygon inside its arm
	// (the fixture's representative points lie on and inside them: see `locations.test.ts`).
	for (const name of [NAMES[7], NAMES[8]]) {
		const feature = fixture.locations.find(
			(location) => location.properties.id === (name === NAMES[7] ? 7 : 8)
		)!;
		const expected = await project(page, feature.properties.point);
		const box = (await sign(page, name).boundingBox())!;
		expect(box.x + box.width / 2).toBeCloseTo(expected.x, -1);
		expect(box.y + box.height / 2).toBeCloseTo(expected.y, -1);
	}
});

test('AC 11: Site names are linked labels from z16, and there are no layer toggles', async ({
	page
}) => {
	await openExplore(page, 15);
	await expect(page.locator('.map a.tart-site')).toHaveCount(0);
	await zoomTo(page, 16);
	const site = page.getByRole('link', { name: 'Ex deposito dei tram fittizio' });
	await expect(site).toBeVisible();
	await expect(site).toHaveAttribute('href', '/en/sites/1000-ex-deposito-dei-tram-fittizio');
	await expect(page.locator('.map input[type="checkbox"]')).toHaveCount(0);
});

test('hover triggers nothing on the map', async ({ page }) => {
	await openExplore(page, 17);
	await expect(buttons(page)).toHaveCount(9);
	const before = await buttons(page).evaluateAll((all) => all.map((b) => b.outerHTML));
	const box = (await sign(page, NAMES[1]).first().boundingBox())!;
	await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
	await page.waitForTimeout(300);
	expect(await buttons(page).evaluateAll((all) => all.map((b) => b.outerHTML))).toEqual(before);
});

for (const language of ['en', 'it']) {
	test(`AC 49: the map with its signs passes axe in ${language}`, async ({ page }) => {
		await serveStyles(page);
		await serveLocations(page);
		await page.goto(`/${language}/`);
		await expect(map(page)).toBeVisible();
		await zoomTo(page, 17, language);
		await expect(buttons(page)).toHaveCount(9);
		const results = await new AxeBuilder({ page }).withTags(WCAG_22_AA).analyze();
		expect(results.violations).toEqual([]);
	});
}
