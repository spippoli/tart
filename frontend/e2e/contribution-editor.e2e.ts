import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';
import { createHash } from 'node:crypto';
import { serveStyles } from './map-style';

/**
 * The editor of a new Artwork (Contribution and moderation spec, Submission form). The
 * stand-in API keeps the drafts, answers the uploads and the duplicate warning, and
 * refuses a few things as the real one would (e2e/mock-api.ts); the real API's own tests
 * cover validation, autosave, and the lifecycle. Every record here is fictional.
 */

const MOCK = 'http://localhost:8795';
const BASE = 'http://localhost:4273';
const WCAG_22_AA = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];
const HEADERS = { 'x-tart-request': '1', 'x-tart-client-ip': '127.0.0.1' };

type Language = 'en' | 'it';
const WORDS = {
	en: {
		path: (id: number) => `/en/contributions/${id}/edit`,
		steps: 'Steps of the form',
		stepNames: [
			'Location',
			'Documentation',
			'The Artwork',
			'Attribution',
			'Creation date',
			'Sources',
			'Review and submit'
		],
		heading: (number: number, name: string) => `Step ${number} of 7: ${name}`,
		toComplete: 'to complete',
		toFix: 'to fix',
		complete: 'complete',
		submit: 'Submit for review'
	},
	it: {
		path: (id: number) => `/it/contributi/${id}/modifica`,
		steps: 'Passaggi del modulo',
		stepNames: [
			'Posizione',
			'Documentazione',
			"L'opera",
			'Attribuzione',
			'Data di creazione',
			'Fonti',
			'Riepilogo e invio'
		],
		heading: (number: number, name: string) => `Passaggio ${number} di 7: ${name}`,
		toComplete: 'da completare',
		toFix: 'da correggere',
		complete: 'completo',
		submit: 'Invia alla revisione'
	}
} as const;

/** An address of its own for each test and project, since the stand-in API keeps state. */
function address(info: { project: { name: string }; title: string }, extra = '') {
	const slug = createHash('sha1').update(info.title).digest('hex').slice(0, 12);
	return `persona${extra}-${info.project.name}-${slug}@example.org`;
}

/** What the browser asks of `/api/*`, answered by the stand-in API on its own port. */
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

/** A fictional signed-in User with a new draft of an Artwork; returns the draft's id. */
async function startDraft(
	page: Page,
	info: { project: { name: string }; title: string },
	options: { extra?: string; content?: unknown } = {}
): Promise<number> {
	const email = address(info, options.extra);
	await page
		.context()
		.addCookies([{ name: 'tart_session', value: encodeURIComponent(email), url: BASE }]);
	await serveApi(page);
	const created = await page.request.post(`${MOCK}/api/contributions`, {
		headers: HEADERS,
		data: { target_kind: 'artwork' }
	});
	const { id } = await created.json();
	if (options.content !== undefined) {
		await page.request.put(`${MOCK}/api/contributions/${id}/working-copy`, {
			headers: HEADERS,
			data: { content: options.content }
		});
	}
	return id;
}

/** The working copy of a complete fictional Artwork, as the editor writes it. */
function complete(overrides: Record<string, unknown> = {}) {
	return {
		operations: [
			{
				op: 'create',
				ref: 'location',
				kind: 'location',
				record: {
					geometry: { type: 'Point', coordinates: [12.5, 41.91] },
					surface_type: 'wall',
					approximate: false,
					uncertainty_radius: null,
					place_description: 'Muro di prova'
				}
			},
			{
				op: 'create',
				ref: 'artist-1',
				kind: 'artist',
				record: { name: 'Artista Nuovo', kind: 'individual' }
			},
			{
				op: 'create',
				ref: 'source-2',
				kind: 'source',
				record: { title: 'Libro fittizio', author: null, publication: null, url: null, note: null }
			},
			{
				op: 'create',
				ref: 'doc-3',
				kind: 'documentation_item',
				record: {
					medium: 'link',
					observed_date: {
						precision: 'year',
						qualifier: 'exact',
						first: '2020-01-01',
						second: null
					},
					artworks: [{ new: 'artwork' }],
					url: 'https://example.org/pagina'
				}
			},
			{
				op: 'create',
				ref: 'artwork',
				kind: 'artwork',
				record: {
					location: { new: 'location' },
					expression_types: ['mural'],
					title: 'Il gatto di prova',
					description: 'Un gatto fittizio.',
					attributions: [
						{
							artist: { new: 'artist-1' },
							certainty: 'probable',
							alias: null,
							note: null,
							citations: [{ new: 'source-2' }]
						}
					],
					history_events: [
						{
							id: { new: 'created' },
							type: 'created',
							observed_date: {
								precision: 'year',
								qualifier: 'circa',
								first: '2019-01-01',
								second: null
							},
							citations: []
						}
					],
					series: [],
					sources: [{ new: 'source-2' }]
				}
			}
		],
		initial_condition: 'intact',
		editor: {
			untitled: false,
			attributed: true,
			confirmed_key: null,
			counter: 3,
			labels: {},
			files: {},
			suggested: []
		},
		...overrides
	};
}

const stepButton = (page: Page, language: Language, index: number) =>
	page.getByRole('navigation', { name: WORDS[language].steps }).getByRole('button', {
		name: new RegExp(`^${index + 1}\\. ${WORDS[language].stepNames[index]}`)
	});

const heading = (page: Page, language: Language, index: number) =>
	page.getByRole('heading', {
		level: 2,
		name: WORDS[language].heading(index + 1, WORDS[language].stepNames[index])
	});

async function open(page: Page, id: number, language: Language = 'en') {
	await page.goto(WORDS[language].path(id));
	await expect(page.locator('.editor')).toBeVisible();
	// The stepper works once the page has hydrated.
	await expect(
		page.getByText(/^(Changes are saved|Saved automatically|Le modifiche|Salvato)/)
	).toBeVisible();
}

async function axe(page: Page, label: string) {
	const results = await new AxeBuilder({ page }).withTags(WCAG_22_AA).analyze();
	expect(results.violations, label).toEqual([]);
}

async function savedCopy(page: Page, id: number) {
	const response = await page.request.get(`${MOCK}/api/contributions/${id}`);
	return (await response.json()).working_copy;
}

test.describe('AC 12: the steps are reached in any order and nothing is validated on the way', () => {
	for (const language of ['en', 'it'] as const) {
		test(`every step opens from the step list, last to first (${language})`, async ({
			page
		}, info) => {
			const id = await startDraft(page, info);
			await open(page, id, language);
			for (const index of [6, 5, 4, 3, 2, 1, 0]) {
				await stepButton(page, language, index).click();
				await expect(heading(page, language, index)).toBeVisible();
				await expect(heading(page, language, index)).toBeFocused();
				await expect(stepButton(page, language, index)).toHaveAttribute('aria-current', 'step');
			}
			// Typing in a later step first, then leaving the earlier ones empty, is allowed.
			await stepButton(page, language, 2).click();
			await page.locator('#editor-title').fill('Il gatto di prova');
			await stepButton(page, language, 0).click();
			await expect(page.locator('#editor-summary')).toHaveCount(0);
			await expect(
				page.locator('.step-button .state', { hasText: WORDS[language].toFix })
			).toHaveCount(0);
		});
	}

	test('the previous and next buttons walk the same list', async ({ page }, info) => {
		const id = await startDraft(page, info);
		await open(page, id);
		await expect(page.getByRole('button', { name: 'Previous step' })).toBeDisabled();
		await page.getByRole('button', { name: 'Next step' }).click();
		await expect(heading(page, 'en', 1)).toBeVisible();
		await page.getByRole('button', { name: 'Previous step' }).click();
		await expect(heading(page, 'en', 0)).toBeVisible();
	});

	test('each step state is a word: to complete, complete', async ({ page }, info) => {
		const id = await startDraft(page, info);
		await open(page, id);
		await expect(stepButton(page, 'en', 0)).toContainText('to complete');
		// An optional step with nothing in it asks nothing.
		await expect(stepButton(page, 'en', 4)).toContainText('complete');
		await expect(stepButton(page, 'en', 4)).not.toContainText('to complete');
	});
});

test.describe('AC 13: a failed submit lists every error, linked to its field', () => {
	for (const language of ['en', 'it'] as const) {
		test(`the summary takes focus, and each link reaches a field that names its error (${language})`, async ({
			page
		}, info) => {
			const id = await startDraft(page, info);
			await open(page, id, language);
			await stepButton(page, language, 6).click();
			await page.getByRole('button', { name: WORDS[language].submit }).click();

			const summary = page.locator('#editor-summary');
			await expect(summary).toBeFocused();
			await expect(summary).toHaveAttribute('role', 'alert');
			await expect(summary.getByRole('link')).toHaveCount(7);

			// Location: the field is the coordinates field, invalid and described by its error.
			await summary.getByRole('link').first().click();
			const coordinates = page.locator('#editor-location-coordinates');
			await expect(heading(page, language, 0)).toBeVisible();
			await expect(coordinates).toBeFocused();
			await expect(coordinates).toHaveAttribute('aria-invalid', 'true');
			const described = await coordinates.getAttribute('aria-describedby');
			expect(described).toContain('editor-location-coordinates-message');
			await expect(page.locator('#editor-location-coordinates-message')).not.toBeEmpty();

			// The step is "to fix", in words, not by colour.
			await expect(stepButton(page, language, 0)).toContainText(WORDS[language].toFix);
			await expect(stepButton(page, language, 1)).toContainText(WORDS[language].toFix);
			await expect(stepButton(page, language, 5)).toContainText(WORDS[language].complete);
		});
	}

	test('a field error is text bound to the field with aria-describedby and aria-invalid', async ({
		page
	}, info) => {
		const id = await startDraft(page, info);
		await open(page, id);
		await stepButton(page, 'en', 6).click();
		await page.getByRole('button', { name: 'Submit for review' }).click();
		await page
			.locator('#editor-summary')
			.getByRole('link', { name: /Choose the state/ })
			.click();
		const condition = page.locator('#editor-condition');
		await expect(condition).toBeFocused();
		await expect(condition).toHaveAttribute('aria-invalid', 'true');
		const error = page.locator('#editor-condition-error');
		await expect(error).toContainText('Choose the state the Artwork was in');
		await expect(condition).toHaveAttribute('aria-describedby', /editor-condition-error/);

		await page
			.locator('#editor-summary')
			.getByRole('link', { name: /Enter a title/ })
			.click();
		await expect(page.locator('#editor-title')).toBeFocused();
		await expect(page.locator('#editor-title')).toHaveAttribute('aria-invalid', 'true');
	});

	test('an error goes away as the field is fixed, and none appears before a submit', async ({
		page
	}, info) => {
		const id = await startDraft(page, info);
		await open(page, id);
		await stepButton(page, 'en', 2).click();
		await page.locator('#editor-title').focus();
		await page.locator('#editor-title').blur();
		await expect(page.locator('#editor-title-error')).toHaveCount(0);
		await stepButton(page, 'en', 6).click();
		await page.getByRole('button', { name: 'Submit for review' }).click();
		await stepButton(page, 'en', 2).click();
		await expect(page.locator('#editor-title-error')).toBeVisible();
		await page.locator('#editor-title').fill('Il gatto di prova');
		await expect(page.locator('#editor-title-error')).toHaveCount(0);
	});
});

test.describe('AC 18: the file metadata only suggests', () => {
	test('the capture date prefills the Observed date with a notice, and the position fills a field without placing anything', async ({
		page
	}, info) => {
		const id = await startDraft(page, info);
		await open(page, id);
		await stepButton(page, 'en', 1).click();
		await page.locator('#editor-documentation-add').setInputFiles({
			name: 'foto-gps.jpg',
			mimeType: 'image/jpeg',
			buffer: Buffer.from('fictional image')
		});
		await expect(page.getByText('File ready.')).toBeVisible({ timeout: 10_000 });
		await expect(page.getByText('This date is a suggestion, read from the file')).toBeVisible();
		await expect(page.getByLabel('Date, or start of a range')).toHaveValue('2024-05-17');

		await stepButton(page, 'en', 0).click();
		const coordinates = page.locator('#editor-location-coordinates');
		await expect(coordinates).toHaveValue('41.895500, 12.482300');
		await expect(page.getByText('This position comes from the photo you added')).toBeVisible();
		// Nothing is placed: the position is not confirmed and no Location is in the draft.
		await expect(page.locator('#editor-location-coordinates-message')).toBeEmpty();
		await expect(stepButton(page, 'en', 0)).toContainText('to complete');
		await expect
			.poll(async () => (await savedCopy(page, id))?.operations?.length)
			.toBeGreaterThan(0);
		const kinds = ((await savedCopy(page, id)).operations as { kind: string }[]).map(
			(each) => each.kind
		);
		expect(kinds).not.toContain('location');
		const artwork = (await savedCopy(page, id)).operations.at(-1).record;
		expect(artwork.location).toBeNull();

		// Only the person's own press places it.
		await page.getByRole('button', { name: 'Use these coordinates' }).click();
		await expect(page.locator('#editor-location-coordinates-message')).toContainText('41.8955 N');
	});
});

test.describe('AC 19: a geometry that cannot be kept is refused with a text message', () => {
	test('coordinates outside the boundary say so in words', async ({ page }, info) => {
		const id = await startDraft(page, info);
		await open(page, id);
		await page.locator('#editor-location-coordinates').fill('45.0, 9.0');
		await page.getByRole('button', { name: 'Use these coordinates' }).click();
		await expect(page.locator('#editor-location-coordinates-message')).toHaveText(
			'These coordinates are outside the area this archive covers.'
		);
		await expect(page.locator('#editor-location-coordinates')).toHaveAttribute(
			'aria-invalid',
			'true'
		);
	});

	test('a radius on anything but an approximate point is refused on submit, beside the radius', async ({
		page
	}, info) => {
		const id = await startDraft(page, info, { content: complete() });
		await open(page, id);
		await stepButton(page, 'en', 0).click();
		await page.locator('#editor-location-radius').fill('40');
		await stepButton(page, 'en', 6).click();
		await page.getByRole('button', { name: 'Submit for review' }).click();
		await page
			.locator('#editor-summary')
			.getByRole('link', { name: /An uncertainty radius is only for an approximate/ })
			.click();
		const radius = page.locator('#editor-location-radius');
		await expect(radius).toBeFocused();
		await expect(radius).toHaveAttribute('aria-invalid', 'true');
		await expect(page.locator('#editor-location-radius-error')).toContainText(
			'An uncertainty radius is only for an approximate position'
		);
		// Approximate, and a point: the same radius is kept.
		await page.getByLabel('Approximate').check();
		await expect(page.locator('#editor-location-radius-error')).toBeEmpty();
	});

	test('an area is drawn at the crosshair: too few vertices and a crossing outline are refused in words', async ({
		page
	}, info) => {
		test.skip(!!info.project.use.isMobile, 'The drawing tool is exercised once, at desktop width.');
		const id = await startDraft(page, info);
		await open(page, id);
		const map = page.locator('.map[data-state="ready"]');
		await expect(map).toBeVisible();
		await page.getByLabel('Area', { exact: true }).check();
		await page.getByLabel('Crosshair').check();
		const status = page.locator('.tool .status');

		// Two vertices are not an area.
		await page.getByRole('button', { name: 'Add vertex here' }).click();
		await page.getByRole('button', { name: 'Add vertex here' }).click();
		await page.getByRole('button', { name: 'Done' }).click();
		await expect(status).toHaveText('An area needs at least 3 vertices.');

		// A bow-tie: the corners of a square taken in a crossing order.
		await page.getByRole('button', { name: 'Undo last change' }).click();
		await page.getByRole('button', { name: 'Undo last change' }).click();
		await expect(page.getByText('Vertices: 0')).toBeVisible();
		const controls = page.getByRole('group', { name: 'Map controls' });
		const centre = async () => {
			let last = '';
			await expect
				.poll(
					async () => {
						const now = `${await map.getAttribute('data-lon')},${await map.getAttribute('data-lat')}`;
						const settled = now === last;
						last = now;
						return settled;
					},
					{ intervals: [400] }
				)
				.toBe(true);
		};
		const addHere = async () => {
			await centre();
			await page.getByRole('button', { name: 'Add vertex here' }).click();
		};
		const move = async (direction: 'east' | 'west' | 'north' | 'south') => {
			await controls.getByRole('button', { name: `Move ${direction}` }).click();
			await centre();
		};
		await addHere();
		await move('east');
		await addHere();
		await move('west');
		await move('south');
		await addHere();
		await move('east');
		await addHere();
		await page.getByRole('button', { name: 'Done' }).click();
		await expect(status).toHaveText(
			'The outline crosses itself. Move or delete a vertex so that it does not.'
		);
	});
});

test.describe('AC 21: a retired vocabulary entry is not offered', () => {
	test('the Expression types leave out the retired one', async ({ page }, info) => {
		const id = await startDraft(page, info);
		await open(page, id);
		await stepButton(page, 'en', 2).click();
		const types = page.getByRole('group', { name: 'Expression types' });
		await expect(types.getByLabel('Mural')).toBeVisible();
		await expect(types.getByLabel('Stencil')).toHaveCount(0);
		await stepButton(page, 'en', 0).click();
		await page.locator('#editor-location-coordinates').fill('41.91, 12.5');
		await page.getByRole('button', { name: 'Use these coordinates' }).click();
		const surface = page.getByLabel('Type of surface');
		await expect(surface.locator('option')).toHaveText([
			'Choose…',
			'Wall',
			'Building wall',
			'Shutter'
		]);
	});
});

test.describe('AC 22: the preview shows the proposal hatched and labelled', () => {
	test('a dashed outline, a hatched ground, the label in words, and no Condition shown yet', async ({
		page
	}, info) => {
		const id = await startDraft(page, info, { content: complete() });
		await open(page, id);
		await stepButton(page, 'en', 6).click();
		const proposal = page.getByRole('region', { name: 'Preview' });
		await expect(proposal).toContainText('Proposed · not public until approved');
		const style = await proposal.evaluate((element) => {
			const css = getComputedStyle(element);
			return { border: css.borderTopStyle, image: css.backgroundImage };
		});
		expect(style.border).toBe('dashed');
		expect(style.image).toContain('repeating-linear-gradient');
		// The Condition proposed is inside the proposal; the one the archive shows is not changed by it.
		await expect(proposal).toContainText('Initial Condition');
		await expect(proposal).toContainText('Intact');
		const shown = page.locator('[data-displayed-condition]');
		await expect(shown).toContainText('Condition shown by the archive: none');
		await expect(shown).not.toContainText('Intact');
		// The Evidence level of the Attribution reads from what it cites.
		await expect(proposal).toContainText('documented · 1 source');
	});
});

test.describe('AC 39: the warning, the autosave status, and the results are announced', () => {
	test('autosave says it saved, in a status region', async ({ page }, info) => {
		const id = await startDraft(page, info);
		await open(page, id);
		await stepButton(page, 'en', 2).click();
		await page.locator('#editor-title').fill('Il gatto di prova');
		const status = page.getByRole('status').filter({ hasText: /^Saved automatically · \d\d:\d\d/ });
		await expect(status).toBeVisible();
		await expect
			.poll(async () => (await savedCopy(page, id))?.operations?.at(-1)?.record?.title)
			.toBe('Il gatto di prova');
	});

	test('the duplicate warning is announced and lists the Locations with all their Artworks', async ({
		page
	}, info) => {
		const id = await startDraft(page, info);
		await open(page, id);
		await page.locator('#editor-location-coordinates').fill('41.8955, 12.4823');
		await page.getByRole('button', { name: 'Use these coordinates' }).click();
		const warning = page.getByRole('region', { name: 'Is it already in the archive?' });
		await expect(warning).toBeVisible();
		await expect(
			page.getByRole('status').filter({ hasText: 'Warning: 1 Locations are close to this place.' })
		).toBeAttached();
		await expect(warning.getByRole('heading', { level: 4 })).toContainText('Parete di prova');
		await expect(warning).toContainText('12 m away');
		// All three Artworks of the Location, a disappeared one included.
		await expect(warning.locator('ul.artworks > li')).toHaveCount(3);
		await expect(warning).toContainText('Covered');
		await expect(
			warning.getByRole('link', { name: /Add documentation to this Artwork/ })
		).toHaveCount(3);
	});

	test('a failed submit is announced and the list of problems takes focus', async ({
		page
	}, info) => {
		const id = await startDraft(page, info);
		await open(page, id);
		await stepButton(page, 'en', 6).click();
		await page.getByRole('button', { name: 'Submit for review' }).click();
		await expect(
			page.getByRole('status').filter({ hasText: 'The form could not be submitted: 7 problems' })
		).toBeAttached();
		await expect(page.getByRole('alert')).toContainText('7 problems to fix before you can submit');
		await expect(page.getByRole('alert')).toBeFocused();
	});
});

test.describe('the duplicate warning asks for the explicit confirmations', () => {
	test('"it is another surface" is confirmed once, and the Location is a new one', async ({
		page
	}, info) => {
		const draft = await startDraft(page, info, { extra: '-surface' });
		await open(page, draft);
		await page.locator('#editor-location-coordinates').fill('41.8955, 12.4823');
		await page.getByRole('button', { name: 'Use these coordinates' }).click();
		const confirm = page.getByLabel(/It's another surface/);
		await expect(confirm).not.toBeChecked();
		await stepButton(page, 'en', 6).click();
		await page.getByRole('button', { name: 'Submit for review' }).click();
		await expect(page.locator('#editor-summary')).toContainText(
			'Confirm that this is another surface, or put the Artwork on one of the Locations listed.'
		);
		await page
			.locator('#editor-summary')
			.getByRole('link', { name: /Confirm that this is another surface/ })
			.click();
		await expect(confirm).toBeFocused();
		await expect(confirm).toHaveAttribute('aria-invalid', 'true');
		await confirm.check();
		await expect(page.locator('#editor-duplicate-confirm-error')).toHaveCount(0);
	});

	test('"New Artwork on this Location" puts it on that Location and asks to confirm it is a different Artwork', async ({
		page
	}, info) => {
		const draft = await startDraft(page, info);
		await open(page, draft);
		await page.locator('#editor-location-coordinates').fill('41.8955, 12.4823');
		await page.getByRole('button', { name: 'Use these coordinates' }).click();
		await page.getByRole('button', { name: /New Artwork on this Location/ }).click();
		await expect(
			page.getByText('The Artwork will be put on the existing Location: Parete di prova 1.')
		).toBeVisible();
		// The drawn geometry is dropped, and no Location is created.
		await expect(page.getByLabel('Type of surface')).toHaveCount(0);
		const confirm = page.getByLabel('It is a different Artwork from those listed.');
		await expect(confirm).not.toBeChecked();
		await confirm.check();
		await expect(stepButton(page, 'en', 0)).toContainText('complete');
		await expect(stepButton(page, 'en', 0)).not.toContainText('to complete');
		await expect
			.poll(async () => (await savedCopy(page, draft))?.operations?.at(-1)?.record?.location)
			.toBe(200);
		const kinds = ((await savedCopy(page, draft)).operations as { kind: string }[]).map(
			(each) => each.kind
		);
		expect(kinds).not.toContain('location');
	});
});

test.describe('submitting', () => {
	test('a complete Artwork is submitted with the terms accepted once, and the draft becomes a Submission', async ({
		page
	}, info) => {
		const id = await startDraft(page, info, { content: complete() });
		await open(page, id);
		await stepButton(page, 'en', 6).click();
		await expect(page.getByLabel(/I accept the/)).toBeVisible();
		await page.getByRole('button', { name: 'Submit for review' }).click();
		await expect(page.locator('#editor-summary')).toContainText(
			'Accept the terms of use to submit.'
		);
		await page.getByLabel(/I accept the/).check();
		await page.getByLabel('Note to the Moderators (optional)').fill('Una nota fittizia.');
		await page.getByRole('button', { name: 'Submit for review' }).click();
		await expect(page).toHaveURL(new RegExp(`/en/contributions/${id}$`));
		const submitted = await (await page.request.get(`${MOCK}/api/contributions/${id}`)).json();
		expect(submitted.status).toBe('submitted');
		expect(submitted.last_round.initial_condition).toBe('intact');
	});

	test('a User who accepted the terms sees one line, not the box', async ({ page }, info) => {
		const id = await startDraft(page, info, { extra: '-accettati', content: complete() });
		await open(page, id);
		await stepButton(page, 'en', 6).click();
		await expect(page.getByText('You accepted the terms (version 1).')).toBeVisible();
		await expect(page.getByLabel(/I accept the/)).toHaveCount(0);
		await page.getByRole('button', { name: 'Submit for review' }).click();
		await expect(page).toHaveURL(new RegExp(`/en/contributions/${id}$`));
	});

	test('a refusal by the server stays in the editor, words the wait, and keeps the draft', async ({
		page
	}, info) => {
		const id = await startDraft(page, info, { extra: '-accettati', content: complete() });
		await open(page, id);
		await stepButton(page, 'en', 6).click();
		await page.getByLabel('Note to the Moderators (optional)').fill('oltre il limite');
		await page.getByRole('button', { name: 'Submit for review' }).click();
		const summary = page.locator('#editor-summary');
		await expect(summary).toBeFocused();
		await expect(summary).toContainText('You have submitted too much in 24 hours.');
		await expect(summary).toContainText('in 10 minutes');
		await expect(page).toHaveURL(new RegExp(`/en/contributions/${id}/edit$`));
		expect((await savedCopy(page, id)).initial_condition).toBe('intact');
	});

	test('a server error for a rule the form did not foresee is placed at its step', async ({
		page
	}, info) => {
		const content = complete();
		(content.operations[0].record as { geometry: unknown }).geometry = {
			type: 'Point',
			coordinates: [13.5, 41.91]
		};
		const id = await startDraft(page, info, { extra: '-accettati', content });
		await open(page, id);
		await stepButton(page, 'en', 6).click();
		await page.getByRole('button', { name: 'Submit for review' }).click();
		await page
			.locator('#editor-summary')
			.getByRole('link', { name: /The position is outside the area this archive covers/ })
			.click();
		await expect(heading(page, 'en', 0)).toBeVisible();
	});
});

test.describe('leaving', () => {
	test('a draft is resumed at its first step still to complete, with a notice that can be dismissed', async ({
		page
	}, info) => {
		const id = await startDraft(page, info, { content: complete({ initial_condition: null }) });
		await open(page, id);
		await expect(heading(page, 'en', 1)).toBeVisible();
		const notice = page.getByRole('complementary', { name: 'Draft resumed' });
		await expect(notice).toContainText('first step still to complete: Documentation');
		await notice.getByRole('button', { name: 'Dismiss' }).click();
		await expect(notice).toHaveCount(0);
		// What was entered is where it was left.
		await stepButton(page, 'en', 2).click();
		await expect(page.locator('#editor-title')).toHaveValue('Il gatto di prova');
		await stepButton(page, 'en', 3).click();
		await expect(page.getByLabel('The artist is known or can be suggested')).toBeChecked();
	});

	test('Delete draft asks first, and deletes', async ({ page }, info) => {
		const id = await startDraft(page, info);
		await open(page, id);
		await page.getByRole('button', { name: 'Delete draft' }).click();
		await expect(page.getByText('Delete this draft and its files for good?')).toBeVisible();
		await page.getByRole('button', { name: 'No, keep it' }).click();
		await expect(page.getByRole('button', { name: 'Delete draft' })).toBeVisible();
		await page.getByRole('button', { name: 'Delete draft' }).click();
		await page.getByRole('button', { name: 'Yes, delete the draft' }).click();
		await expect(page).toHaveURL(/\/en\/account\/contributions$/);
		const gone = await page.request.get(`${MOCK}/api/contributions/${id}`);
		expect(gone.status()).toBe(404);
	});

	test('Exit and continue later saves first', async ({ page }, info) => {
		const id = await startDraft(page, info);
		await open(page, id);
		await stepButton(page, 'en', 2).click();
		await page.locator('#editor-title').fill('Il gatto di prova');
		await page.getByRole('button', { name: 'Exit and continue later' }).click();
		await expect(page).toHaveURL(/\/en\/account\/contributions$/);
		expect((await savedCopy(page, id)).operations.at(-1).record.title).toBe('Il gatto di prova');
	});

	test('a draft of someone else, or a missing one, answers 404; an anonymous visitor signs in', async ({
		page
	}, info) => {
		const id = await startDraft(page, info);
		await page.context().clearCookies();
		await page.goto(WORDS.en.path(id));
		await expect(page).toHaveURL(/\/en\/sign-in\?next=/);
		await page
			.context()
			.addCookies([
				{ name: 'tart_session', value: encodeURIComponent(address(info, '-altra')), url: BASE }
			]);
		const other = await page.goto(WORDS.en.path(id));
		expect(other?.status()).toBe(404);
		const missing = await page.goto(WORDS.en.path(999999));
		expect(missing?.status()).toBe(404);
	});
});

test.describe('the upload of a file', () => {
	test('a refused file says why, and a second attempt is a new document', async ({
		page
	}, info) => {
		const id = await startDraft(page, info);
		await open(page, id);
		await stepButton(page, 'en', 1).click();
		await page.locator('#editor-documentation-add').setInputFiles({
			name: 'rifiutato.tiff',
			mimeType: 'image/tiff',
			buffer: Buffer.from('fictional')
		});
		await expect(
			page.getByText('The file was refused: this type of file is not supported')
		).toBeVisible({
			timeout: 10_000
		});
		await stepButton(page, 'en', 6).click();
		await page.getByRole('button', { name: 'Submit for review' }).click();
		await expect(page.locator('#editor-summary')).toContainText('The file was refused.');
	});

	test('an uploaded image asks for its rights fields, alt text included', async ({
		page
	}, info) => {
		const id = await startDraft(page, info);
		await open(page, id);
		await stepButton(page, 'en', 1).click();
		await page.locator('#editor-documentation-add').setInputFiles({
			name: 'foto.jpg',
			mimeType: 'image/jpeg',
			buffer: Buffer.from('fictional image')
		});
		await expect(page.getByText('File ready.')).toBeVisible({ timeout: 10_000 });
		await expect(page.getByLabel('Licence of the file')).toHaveValue('CC-BY-SA-4.0');
		await expect(page.getByLabel('Text alternative')).toBeVisible();
		await page.getByLabel('Someone else').check();
		await expect(page.getByLabel('Where it was published (address)')).toBeVisible();
		await stepButton(page, 'en', 6).click();
		await page.getByRole('button', { name: 'Submit for review' }).click();
		const summary = page.locator('#editor-summary');
		await expect(summary).toContainText('Enter the creator credit.');
		await expect(summary).toContainText(
			'Enter a text alternative that describes what the image shows.'
		);
		await expect(summary).toContainText('Enter the address where the file was published.');
	});
});

test.describe('creating records inline', () => {
	test('a new Artist whose name is alike shows the candidate and does not block', async ({
		page
	}, info) => {
		const id = await startDraft(page, info);
		await open(page, id);
		await stepButton(page, 'en', 3).click();
		await page.getByLabel('The artist is known or can be suggested').check();
		await page.getByLabel('Search an Artist by name').fill('Nebbia Finta II');
		await page.getByRole('button', { name: 'Create a new Artist with this name' }).click();
		const alike = page.getByRole('region', { name: 'Something similar exists' });
		await expect(alike).toContainText('Nebbia Finta');
		await alike.getByRole('button', { name: 'Create mine anyway' }).click();
		await expect(page.getByText('Attribution 1: Nebbia Finta II')).toBeVisible();
		await expect(page.getByText('Evidence level: reported · no sources cited')).toBeVisible();
		// A confirmed attribution needs a citation.
		await page.getByLabel('How sure is this attribution').selectOption('confirmed');
		await stepButton(page, 'en', 6).click();
		await page.getByRole('button', { name: 'Submit for review' }).click();
		await expect(page.locator('#editor-summary')).toContainText(
			'A confirmed attribution must cite at least one Source or document.'
		);
	});

	test('an existing Artist is found by name and linked', async ({ page }, info) => {
		const id = await startDraft(page, info);
		await open(page, id);
		await stepButton(page, 'en', 3).click();
		await page.getByLabel('The artist is known or can be suggested').check();
		await page.getByLabel('Search an Artist by name').fill('lupo');
		await page.getByRole('main').getByRole('button', { name: 'Search', exact: true }).click();
		await page.getByRole('button', { name: 'Use Lupo Inventato' }).click();
		await expect(page.getByText('Attribution 1: Lupo Inventato')).toBeVisible();
	});
});

test.describe('axe over the states of the editor', () => {
	for (const language of ['en', 'it'] as const) {
		for (const colorScheme of ['light', 'dark'] as const) {
			test(`an empty draft, every step (${language}, ${colorScheme})`, async ({ page }, info) => {
				await page.emulateMedia({ colorScheme });
				const id = await startDraft(page, info);
				await open(page, id, language);
				for (const index of [0, 1, 2, 3, 4, 5, 6]) {
					await stepButton(page, language, index).click();
					await expect(heading(page, language, index)).toBeVisible();
					await axe(page, `empty draft, step ${index + 1}`);
				}
			});

			test(`a resumed draft with everything in it, every step (${language}, ${colorScheme})`, async ({
				page
			}, info) => {
				await page.emulateMedia({ colorScheme });
				const id = await startDraft(page, info, { content: complete() });
				await open(page, id, language);
				// Everything is complete: it resumes at the end.
				await expect(heading(page, language, 6)).toBeVisible();
				for (const index of [6, 0, 1, 2, 3, 4, 5]) {
					await stepButton(page, language, index).click();
					await expect(heading(page, language, index)).toBeVisible();
					await axe(page, `resumed draft, step ${index + 1}`);
				}
			});

			test(`validation errors, every step (${language}, ${colorScheme})`, async ({
				page
			}, info) => {
				await page.emulateMedia({ colorScheme });
				const id = await startDraft(page, info);
				await open(page, id, language);
				await stepButton(page, language, 6).click();
				await page.getByRole('button', { name: WORDS[language].submit }).click();
				await expect(page.locator('#editor-summary')).toBeFocused();
				for (const index of [6, 0, 1, 2, 3]) {
					await stepButton(page, language, index).click();
					await expect(heading(page, language, index)).toBeVisible();
					await axe(page, `errors, step ${index + 1}`);
				}
			});

			test(`the duplicate warning (${language}, ${colorScheme})`, async ({ page }, info) => {
				await page.emulateMedia({ colorScheme });
				const id = await startDraft(page, info);
				await open(page, id, language);
				await page.locator('#editor-location-coordinates').fill('41.8955, 12.4823');
				await page
					.getByRole('button', {
						name: language === 'en' ? 'Use these coordinates' : 'Usa queste coordinate'
					})
					.click();
				await expect(page.locator('#editor-duplicates-title')).toBeVisible();
				await axe(page, 'duplicate warning');
				await page.locator('#editor-duplicate-confirm').focus();
				await stepButton(page, language, 6).click();
				await page.getByRole('button', { name: WORDS[language].submit }).click();
				await stepButton(page, language, 0).click();
				await expect(page.locator('#editor-duplicate-confirm-error')).toBeVisible();
				await axe(page, 'duplicate warning with its error');
			});
		}
	}

	test('documents, alike records, and sources in use (en)', async ({ page }, info) => {
		const id = await startDraft(page, info);
		await open(page, id);
		await stepButton(page, 'en', 1).click();
		await page.locator('#editor-documentation-add').setInputFiles({
			name: 'foto.jpg',
			mimeType: 'image/jpeg',
			buffer: Buffer.from('fictional image')
		});
		await expect(page.getByText('File ready.')).toBeVisible({ timeout: 10_000 });
		await page.getByLabel('Someone else').check();
		await axe(page, 'a file with third-party rights');
		await stepButton(page, 'en', 3).click();
		await page.getByLabel('The artist is known or can be suggested').check();
		await page.getByLabel('Search an Artist by name').fill('Nebbia Finta II');
		await page.getByRole('button', { name: 'Create a new Artist with this name' }).click();
		await axe(page, 'a similar Artist');
		await page.getByRole('button', { name: 'Create mine anyway' }).click();
		await axe(page, 'a new attribution');
	});
});
