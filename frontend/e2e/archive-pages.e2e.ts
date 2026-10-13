/**
 * Archive records spec, the other record pages, the indexes, and `/revisions`, against
 * the stand-in API's answers over the fictional dataset: criteria 21, 25, 26, and 37.
 * Criterion 35 is the build's missing-key check.
 */
import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';
import { readFileSync } from 'node:fs';

const ids: Record<string, number> = JSON.parse(
	readFileSync(new URL('fixtures/archive/ids.json', import.meta.url), 'utf8')
);
const WCAG_22_AA = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];

const segments = {
	it: {
		artists: '/it/artisti',
		locations: '/it/superfici',
		sites: '/it/luoghi',
		areas: '/it/aree',
		series: '/it/serie',
		sources: '/it/fonti',
		artworks: '/it/opere',
		documents: '/it/documenti',
		revisions: 'revisioni'
	},
	en: {
		artists: '/en/artists',
		locations: '/en/locations',
		sites: '/en/sites',
		areas: '/en/areas',
		series: '/en/series',
		sources: '/en/sources',
		artworks: '/en/artworks',
		documents: '/en/documents',
		revisions: 'revisions'
	}
};
type Segment = Exclude<keyof (typeof segments)['en'], 'revisions'>;

/** One record of each kind, by its key in the dataset. */
const records: [Segment, string][] = [
	['artists', 'nebbia'],
	['artists', 'collettivo'],
	['locations', 'cortile'],
	['locations', 'saracinesca'],
	['locations', 'facciata'],
	['sites', 'deposito'],
	['areas', 'quartiere'],
	['series', 'gatti'],
	['sources', 'fanzine'],
	['sources', 'intervista']
];

async function axe(page: Page, label: string) {
	const results = await new AxeBuilder({ page }).withTags(WCAG_22_AA).analyze();
	expect(results.violations, label).toEqual([]);
}

for (const [language, paths] of Object.entries(segments)) {
	test(`AC 37: ${language} record pages, indexes, and revisions pass axe`, async ({ page }) => {
		for (const [segment, key] of records) {
			const response = await page.goto(`${paths[segment]}/${ids[key]}`);
			expect(response?.status(), key).toBe(200);
			await axe(page, `${language} ${key}`);
			await page.goto(`${page.url()}/${paths.revisions}`);
			await axe(page, `${language} ${key} revisions`);
		}
		for (const segment of ['artists', 'sites', 'areas', 'series'] as const) {
			expect((await page.goto(paths[segment]))?.status()).toBe(200);
			await axe(page, `${language} ${segment} index`);
		}
		for (const key of ['gatto', 'onda', 'foto-gatto']) {
			const segment = key.startsWith('foto') ? 'documents' : 'artworks';
			await page.goto(`${paths[segment]}/${ids[key]}/${paths.revisions}`);
			await axe(page, `${language} ${key} revisions`);
		}
		expect((await page.goto(`${paths.artists}/9001`))?.status()).toBe(410);
	});
}

test('AC 25: every record page has Report and a link to its revisions', async ({ page }) => {
	const pages: [Segment, string][] = [
		...records,
		['artworks', 'gatto'],
		['documents', 'foto-gatto']
	];
	for (const [segment, key] of pages) {
		await page.goto(`${segments.en[segment]}/${ids[key]}`);
		const actions = page.locator('section.actions');
		await expect(actions.getByRole('link', { name: 'Report this content' })).toHaveAttribute(
			'href',
			/^\/en\/report\?object=[a-z_]+%3A\d+$/
		);
		await actions.getByRole('link', { name: 'Revision history' }).click();
		await expect(page).toHaveURL(/\/revisions$/);
		await expect(page.getByRole('heading', { level: 1 })).toContainText('Revision history');
	}
});

test('AC 26: revisions name the Submitter without a link, list changes, and hide the Moderator', async ({
	page
}) => {
	await page.goto(`/en/artworks/${ids.gatto}-il-gatto-che-legge/revisions`);
	const revisions = page.locator('ol.revisions > li');
	await expect(revisions).toHaveCount(2);
	await expect(revisions.first()).toHaveAttribute('id', /^revision-\d+$/);
	await expect(revisions.first()).toContainText('Contributed by Contributrice fittizia');
	await expect(revisions.first().getByRole('link', { name: /Contributrice/ })).toHaveCount(0);
	await expect(page.locator('main')).not.toContainText('Moderatore');
	// A later change shows its previous and new values.
	const description = revisions.first().locator('li', { hasText: 'Description changed' });
	await expect(description.locator('dt')).toHaveText(['Before', 'After']);
	await expect(description).toContainText('firmato in basso');
	// The first Revision lists the initial values, with linked records by name.
	await expect(revisions.last()).toContainText('Added to Attributions');
	await expect(
		revisions.last().getByRole('link', { name: 'Nebbia Finta', exact: true })
	).toBeVisible();
	await expect(
		revisions.first().getByRole('link', { name: 'Report this revision' })
	).toHaveAttribute('href', /report\?object=artwork%3A\d+%23revision-\d+$/);
});

test('AC 26: a redacted value is hidden on revisions', async ({ page }) => {
	await page.goto(`/en/artworks/${ids.onda}/revisions`);
	const description = page.locator('ul.changes > li', { hasText: 'Description' });
	await expect(description).toContainText('removed for legal reasons');
	await expect(page.locator('main')).not.toContainText('posizione nota solo');
});

test('AC 21: revisions show change lists, never a Timeline', async ({ page }) => {
	await page.goto(`/en/artworks/${ids.gatto}/revisions`);
	await expect(page.getByRole('heading', { name: 'Timeline' })).toHaveCount(0);
	await expect(page.locator('ol.timeline')).toHaveCount(0);
});

test('the Location page lists its stratigraphy, most recent first, and disappearances', async ({
	page
}) => {
	await page.goto(`/en/locations/${ids.cortile}`);
	const strata = page.locator('section[aria-labelledby="stratigraphy"] .cards > li > a');
	await expect(strata).toHaveText(['Il gatto che legge', 'Ritratto fittizio']);
	await page.goto(`/en/locations/${ids.saracinesca}`);
	await expect(page.locator('section[aria-labelledby="disappearances"] img')).toHaveAttribute(
		'alt',
		/saracinesca nuova/
	);
});

test('the Artist page shows memberships both ways and attributed Artworks', async ({ page }) => {
	await page.goto(`/en/artists/${ids.collettivo}`);
	await expect(page.locator('section[aria-labelledby="members"]')).toContainText(
		'Lupo Inventato (2016 – 2019)'
	);
	await page.goto(`/en/artists/${ids.lupo}`);
	await expect(page.locator('section[aria-labelledby="member-of"]')).toContainText(
		'Collettivo Vernice Assente'
	);
	await expect(page.locator('section[aria-labelledby="artworks"]')).toContainText(
		'disputed attribution'
	);
	await expect(page.locator('article img')).toHaveCount(0);
});

test('an index lists by name and a Source renders its citation', async ({ page }) => {
	await page.goto('/it/artisti');
	await expect(page.locator('ul.index a')).toHaveText([
		'Collettivo Vernice Assente',
		'Lupo Inventato',
		'Nebbia Finta',
		'Ombra Supposta'
	]);
	await page.goto(`/en/sources/${ids.fanzine}`);
	await expect(page.locator('.citation')).toHaveText(
		'Redazione immaginaria, Muri che parlano, n. 3, Fanzine fittizia, 2019'
	);
	await expect(page.locator('section[aria-labelledby="cited-by"]')).toContainText(
		'Il gatto che legge'
	);
});
