/**
 * Archive records spec, record pages, against the stand-in API's answers over the
 * fictional dataset (`fixtures/archive`, the real API's responses): criteria 1, 14, 16,
 * 22, 23, 28, 30, 31, 32, 33, 34, 36, 37, and 50 for the Artwork and Documentation item
 * pages. Pending content needs Submissions (Contribution and moderation), so the pending
 * state of criterion 37 comes with them.
 */
import AxeBuilder from '@axe-core/playwright';
import type { Page } from '@playwright/test';
import { expect, hydrated, test } from './test';
import { readFileSync } from 'node:fs';

const ids: Record<string, number> = JSON.parse(
	readFileSync(new URL('fixtures/archive/ids.json', import.meta.url), 'utf8')
);
const WITHDRAWN = 9001;
const MERGED = 9002;
const WCAG_22_AA = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];

const artworkStates: Record<string, number> = {
	complete: ids.gatto,
	untitled: ids['senza-titolo'],
	'unknown artist': ids.occhio,
	'disputed attribution': ids.mani,
	'approximate location (and a redacted description)': ids.onda,
	disappeared: ids.coperto,
	destroyed: ids.fiore,
	'no image (link-only documentation)': ids.scritta,
	merged: MERGED
};
const documents: Record<string, number> = {
	image: ids['foto-gatto'],
	'image of a disappearance': ids['foto-saracinesca'],
	text: ids.testimonianza,
	link: ids.collegamento
};
const prefixes = {
	it: { artworks: '/it/opere', documents: '/it/documenti' },
	en: { artworks: '/en/artworks', documents: '/en/documents' }
};

async function axe(page: Page, label: string) {
	const results = await new AxeBuilder({ page }).withTags(WCAG_22_AA).analyze();
	expect(results.violations, label).toEqual([]);
}

async function signInAs(page: Page, email: string) {
	await page.goto('/en/sign-in');
	await page.getByLabel('Email address').fill(email);
	await page.getByRole('button', { name: 'Send the code' }).click();
	await page.getByLabel('Code', { exact: true }).fill('123456');
	await page.getByRole('main').getByRole('button', { name: 'Sign in' }).click();
	await page.waitForURL((url) => !url.pathname.includes('sign-in'));
	await hydrated(page);
}

for (const [language, paths] of Object.entries(prefixes)) {
	test(`AC 37: ${language} Artwork pages pass axe in every state`, async ({ page }) => {
		for (const [state, id] of Object.entries(artworkStates)) {
			const response = await page.goto(`${paths.artworks}/${id}`);
			expect(response?.status(), state).toBe(200);
			await axe(page, `${language} ${state}`);
		}
		const withdrawn = await page.goto(`${paths.artworks}/${WITHDRAWN}`);
		expect(withdrawn?.status()).toBe(410);
		await axe(page, `${language} withdrawn`);
	});

	test(`AC 37: ${language} Documentation item pages pass axe`, async ({ page }) => {
		for (const [state, id] of Object.entries(documents)) {
			expect((await page.goto(`${paths.documents}/${id}`))?.status(), state).toBe(200);
			await axe(page, `${language} ${state}`);
		}
	});
}

test('AC 37: a Moderator sees a withdrawn Artwork under its banner, with axe passing', async ({
	page
}) => {
	await signInAs(page, 'moderatrice@example.org');
	await page.goto(`/en/artworks/${ids.gatto}`);
	await expect(page.getByRole('note')).toContainText('Withdrawn on May 4, 2026');
	await expect(page.getByRole('heading', { level: 1 })).toHaveText('Il gatto che legge');
	await page.goto(`/en/artworks/${ids.onda}`);
	await expect(page.getByText('(Redacted on May 4, 2026)')).toBeVisible();
	await axe(page, 'moderator');
});

test('AC 16 and 50: a missing or wrong slug answers 301; untitled is canonical at its id', async ({
	page
}) => {
	for (const path of [`/it/opere/${ids.gatto}`, `/it/opere/${ids.gatto}-vecchio-titolo`]) {
		const response = await page.request.get(path, { maxRedirects: 0 });
		expect(response.status()).toBe(301);
		expect(response.headers().location).toBe(`/it/opere/${ids.gatto}-il-gatto-che-legge`);
	}
	const untitled = await page.request.get(`/en/artworks/${ids['senza-titolo']}`, {
		maxRedirects: 0
	});
	expect(untitled.status()).toBe(200);
	const merged = await page.request.get(`/en/artworks/${MERGED}`, { maxRedirects: 0 });
	expect(merged.status()).toBe(301);
	expect(merged.headers().location).toBe(`/en/artworks/${ids.gatto}-il-gatto-che-legge`);
	const otherKind = await page.request.get(`/en/artists/${ids.gatto}`, { maxRedirects: 0 });
	expect(otherKind.status()).toBe(404);
});

test('AC 1 and 14: Untitled in the header, the browser title, and lists; retired types keep their label', async ({
	page
}) => {
	await page.goto(`/en/artworks/${ids['senza-titolo']}`);
	await expect(page.getByRole('heading', { level: 1 })).toHaveText('Untitled');
	await expect(page).toHaveTitle(/^Untitled — /);
	// `stencil` is retired in this Instance's vocabulary, and still shows its label.
	await expect(page.locator('header .types')).toHaveText('Stencil');
	await page.goto(`/en/artworks/${ids.fiore}`);
	const sameSurface = page
		.getByRole('heading', { name: 'On the same surface' })
		.locator('xpath=following-sibling::ul[1]');
	await expect(sameSurface.getByRole('link', { name: 'Untitled' })).toBeVisible();
});

test('AC 30: Condition, Evidence level, and Attribution are given in words', async ({ page }) => {
	await page.goto(`/en/artworks/${ids['senza-titolo']}`);
	const header = page.locator('article header');
	// The spec's presentation example, in this UI language's date format.
	await expect(header).toContainText('Missing · since c. 2019 · last documented Mar 3, 2018');
	await expect(header).toContainText('reported · no sources cited');
	await expect(header).toContainText('Nebbia Finta — probable attribution');
	await expect(header.locator('svg[data-sign="disappeared"]')).toHaveAttribute(
		'aria-hidden',
		'true'
	);
	await page.goto(`/en/artworks/${ids.mani}`);
	await expect(page.locator('article header')).toContainText(
		'Disputed attribution: Lupo Inventato or Ombra Supposta'
	);
	await page.goto(`/en/artworks/${ids.occhio}`);
	await expect(page.locator('article header')).toContainText('Unknown artist');
	// Grayscale: the page still says everything without its colours.
	await page.addStyleTag({ content: 'html { filter: grayscale(1) }' });
	await expect(page.locator('article header')).toContainText('Intact · since 2023');
});

test('AC 22 and 36: the Timeline is an ordered list with three dates per event', async ({
	page
}) => {
	await page.goto(`/en/artworks/${ids.gatto}`);
	const timeline = page.locator('ol.timeline');
	const entries = timeline.locator(':scope > li');
	await expect(entries).toHaveCount(4);
	const creation = entries.nth(0);
	await expect(creation).toContainText('Creation');
	for (const label of ['Observed', 'Submitted', 'Approved']) {
		await expect(creation.locator('dt', { hasText: label })).toHaveCount(1);
	}
	await expect(creation.getByRole('link', { name: 'Revision that added it' })).toHaveAttribute(
		'href',
		/\/en\/artworks\/\d+-il-gatto-che-legge\/revisions#revision-\d+$/
	);
	const item = entries.filter({ hasText: 'Documentation: image' });
	await expect(item.locator('dt')).toHaveText(['Observed']);
	await expect(timeline).not.toContainText('Contributrice');
});

test('AC 22: an image item on the Timeline shows its thumbnail, a text item its incipit', async ({
	page
}) => {
	await page.goto(`/en/artworks/${ids.gatto}`);
	const image = page.locator('ol.timeline > li').filter({ hasText: 'Documentation: image' });
	const thumbnail = image.getByRole('link').locator('img');
	await expect(thumbnail).toHaveAttribute('src', /^\/api\/media\/.+\/thumbnail$/);
	await expect(thumbnail).toHaveAttribute('alt', /^Immagine fittizia/);
	await expect(image.locator('dt')).toHaveText(['Observed']);
	await expect(image).not.toContainText('Credit');

	await page.goto(`/en/artworks/${ids.scritta}`);
	const text = page.locator('ol.timeline > li').filter({ hasText: 'Documentation: text' });
	await expect(text.locator('.incipit')).toHaveText(
		'Testimonianza fittizia: la scritta era ancora leggibile.'
	);
	await expect(text.locator('.incipit')).toHaveAttribute('lang', 'it');
	await expect(text.locator('img')).toHaveCount(0);
	const link = page.locator('ol.timeline > li').filter({ hasText: 'Documentation: link' });
	await expect(link.locator('img, .incipit')).toHaveCount(0);
});

test('AC 23, 32, and 36: each image has its alt text, credit, licence scope, and date', async ({
	page
}) => {
	await page.goto(`/en/artworks/${ids.gatto}`);
	const figure = page.locator('.gallery figure').first();
	await expect(figure.locator('img')).toHaveAttribute('alt', /^Immagine fittizia/);
	await expect(figure.locator('figcaption')).toContainText('Apr 12, 2024');
	await expect(figure.locator('figcaption')).toContainText('Credit: Fotografa fittizia');
	await expect(figure.locator('figcaption')).toContainText(
		'Licence: CC BY-SA 4.0, which covers the file only, not the artwork'
	);
	for (const image of await page.locator('img').all()) {
		expect(await image.getAttribute('alt')).toBeTruthy();
	}
});

test('AC 28: a Documentation item page shows its dates, rights, and what it documents', async ({
	page
}) => {
	await page.goto(`/en/documents/${ids['foto-saracinesca']}`);
	const details = page.locator('article dl');
	for (const label of ['Observed date', 'Submitted', 'Approved']) {
		await expect(details.locator('dt', { hasText: label })).toHaveCount(1);
	}
	await expect(details).toContainText('own work of the creator');
	await expect(details).toContainText('covers the file only');
	await expect(details).toContainText('Saracinesca fittizia di via Inventata 7');
	await expect(page.getByRole('link', { name: 'Fiore fittizio' })).toBeVisible();
});

test('AC 33: without a map, the place is stated in words', async ({ page }) => {
	await page.goto(`/en/artworks/${ids.onda}`);
	const where = page.locator('.where');
	await expect(where).toContainText('approximate location, within 150 m');
	await expect(where.getByRole('link', { name: 'Open in a maps app' })).toHaveAttribute(
		'href',
		/^geo:41\.905000,12\.510000;u=150$/
	);
	await page.goto(`/en/artworks/${ids.gatto}`);
	await expect(page.locator('.where')).toContainText('Ex deposito dei tram fittizio');
	await expect(page.locator('.where')).toContainText('Quartiere Immaginario, Rione di Prova');
	await expect(page.locator('canvas')).toHaveCount(0);
});

test('AC 34: archive content keeps its own language on an English page', async ({ page }) => {
	await page.goto(`/en/artworks/${ids.gatto}`);
	await expect(page.locator('html')).toHaveAttribute('lang', 'en');
	await expect(page.locator('h1 [lang="it"]')).toHaveText('Il gatto che legge');
	await expect(page.locator('#description ~ p[lang="it"]').first()).toContainText('Opera fittizia');
});

test('a redacted description shows the neutral placeholder', async ({ page }) => {
	await page.goto(`/en/artworks/${ids.onda}`);
	await expect(page.locator('section[aria-labelledby="description"]')).toContainText(
		'removed for legal reasons'
	);
});

test('AC 31: every control of an Artwork page is keyboard-operable with visible focus', async ({
	page
}) => {
	await page.goto(`/en/artworks/${ids.gatto}`);
	await expect(page.locator('header.site-header.enhanced')).toBeAttached();
	const links = await page.locator('article a').count();
	let reached = 0;
	for (let step = 0; step < 120 && reached < links; step++) {
		await page.keyboard.press('Tab');
		const focused = await page.evaluate(() => {
			const element = document.activeElement as HTMLElement | null;
			if (!element || element === document.body) return null;
			const style = getComputedStyle(element);
			return {
				inArticle: !!element.closest('article'),
				outline: style.outlineStyle !== 'none' && parseFloat(style.outlineWidth) >= 2
			};
		});
		if (focused === null) break;
		if (!focused.inArticle) continue;
		expect(focused.outline).toBe(true);
		reached++;
	}
	expect(reached).toBe(links);
});
