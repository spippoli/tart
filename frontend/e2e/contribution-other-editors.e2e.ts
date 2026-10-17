import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';
import { createHash } from 'node:crypto';
import { serveStyles } from './map-style';

/**
 * The editors of the other record kinds (Contribution and moderation spec, Other editors;
 * acceptance criteria 45 to 50): an edit of a Location and of an Artwork, a new Area, and
 * documentation or a History event added to an Artwork. The stand-in API keeps the drafts
 * and answers the record an edit starts from (e2e/mock-api.ts); the real API's own tests
 * cover what approval writes. Every record here is fictional.
 */

const MOCK = 'http://localhost:8795';
const BASE = 'http://localhost:4273';
const WCAG_22_AA = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];
const HEADERS = { 'x-tart-request': '1', 'x-tart-client-ip': '127.0.0.1', 'x-mock-editor': '1' };

type Language = 'en' | 'it';
const path = (language: Language, id: number) =>
	language === 'en' ? `/en/contributions/${id}/edit` : `/it/contributi/${id}/modifica`;

function address(info: { project: { name: string }; title: string }) {
	const slug = createHash('sha1').update(info.title).digest('hex').slice(0, 12);
	return `persona-altri-${info.project.name}-${slug}@example.org`;
}

async function serveApi(page: Page) {
	await serveStyles(page);
	await page.route(
		/\/api\/(contributions|contribution\/duplicates|media|discovery|archive)(\/|\?|$)/,
		async (route) => {
			const url = new URL(route.request().url());
			try {
				const response = await route.fetch({
					url: MOCK + url.pathname + url.search,
					headers: { ...route.request().headers(), 'x-tart-client-ip': '127.0.0.1' }
				});
				await route.fulfill({ response });
			} catch {
				// The page navigated away while the request was in flight.
			}
		}
	);
}

async function startDraft(
	page: Page,
	info: { project: { name: string }; title: string },
	body: Record<string, unknown>,
	content?: unknown
): Promise<number> {
	await page
		.context()
		.addCookies([{ name: 'tart_session', value: encodeURIComponent(address(info)), url: BASE }]);
	await serveApi(page);
	const created = await page.request.post(`${MOCK}/api/contributions`, {
		headers: HEADERS,
		data: body
	});
	const { id } = await created.json();
	if (content !== undefined) {
		await page.request.put(`${MOCK}/api/contributions/${id}/working-copy`, {
			headers: HEADERS,
			data: { content }
		});
	}
	return id;
}

async function open(page: Page, id: number, language: Language = 'en') {
	await page.goto(path(language, id));
	await expect(page.locator('.editor')).toBeVisible();
	// The status text is server-rendered; the steps and buttons work once the page has hydrated.
	await expect(page.locator('.editor[data-hydrated="true"]')).toBeVisible();
}

async function axe(page: Page, label: string) {
	const results = await new AxeBuilder({ page }).withTags(WCAG_22_AA).analyze();
	expect(results.violations, label).toEqual([]);
}

const steps = (page: Page) => page.getByRole('navigation', { name: /Steps of the form|Passaggi/ });

test.describe('AC 48: a Location geometry edit', () => {
	test('shows the number of Artworks and offers the Merge editor near another Location', async ({
		page
	}, info) => {
		const id = await startDraft(page, info, { target_kind: 'location', target_id: 201 });
		await open(page, id);
		await expect(steps(page).getByRole('button')).toHaveCount(3);
		await expect(page.locator('[data-location-artworks]')).toContainText(
			'This Location carries 3 Artworks: the change applies to all of them.'
		);
		await expect(page.getByText('Current').first()).toBeVisible();
		await page.getByRole('button', { name: 'Edit Geometry' }).click();
		await page.locator('#record-field-geometry-coordinates').fill('41.8955, 12.4823');
		await page.getByRole('button', { name: 'Use these coordinates' }).click();
		const merge = page.locator('[data-location-merge]');
		await expect(merge).toBeVisible();
		await expect(merge.getByRole('link')).toHaveAttribute('href', /merge\?source=201&into=200/);
		await axe(page, 'a Location edit with a proposed geometry');
	});

	for (const language of ['en', 'it'] as const) {
		test(`the edit is accessible (${language})`, async ({ page }, info) => {
			const id = await startDraft(page, info, { target_kind: 'location', target_id: 201 });
			await open(page, id, language);
			await axe(page, `the first step of a Location edit (${language})`);
		});
	}
});

test.describe('AC 45: an edit of an Artwork', () => {
	test('lists the fields as current against proposed, and refuses an empty edit', async ({
		page
	}, info) => {
		const id = await startDraft(page, info, { target_kind: 'artwork', target_id: 9 });
		await open(page, id);
		await expect(page.getByText('Gatto di prova').first()).toBeVisible();
		await page.getByRole('button', { name: 'Edit Title' }).click();
		await expect(page.getByText('Proposed · not public until approved').first()).toBeVisible();
		await page.getByRole('button', { name: 'Cancel the change to Title' }).click();
		await steps(page).getByRole('button').last().click();
		await page.getByRole('button', { name: 'Submit for review' }).click();
		await expect(page.getByRole('alert')).toContainText('Nothing is changed yet');
		await axe(page, 'the error summary of an empty edit');
	});

	test('creates a Series from the Artwork field', async ({ page }, info) => {
		const id = await startDraft(page, info, { target_kind: 'artwork', target_id: 9 });
		await open(page, id);
		await page.getByLabel('Add to a Series that exists').fill('Cani');
		await page.getByRole('button', { name: 'Create a new Series with this name' }).click();
		await expect(page.getByRole('group', { name: 'New Series' })).toBeVisible();
		await expect(page.getByText('This Artwork will be its first member.')).toBeVisible();
	});
});

test.describe('AC 47: a new Area', () => {
	test('is drawn as a polygon with a text readout, in both languages', async ({ page }, info) => {
		const id = await startDraft(page, info, { target_kind: 'area' });
		await open(page, id);
		await expect(steps(page).getByRole('button')).toHaveCount(4);
		await steps(page).getByRole('button').nth(1).click();
		await expect(page.getByRole('status').filter({ hasText: 'Nothing drawn yet' })).toBeVisible();
		await expect(page.locator('#record-field-geometry-coordinates')).toHaveCount(0);
		await axe(page, 'the Polygon step');
		await open(page, id, 'it');
		await expect(steps(page).getByRole('button').first()).toContainText('Nome e descrizione');
		await axe(page, 'the first step of a new Area (it)');
	});
});

test.describe('Add documentation and History events', () => {
	const copy = (flavour: string, report = false) => ({
		operations: [],
		editor: { flavour, target: { id: 9, title: 'Gatto di prova' }, event: { report } }
	});

	test('add documentation asks whether the files show a change', async ({ page }, info) => {
		const id = await startDraft(
			page,
			info,
			{ target_kind: 'artwork', target_id: 9 },
			copy('documentation')
		);
		await open(page, id);
		await expect(steps(page).getByRole('button')).toHaveCount(4);
		await steps(page).getByRole('button').nth(1).click();
		await page.getByRole('radio', { name: /Yes: add a History event/ }).check();
		await expect(page.getByRole('group', { name: 'Visible change' })).toBeVisible();
		await expect(page.getByRole('group', { name: 'Other facts' })).toHaveCount(0);
		await axe(page, 'the change step');
	});

	test('a History event reached from an edit offers the Other facts too', async ({
		page
	}, info) => {
		const id = await startDraft(
			page,
			info,
			{ target_kind: 'artwork', target_id: 9 },
			copy('event', true)
		);
		await open(page, id);
		await expect(steps(page).getByRole('button')).toHaveCount(3);
		await expect(page.getByRole('group', { name: 'Disappearance' })).toBeVisible();
		await expect(page.getByRole('group', { name: 'Other facts' })).toHaveCount(0);
		await axe(page, 'the event step');
	});

	test('the events of "Propose an edit" include the Other facts', async ({ page }, info) => {
		const id = await startDraft(
			page,
			info,
			{ target_kind: 'artwork', target_id: 9 },
			copy('event', false)
		);
		await open(page, id);
		await expect(page.getByRole('group', { name: 'Other facts' })).toBeVisible();
	});
});
