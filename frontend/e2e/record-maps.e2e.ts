import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { serveStyles } from './map-style';

/**
 * The maps of the record pages and the index name filter (Discovery spec, Mini-map and
 * Index name filter): criteria 36, 39, 41, 65, and 66. The canvas is never pixel-tested:
 * the camera is read from the map's `data-*` attributes, and what the canvas draws from
 * its container's.
 */

const WCAG_22_AA = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];
const ids: Record<string, number> = JSON.parse(
	readFileSync(new URL('fixtures/archive/ids.json', import.meta.url), 'utf8')
);
// Records written by hand (e2e/fixtures/archive-extra): a Location with a large extent
// and three neighbours, and a Series with no visible Location.
const BIG_LOCATION = 9100;
const EMPTY_SERIES = 9101;

const map = (page: Page) => page.locator('.map[data-state="ready"]');
const canvas = (page: Page) => page.locator('.map .canvas');
const zoom = async (page: Page) => Number(await map(page).getAttribute('data-zoom'));

async function open(page: Page, path: string) {
	await serveStyles(page);
	await page.goto(path);
	await expect(map(page)).toBeVisible();
}

async function axe(page: Page, label: string) {
	const results = await new AxeBuilder({ page }).withTags(WCAG_22_AA).analyze();
	expect(results.violations, label).toEqual([]);
}

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

test.describe('AC 41: the mini-map', () => {
	test('frames the Location at z17, still, with only the zoom buttons', async ({ page }) => {
		await open(page, `/en/locations/${ids.cortile}`);

		await expect.poll(() => zoom(page)).toBe(17);
		const centre = {
			lon: Number(await map(page).getAttribute('data-lon')),
			lat: Number(await map(page).getAttribute('data-lat'))
		};
		expect(centre.lon).toBeCloseTo(12.495, 3);
		expect(centre.lat).toBeCloseTo(41.895, 3);

		// No wheel and no drag: the camera does not move.
		const box = (await canvas(page).boundingBox())!;
		await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
		await page.mouse.wheel(0, -600);
		await page.mouse.down();
		await page.mouse.move(box.x + box.width / 2 + 80, box.y + box.height / 2 + 60, { steps: 5 });
		await page.mouse.up();
		await page.keyboard.press('ArrowRight');
		await page.waitForTimeout(600);
		expect(await zoom(page)).toBe(17);
		expect(Number(await map(page).getAttribute('data-lon'))).toBeCloseTo(centre.lon, 5);
		expect(Number(await map(page).getAttribute('data-lat'))).toBeCloseTo(centre.lat, 5);

		const controls = page.getByRole('group', { name: 'Map controls' });
		await expect(controls.getByRole('button')).toHaveText(['+Zoom in', '−Zoom out']);
		await expect(page.getByRole('button', { name: 'Legend' })).toHaveCount(0);
		await controls.getByRole('button', { name: 'Zoom out' }).click();
		await expect.poll(() => zoom(page)).toBe(16);
	});

	test('frames a Location larger than the view on its whole extent', async ({ page }) => {
		await open(page, `/en/locations/${BIG_LOCATION}`);

		await expect.poll(() => zoom(page)).toBeLessThan(17);
		expect(await zoom(page)).toBeGreaterThanOrEqual(15);
		expect(Number(await map(page).getAttribute('data-lon'))).toBeCloseTo(12.486, 3);
		expect(Number(await map(page).getAttribute('data-lat'))).toBeCloseTo(41.8935, 3);
	});

	test('draws no cluster and offers no panel or focusable sign', async ({ page }) => {
		await open(page, `/en/locations/${BIG_LOCATION}`);

		await expect(page.locator('.map button.tart-sign')).toHaveCount(0);
		await expect(page.getByRole('dialog')).toHaveCount(0);
	});

	test('links to Explore on the Location, in the keys of the UI language', async ({ page }) => {
		await open(page, `/en/locations/${ids.cortile}`);
		await expect(page.getByRole('link', { name: 'Open on the map' })).toHaveAttribute(
			'href',
			`/en/?location=${ids.cortile}&map=17/41.89500/12.49500`
		);

		await open(page, `/it/superfici/${ids.cortile}`);
		await expect(page.getByRole('link', { name: 'Apri sulla mappa' })).toHaveAttribute(
			'href',
			`/it/?superficie=${ids.cortile}&mappa=17/41.89500/12.49500`
		);
	});

	test('is on Artwork pages too, and passes axe in it and en', async ({ page }) => {
		for (const path of [`/en/artworks/${ids.gatto}`, `/it/opere/${ids.gatto}`]) {
			await open(page, path);
			await expect(page.locator('.map[data-mini]')).toBeVisible();
			await axe(page, path);
		}
		for (const path of [`/en/locations/${BIG_LOCATION}`, `/it/superfici/${BIG_LOCATION}`]) {
			await open(page, path);
			await axe(page, path);
		}
	});
});

test.describe('AC 66: the neighbours of the mini-map', () => {
	test('are muted signs that cannot be focused and are not in the accessibility tree', async ({
		page
	}) => {
		await open(page, `/en/locations/${BIG_LOCATION}`);

		await expect(canvas(page)).toHaveAttribute('data-muted', '3');
		// Only the control's buttons and the attribution toggle are in the map: nothing for the neighbours.
		const buttons = page.locator('.map').getByRole('button');
		const names = (await buttons.allTextContents()).map((text) => text.trim());
		expect(names).toEqual(['+Zoom in', '−Zoom out']);
		await expect(page.locator('.map').getByRole('link', { name: /Location/ })).toHaveCount(0);
		await page.keyboard.press('Tab');
		const reachable = await page.evaluate(() =>
			[...document.querySelectorAll('.map [tabindex], .map canvas')].map((element) =>
				element.getAttribute('tabindex')
			)
		);
		expect(reachable.every((value) => value === null || Number(value) < 0)).toBe(true);
	});

	test('a Location without neighbours has none', async ({ page }) => {
		await open(page, `/en/locations/${ids.cortile}`);

		await expect(canvas(page)).toHaveAttribute('data-muted', '0');
	});

	test('cannot be zoomed out past z15', async ({ page }) => {
		await open(page, `/en/locations/${ids.cortile}`);
		const zoomOut = page
			.getByRole('group', { name: 'Map controls' })
			.getByRole('button', { name: 'Zoom out' });

		for (let step = 0; step < 5; step++) {
			await zoomOut.click();
			await page.waitForTimeout(150);
		}
		await expect.poll(() => zoom(page)).toBe(15);
	});
});

test.describe('AC 39: record pages without WebGL2', () => {
	test('replace the mini-map with the text box', async ({ page }) => {
		await withoutWebGL2(page);
		await serveStyles(page);
		await page.goto(`/en/locations/${ids.cortile}`);

		await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
		await expect(page.locator('.map')).toHaveCount(0);
		await expect(page.locator('canvas')).toHaveCount(0);
		const box = page.locator('.where');
		await expect(box.getByText('Surface')).toBeVisible();
		await expect(box.getByText(/Coordinates/)).toBeVisible();
		await expect(box.getByRole('link', { name: 'Open in a maps app' })).toHaveAttribute(
			'href',
			/^geo:41\.8950\d+,12\.4950\d+/
		);
		await expect(box.getByText('Quartiere Immaginario')).toBeVisible();
		await expect(box.getByText('Ex deposito dei tram fittizio')).toBeVisible();
		await axe(page, 'without WebGL2');
	});

	test('keep the text box when the style cannot be loaded', async ({ page }) => {
		await serveStyles(page, { status: 503, body: { code: 'tiles_missing' } });
		await page.goto(`/it/opere/${ids.gatto}`);

		await expect(page.locator('.where').getByRole('link', { name: /app di mappe/ })).toBeVisible();
		await expect(page.locator('.map')).toHaveCount(0);
	});

	test.describe('without JavaScript', () => {
		test.use({ javaScriptEnabled: false });

		test('the text box is there', async ({ page }) => {
			await page.goto(`/en/artworks/${ids.gatto}`);

			await expect(
				page.locator('.where').getByRole('link', { name: 'Open in a maps app' })
			).toBeVisible();
		});
	});
});

test.describe('AC 65: the maps of a Site, Area, or Series', () => {
	test('a Series map shows only the Locations of its Artworks, with no outline', async ({
		page
	}) => {
		await open(page, `/en/series/${ids.gatti}-gatti-di-carta`);

		await expect(canvas(page)).toHaveAttribute('data-outline', 'false');
		await expect(page.locator('.map button.tart-sign')).toHaveCount(2);
		await expect(page.locator('.map button.tart-sign').first()).toHaveAttribute(
			'aria-label',
			/Location, 1 artwork/
		);
		await axe(page, 'series map');
	});

	test('an Area map draws its outline', async ({ page }) => {
		await open(page, `/en/areas/${ids.quartiere}-quartiere-immaginario`);

		await expect(canvas(page)).toHaveAttribute('data-outline', 'true');
		await expect(page.locator('.map button.tart-sign')).toHaveCount(3);
	});

	test('a Site map fits its Location and stops at z17', async ({ page }) => {
		await open(page, `/en/sites/${ids.deposito}-ex-deposito-dei-tram-fittizio`);

		await expect(page.locator('.map button.tart-sign')).toHaveCount(1);
		await expect.poll(() => zoom(page)).toBe(17);
	});

	test('activating a Location opens its page', async ({ page }) => {
		await open(page, `/en/series/${ids.gatti}-gatti-di-carta`);
		await page.locator('.map button.tart-sign').first().click();

		await expect(page).toHaveURL(/\/en\/locations\/\d+/);
	});

	test('a Series with no visible Location has no map', async ({ page }) => {
		await serveStyles(page);
		await page.goto(`/en/series/${EMPTY_SERIES}`);

		await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
		await expect(page.locator('.map')).toHaveCount(0);
		await expect(page.getByRole('region', { name: 'Map' })).toHaveCount(0);
	});
});

test.describe('AC 36: the Filter by name field of the indexes', () => {
	const indexes = [
		['/en/artists', 'Lupo', 'Lupo Inventato', 'Ombra Supposta'],
		['/it/artisti', 'ombra', 'Ombra Supposta', 'Lupo Inventato'],
		['/en/sites', 'tram', 'Ex deposito dei tram fittizio', null],
		['/it/aree', 'quartiere', 'Quartiere Immaginario', 'Rione di Prova'],
		['/en/series', 'gatti', 'Gatti di carta', null]
	] as const;

	for (const [path, text, shown, hidden] of indexes) {
		test(`filters ${path} by name`, async ({ page }) => {
			await page.goto(path);
			// The form is server-rendered; a field filled before hydration would be reset by it.
			await page.waitForLoadState('networkidle');
			const language = path.startsWith('/it') ? 'it' : 'en';
			const label = language === 'it' ? 'Filtra per nome' : 'Filter by name';
			await page.getByRole('searchbox', { name: label }).fill(text);
			await page.getByRole('button', { name: language === 'it' ? 'Filtra' : 'Filter' }).click();

			await expect(page).toHaveURL(
				new RegExp(`[?&]${language === 'it' ? 'nome' : 'name'}=${text}`)
			);
			await expect(page.getByRole('link', { name: shown })).toBeVisible();
			if (hidden) await expect(page.getByRole('link', { name: hidden })).toHaveCount(0);
			await expect(page.getByRole('searchbox', { name: label })).toHaveValue(text);
			await axe(page, path);
		});
	}

	test('matches without regard to accents, and says when nothing matches', async ({ page }) => {
		await page.goto('/en/artists?name=zzzz');
		await expect(page.getByText('No match for “zzzz”.')).toBeVisible();
		await page.getByRole('link', { name: 'Clear the filter' }).click();
		await expect(page).toHaveURL(/\/en\/artists$/);
		await expect(page.getByRole('link', { name: 'Lupo Inventato' })).toBeVisible();
	});

	test('accepts the key of the other UI language', async ({ page }) => {
		await page.goto('/en/artists?nome=lupo');

		await expect(page.getByRole('link', { name: 'Lupo Inventato' })).toBeVisible();
		await expect(page.getByRole('link', { name: 'Ombra Supposta' })).toHaveCount(0);
	});

	test.describe('without JavaScript', () => {
		test.use({ javaScriptEnabled: false });

		test('the form still filters', async ({ page }) => {
			await page.goto('/it/artisti');
			await page.getByRole('searchbox', { name: 'Filtra per nome' }).fill('lupo');
			await page.getByRole('button', { name: 'Filtra' }).click();

			await expect(page).toHaveURL(/\/it\/artisti\?nome=lupo/);
			await expect(page.getByRole('link', { name: 'Lupo Inventato' })).toBeVisible();
			await expect(page.getByRole('link', { name: 'Ombra Supposta' })).toHaveCount(0);
		});
	});
});
