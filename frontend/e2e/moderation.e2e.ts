import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';
import { serveStyles } from './map-style';

// The Moderation queue and the Submission page as a Moderator reads it (Contribution and
// moderation spec, Queue, Submission page, Moderator identity and Moderation notes): criteria
// 33, 34, 35, 37, 43, and 52. The stand-in API keeps, for each Moderator, seven fictional
// Submissions of other people (e2e/mock-api.ts, `queueSeed`); the API's own tests cover what
// is sent to whom, the orders, the filters, and the comparisons themselves.

const WCAG_22_AA = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];

type Language = 'it' | 'en';

const PATHS = {
	it: {
		queue: '/it/moderazione',
		submission: (id: number) => `/it/contributi/${id}`,
		signIn: '/it/accedi'
	},
	en: {
		queue: '/en/moderation',
		submission: (id: number) => `/en/contributions/${id}`,
		signIn: '/en/sign-in'
	}
} as const;

/** An address of its own for each test and project, since the stand-in API keeps state. */
function address(local: string, info: { project: { name: string }; title: string }) {
	const title = info.title
		.toLowerCase()
		.replace(/[^a-z0-9]+/g, '-')
		.slice(-80);
	return `${local}-${info.project.name}-${title}@example.org`;
}

async function signIn(page: Page, email: string, next: string, language: Language = 'en') {
	const labels = {
		it: { email: 'Indirizzo email', send: 'Invia il codice', code: 'Codice', submit: 'Accedi' },
		en: { email: 'Email address', send: 'Send the code', code: 'Code', submit: 'Sign in' }
	}[language];
	await page.goto(`${PATHS[language].signIn}?next=${encodeURIComponent(next)}`);
	await page.getByLabel(labels.email).fill(email);
	await page.getByRole('button', { name: labels.send }).click();
	await page.getByLabel(labels.code, { exact: true }).fill('123456');
	await page.getByRole('main').getByRole('button', { name: labels.submit, exact: true }).click();
	await expect(page).toHaveURL(next);
}

/** Signed in as a Moderator, with the map styles and the images of the pages served. */
async function moderator(
	page: Page,
	info: { project: { name: string }; title: string },
	next: string,
	language: Language = 'en'
) {
	await serveStyles(page);
	await page.route('**/api/media/**', (route) =>
		route.fulfill({
			contentType: 'image/svg+xml',
			body: '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300"><rect width="400" height="300" fill="#ccc"/></svg>'
		})
	);
	await signIn(page, address('moderatrice', info), next, language);
}

async function expectNoViolations(page: Page) {
	const results = await new AxeBuilder({ page }).withTags(WCAG_22_AA).analyze();
	expect(results.violations).toEqual([]);
}

/** The ids of the Submissions listed, in order. */
async function queued(page: Page): Promise<number[]> {
	const links = await page
		.locator('tbody th a')
		.evaluateAll((all) => all.map((each) => each.getAttribute('href') ?? ''));
	return links.map((href) => Number(/(\d+)$/.exec(href)?.[1]));
}

/** The queue's row of a Submission, found by its own name: other rows link to it in their flags. */
function rowOf(page: Page, id: number) {
	return page.getByRole('row').filter({
		has: page.getByRole('rowheader', { name: new RegExp(`(Submission|contributo) ${id}\\)`) })
	});
}

async function clearFilters(page: Page) {
	await page.getByRole('link', { name: 'Clear the filters' }).click();
	await page.waitForURL((url) => url.search === '');
	await expect(page.getByRole('link', { name: 'Clear the filters' })).toHaveCount(0);
}

async function apply(page: Page, language: Language = 'en') {
	const before = page.url();
	await page.getByRole('button', { name: language === 'en' ? 'Apply' : 'Applica' }).click();
	await page.waitForURL((url) => url.href !== before);
}

const SUBMISSIONS = {
	newArtwork: 401,
	nearNewArtwork: 402,
	movedLocation: 403,
	addedImage: 404,
	outdated: 405,
	own: 406,
	changesRequested: 407
} as const;

// Criterion 34: the queue.

test('AC 34: the queue is oldest first by default and offers newest first and recently resubmitted', async ({
	page
}, info) => {
	await moderator(page, info, PATHS.en.queue);

	await expect(page.getByRole('heading', { level: 1 })).toHaveText('Moderation queue');
	// Only what awaits a decision: 407 waits for its Submitter.
	expect(await queued(page)).toEqual([405, 401, 404, 402, 403, 406]);
	await expect(page.getByRole('status')).toHaveText('Submissions waiting: 6');

	await page.getByLabel('Order', { exact: true }).selectOption('newest');
	await apply(page);
	await expect(page).toHaveURL(/sort=newest/);
	expect(await queued(page)).toEqual([406, 403, 402, 404, 401, 405]);

	await page.getByLabel('Order', { exact: true }).selectOption('resubmitted');
	await apply(page);
	expect(await queued(page)).toEqual([404, 406, 403, 402, 401, 405]);
});

test('AC 34: nothing in the queue ranks by popularity', async ({ page }, info) => {
	await moderator(page, info, PATHS.en.queue);

	const orders = await page
		.getByLabel('Order', { exact: true })
		.locator('option')
		.allTextContents();
	expect(orders).toEqual(['Oldest first', 'Newest first', 'Recently resubmitted']);
	await expect(page.getByRole('main')).not.toContainText(/likes|trending|followers/i);
});

test('AC 34: the queue filters by label, kind, Submitter, Area, and Outdated', async ({
	page
}, info) => {
	await moderator(page, info, PATHS.en.queue);

	await page.getByLabel('What it does').selectOption('adds_history_event');
	await apply(page);
	expect(await queued(page)).toEqual([401]);

	await clearFilters(page);
	await page.getByRole('combobox', { name: 'About' }).selectOption('location');
	await apply(page);
	expect(await queued(page)).toEqual([403]);

	await clearFilters(page);
	await page.getByLabel('Submitter (User number)').fill('8');
	await apply(page);
	expect(await queued(page)).toEqual([402]);

	await clearFilters(page);
	await page.getByLabel('Area', { exact: true }).selectOption({ index: 1 });
	await apply(page);
	await expect(page).toHaveURL(/area=\d+/);

	await clearFilters(page);
	await page.getByLabel('Outdated').selectOption('yes');
	await apply(page);
	expect(await queued(page)).toEqual([405]);
	await page.getByLabel('Outdated').selectOption('no');
	await apply(page);
	expect(await queued(page)).toEqual([401, 404, 402, 403, 406]);
});

test('AC 34: the queue says what to note in words, and an empty result has its own state', async ({
	page
}, info) => {
	await moderator(page, info, PATHS.en.queue);

	const outdated = rowOf(page, 405);
	await expect(outdated).toContainText('Outdated: the record changed after it was written');
	await expect(outdated.getByRole('link', { name: 'Submission 404' })).toHaveAttribute(
		'href',
		'/en/contributions/404'
	);
	const near = rowOf(page, 401);
	await expect(near).toContainText('A new Location within 25 m of the new Location of:');
	await expect(near.getByRole('link', { name: 'Submission 402' })).toBeVisible();
	await expect(rowOf(page, 403)).toContainText('Nothing to note');
	await expect(rowOf(page, 406)).toContainText('Your own Submission');

	await page.getByLabel('Submitter (User number)').fill('999');
	await apply(page);
	await expect(page.getByText('No waiting Submission matches these filters.')).toBeVisible();
	await expect(page.getByRole('status')).toHaveText('Submissions waiting: 0');
});

test('AC 34: the queue is in Italian under its own address', async ({ page }, info) => {
	await moderator(page, info, PATHS.it.queue, 'it');

	await expect(page.getByRole('heading', { level: 1 })).toHaveText('Coda di moderazione');
	await expect(page.getByLabel('Ordine', { exact: true })).toBeVisible();
	await expect(page.getByRole('status')).toHaveText('Contributi in attesa: 6');
	const outdated = rowOf(page, 405);
	await expect(outdated).toContainText('Superato: la scheda è cambiata dopo che è stato scritto');
	await expect(outdated).toContainText('Utente n. 10');
});

test('AC 34: the queue is operable by keyboard', async ({ page }, info) => {
	await moderator(page, info, PATHS.en.queue);

	await page.getByLabel('Order', { exact: true }).focus();
	await page.keyboard.press('ArrowDown');
	await page.keyboard.press('Tab');
	await expect(page.getByLabel('What it does')).toBeFocused();
	await page.getByRole('button', { name: 'Apply' }).focus();
	await page.keyboard.press('Enter');
	await expect(page).toHaveURL(/sort=newest/);
	await page.getByRole('link', { name: /Submission 406/ }).focus();
	await page.keyboard.press('Enter');
	await expect(page).toHaveURL('/en/contributions/406');
});

// Criterion 37 and 33: who is named, and Moderation notes.

test('AC 37: a Moderator reads the Submitter by display name and User number, never an email', async ({
	page
}, info) => {
	await moderator(page, info, PATHS.en.submission(SUBMISSIONS.newArtwork));

	await expect(page.getByRole('heading', { level: 1 })).toHaveText('New Artwork (Submission 401)');
	await expect(page.getByText('Ada di prova (User #7)')).toBeVisible();
	await expect(page.getByRole('main')).not.toContainText('@');
	await page.goto(PATHS.en.queue);
	await expect(page.getByRole('main')).toContainText('Ada di prova (User #7)');
	await expect(page.getByRole('main')).not.toContainText('@');
});

test('AC 37: someone who is not a Moderator, nor the Submitter, is told the Submission does not exist', async ({
	page
}, info) => {
	await signIn(page, address('persona', info), '/en/', 'en');

	const response = await page.goto(PATHS.en.submission(SUBMISSIONS.newArtwork));

	expect(response?.status()).toBe(404);
});

test('AC 33: a Moderator adds a Moderation note with author and date, and cannot edit it', async ({
	page
}, info) => {
	await moderator(page, info, PATHS.en.submission(SUBMISSIONS.newArtwork));
	const notes = page.getByRole('region', { name: 'Moderation notes' });

	await expect(notes).toContainText('Only Moderators read these notes.');
	await expect(notes).toContainText('No note yet.');
	await notes.getByLabel('New note').fill('Controllare la liberatoria dei file.');
	await notes.getByRole('button', { name: 'Add the note' }).click();

	await expect(notes.getByRole('status')).toHaveText('The note was added.');
	const note = notes.getByRole('listitem');
	await expect(note).toContainText('Moderatrice di prova (User #1)');
	await expect(note.locator('blockquote')).toHaveText('Controllare la liberatoria dei file.');
	await expect(note.locator('blockquote')).toHaveAttribute('lang', 'it');
	// A note is immutable: there is nothing to edit or delete.
	await expect(note.getByRole('button')).toHaveCount(0);
	await expect(notes.getByRole('textbox')).toHaveValue('');
	// It is still there after a reload.
	await page.reload();
	await expect(notes.locator('blockquote')).toHaveText('Controllare la liberatoria dei file.');
});

test('AC 33: a blank note is refused in words', async ({ page }, info) => {
	await moderator(page, info, PATHS.en.submission(SUBMISSIONS.newArtwork));
	const notes = page.getByRole('region', { name: 'Moderation notes' });

	await notes.getByRole('button', { name: 'Add the note' }).click();

	await expect(notes.getByRole('alert')).toHaveText('Write the note first.');
	await expect(notes.getByLabel('New note')).toHaveAttribute('aria-invalid', 'true');
});

test('AC 33: a Moderator can add a note to their own Submission, which they cannot decide on', async ({
	page
}, info) => {
	await moderator(page, info, PATHS.en.submission(SUBMISSIONS.own));
	const notes = page.getByRole('region', { name: 'Moderation notes' });

	await notes.getByLabel('New note').fill('Una nota sulla mia scheda.');
	await notes.getByRole('button', { name: 'Add the note' }).click();

	await expect(notes.getByRole('status')).toHaveText('The note was added.');
	const decision = page.getByRole('region', { name: 'Your decision' });
	await expect(decision).toContainText('This is your own Submission.');
	await expect(decision.getByRole('button')).toHaveCount(0);
});

// Criterion 35: the review checklist.

for (const language of ['en', 'it'] as const) {
	test(`AC 35: the ${language} checklist is beside the decision on every Submission a Moderator opens`, async ({
		page
	}, info) => {
		await moderator(page, info, PATHS[language].submission(SUBMISSIONS.newArtwork), language);
		const heading = { en: 'Review checklist', it: 'Lista di controllo' }[language];
		const guidelines = { en: 'Editorial guidelines', it: 'Linee guida editoriali' }[language];

		for (const id of Object.values(SUBMISSIONS)) {
			await page.goto(PATHS[language].submission(id));
			const checklist = page.getByRole('region', { name: heading });
			await expect(checklist.getByRole('listitem')).toHaveCount(8);
			await expect(checklist.getByRole('link', { name: guidelines })).toHaveAttribute(
				'href',
				language === 'en' ? '/en/about/guidelines' : '/it/informazioni/linee-guida'
			);
		}
		await page.goto(PATHS[language].submission(SUBMISSIONS.newArtwork));
		const first = await page
			.getByRole('region', { name: heading })
			.getByRole('listitem')
			.first()
			.textContent();
		expect(first).toContain(language === 'en' ? 'People and plates' : 'Persone e targhe');
		// It sits beside the decision, in the same part of the page, and nothing needs ticking.
		await expect(page.getByRole('region', { name: heading }).getByRole('checkbox')).toHaveCount(0);
	});
}

// Criterion 43: the decision form.

test('AC 43: the decision form lists the configured reasons in file order, then duplicate', async ({
	page
}, info) => {
	await moderator(page, info, PATHS.en.submission(SUBMISSIONS.newArtwork));
	const reasons = page.getByLabel('Reason, to reject or to ask for changes');

	expect(await reasons.locator('option').allTextContents()).toEqual([
		'Choose a reason',
		'Identifiable people or number plates',
		'Insufficient evidence',
		'Duplicate of an existing record'
	]);
	expect(
		await reasons
			.locator('option')
			.evaluateAll((all) => all.map((each) => each.getAttribute('value')))
	).toEqual(['', 'people', 'evidence', 'duplicate']);

	await page.goto(PATHS.it.submission(SUBMISSIONS.newArtwork));
	const italian = page.getByLabel('Motivo, per rifiutare o chiedere modifiche');
	expect(await italian.locator('option').allTextContents()).toEqual([
		'Scegli un motivo',
		'Persone o targhe riconoscibili',
		'Prove insufficienti',
		'Duplicato di un record esistente'
	]);
});

test('AC 43: asking for changes with the duplicate reason stores it and says it in words', async ({
	page
}, info) => {
	await moderator(page, info, PATHS.en.submission(SUBMISSIONS.newArtwork));

	await page
		.getByLabel('Reason, to reject or to ask for changes')
		.selectOption({ label: 'Duplicate of an existing record' });
	await page
		.getByLabel('Message to the Submitter, to reject or to ask for changes')
		.fill('Sembra la stessa opera della scheda 42.');
	await page.getByRole('button', { name: 'Ask for changes' }).click();

	const decision = page.getByRole('region', { name: 'Your decision' });
	await expect(decision.getByRole('status')).toHaveText('Changes were requested.');
	await expect(page.getByText('Changes requested').first()).toBeVisible();
	const message = page.getByRole('region', { name: 'Message from the Moderators' });
	await expect(message).toContainText('Duplicate of an existing record');
	await expect(message.locator('blockquote')).toHaveAttribute('lang', 'it');
	// Now it waits for its Submitter: a Moderator can only reject it.
	await expect(page.getByRole('button', { name: 'Reject' })).toBeVisible();
	await expect(page.getByRole('button', { name: 'Approve' })).toHaveCount(0);
	await expect(page.getByRole('button', { name: 'Ask for changes' })).toHaveCount(0);
});

test('AC 43: approving takes no message and records the decision', async ({ page }, info) => {
	await moderator(page, info, PATHS.en.submission(SUBMISSIONS.nearNewArtwork));

	await page.getByRole('button', { name: 'Approve' }).click();

	await expect(page.getByRole('region', { name: 'Your decision' }).getByRole('status')).toHaveText(
		'The Submission was approved.'
	);
	await expect(page.getByText('Approved').first()).toBeVisible();
	await expect(page.getByRole('region', { name: 'Submission log' })).toContainText('Approved');
	await expect(page.getByRole('region', { name: 'Submission log' })).toContainText(
		'Moderatrice di prova (User #1)'
	);
});

test('AC 43: a rejection without reason or message is refused in words, field by field', async ({
	page
}, info) => {
	await moderator(page, info, PATHS.en.submission(SUBMISSIONS.newArtwork));
	const decision = page.getByRole('region', { name: 'Your decision' });

	await page.getByRole('button', { name: 'Reject' }).click();
	await expect(decision.getByRole('alert')).toHaveText('Choose a reason.');
	await expect(page.getByLabel('Reason, to reject or to ask for changes')).toHaveAttribute(
		'aria-invalid',
		'true'
	);

	await page.getByLabel('Reason, to reject or to ask for changes').selectOption('evidence');
	await page.getByRole('button', { name: 'Reject' }).click();
	await expect(decision.getByRole('alert')).toHaveText('Write the message for the Submitter.');
	await expect(
		page.getByLabel('Message to the Submitter, to reject or to ask for changes')
	).toHaveAttribute('aria-invalid', 'true');
});

test('AC 43: a decision somebody else took first shows a message and reloads the page', async ({
	page
}, info) => {
	await moderator(page, info, PATHS.en.submission(SUBMISSIONS.newArtwork));

	// Another Moderator (the same stand-in session in a second page) rejects it first.
	const other = await page.context().newPage();
	await other.goto(PATHS.en.submission(SUBMISSIONS.newArtwork));
	await other.getByLabel('Reason, to reject or to ask for changes').selectOption('evidence');
	await other
		.getByLabel('Message to the Submitter, to reject or to ask for changes')
		.fill('Prove.');
	await other.getByRole('button', { name: 'Reject' }).click();
	await expect(other.getByText('The Submission was rejected.')).toBeVisible();

	await page.getByRole('button', { name: 'Approve' }).click();

	await expect(page.getByRole('region', { name: 'Your decision' }).getByRole('alert')).toHaveText(
		'Someone decided on this Submission first. The page shows its current state.'
	);
	// The page reloaded: it shows the other decision, and offers no decision any more.
	await expect(page.getByText('Rejected').first()).toBeVisible();
	await expect(page.getByRole('button', { name: 'Approve' })).toHaveCount(0);
});

test('AC 43: an Outdated Submission cannot be approved, and one with changes requested only rejected', async ({
	page
}, info) => {
	await moderator(page, info, PATHS.en.submission(SUBMISSIONS.outdated));
	await expect(
		page.getByText('This Submission is Outdated, so it cannot be approved.')
	).toBeVisible();
	await expect(page.getByRole('button', { name: 'Approve' })).toHaveCount(0);
	await expect(page.getByRole('button', { name: 'Reject' })).toBeVisible();

	await page.goto(PATHS.en.submission(SUBMISSIONS.changesRequested));
	await expect(
		page.getByText('This Submission is waiting for its Submitter. You can only reject it.')
	).toBeVisible();
	await expect(page.getByRole('button', { name: 'Reject' })).toBeVisible();
	await expect(page.getByRole('button', { name: 'Approve' })).toHaveCount(0);
	await expect(page.getByRole('button', { name: 'Ask for changes' })).toHaveCount(0);
});

test('AC 43: the decision is operable by keyboard', async ({ page }, info) => {
	await moderator(page, info, PATHS.en.submission(SUBMISSIONS.newArtwork));

	await page.getByLabel('Reason, to reject or to ask for changes').focus();
	await page.keyboard.press('ArrowDown');
	await page.keyboard.press('Tab');
	await page.keyboard.type('Mancano le prove.');
	await page.keyboard.press('Tab');
	await expect(page.getByRole('button', { name: 'Approve' })).toBeFocused();
	await page.keyboard.press('Tab');
	await expect(page.getByRole('button', { name: 'Reject' })).toBeFocused();
	await page.keyboard.press('Enter');

	await expect(page.getByText('Rejected').first()).toBeVisible();
});

// Criterion 52: the comparisons.

test('AC 52: images are set side by side at the same size, current left and proposed right', async ({
	page
}, info) => {
	test.skip(info.project.name === 'mobile', 'the pair is stacked on a narrow screen');
	await moderator(page, info, PATHS.en.submission(SUBMISSIONS.addedImage));
	const images = page.getByRole('region', { name: 'Images' });

	const current = images.getByRole('figure').first();
	const proposed = images.getByRole('figure').last();
	await expect(current).toContainText('Current image');
	await expect(proposed).toContainText('Proposed image');
	await expect(current).toContainText('Observed 2023');
	await expect(current).toContainText('Credit: Fotografa fittizia. Licence: CC-BY-SA-4.0.');
	await expect(proposed).toContainText('Observed 2025');
	const left = (await current.locator('img').boundingBox())!;
	const right = (await proposed.locator('img').boundingBox())!;
	expect(left.x).toBeLessThan(right.x);
	expect(Math.abs(left.y - right.y)).toBeLessThan(2);
	expect(Math.abs(left.width - right.width)).toBeLessThan(2);
	expect(Math.abs(left.height - right.height)).toBeLessThan(2);
	// There is no swipe or toggle: only the two images and a link to each at full size.
	await expect(images.getByRole('button')).toHaveCount(0);
	for (const [figure, file] of [
		[current, '8b3e1c3f-2222-4c0c-9a58-0d6a8c3e8b13'],
		[proposed, '7a2d0b2e-1111-4c0c-9a58-0d6a8c3e8b12']
	] as const) {
		const link = figure.getByRole('link', { name: 'Open at full size (new tab)' });
		await expect(link).toHaveAttribute('href', `/api/media/${file}/large`);
		await expect(link).toHaveAttribute('target', '_blank');
		await expect(link).toHaveAttribute('rel', /noopener/);
	}
});

test('AC 52: below 600 px the images are stacked, and a new Artwork has no current image', async ({
	page
}, info) => {
	await page.setViewportSize({ width: 420, height: 900 });
	await moderator(page, info, PATHS.en.submission(SUBMISSIONS.addedImage));
	const images = page.getByRole('region', { name: 'Images' });

	// Measure once the images are in, so that nothing shifts between the two measures.
	await images
		.locator('img')
		.evaluateAll((all) => Promise.all(all.map((each) => (each as HTMLImageElement).decode())));
	const upper = (await images.getByRole('figure').first().locator('img').boundingBox())!;
	const lower = (await images.getByRole('figure').last().locator('img').boundingBox())!;
	expect(lower.y).toBeGreaterThan(upper.y + upper.height - 1);
	expect(Math.abs(lower.x - upper.x)).toBeLessThan(2);

	await page.goto(PATHS.en.submission(SUBMISSIONS.newArtwork));
	await expect(page.getByText('This Artwork has no image yet.')).toBeVisible();
});

test('AC 52: geometries are overlaid with a legend in words and a text summary', async ({
	page
}, info) => {
	await moderator(page, info, PATHS.en.submission(SUBMISSIONS.movedLocation));
	const geometry = page.getByRole('region', { name: 'Geometry' });

	await expect(geometry.locator('.map[data-state="ready"]')).toBeVisible();
	await expect(
		geometry.getByRole('group', { name: 'Map of the current and the proposed geometry' })
	).toBeVisible();
	await expect(geometry.getByText('Grey, solid outline: the current geometry.')).toBeVisible();
	await expect(geometry.getByText('Dashed outline: the proposed geometry.')).toBeVisible();
	await expect(geometry.getByText('Vertices: 1 before, 1 after.')).toBeVisible();
	await expect(geometry.getByText('Largest shift: 30 m towards the north.')).toBeVisible();
	await expect(geometry.getByRole('link', { name: 'Location 13, 10 m away' })).toHaveAttribute(
		'href',
		'/en/locations/13'
	);
});

test('AC 52: without WebGL2 the text summary alone is shown', async ({ page }, info) => {
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
	await moderator(page, info, PATHS.en.submission(SUBMISSIONS.movedLocation));
	const geometry = page.getByRole('region', { name: 'Geometry' });

	await expect(geometry.getByText('Largest shift: 30 m towards the north.')).toBeVisible();
	await expect(geometry.locator('.map')).toHaveCount(0);
	await expect(geometry.getByText('Grey, solid outline: the current geometry.')).toHaveCount(0);
});

test('AC 52: a new Location says in the legend that there is no current geometry', async ({
	page
}, info) => {
	await moderator(page, info, PATHS.en.submission(SUBMISSIONS.newArtwork));
	const geometry = page.getByRole('region', { name: 'Geometry' });

	await expect(geometry.getByText('There is no current geometry: this one is new.')).toBeVisible();
	await expect(geometry.getByText('Vertices: 1.')).toBeVisible();
	await expect(geometry.getByRole('link', { name: 'Location 12, 18.4 m away' })).toBeVisible();
});

test('AC 52: each change is set beside what it replaces, and a revised round against the previous', async ({
	page
}, info) => {
	await moderator(page, info, PATHS.en.submission(SUBMISSIONS.addedImage));
	const proposed = page.getByRole('region', { name: 'Current and proposed' });

	await expect(proposed).toContainText('Now: Gatto');
	await expect(proposed).toContainText('Now: Nothing: it is not set now');
	await expect(proposed).toContainText(
		'Written against Revision 4; the record is now at Revision 5.'
	);

	const rounds = page.getByRole('region', { name: 'Rounds' });
	await expect(rounds).toContainText('Round 2 against round 1.');
	await expect(
		rounds.getByRole('listitem').filter({ hasText: 'Sets the field title' })
	).toContainText('The same as in the previous round');
	await expect(
		rounds.getByRole('listitem').filter({ hasText: 'Un gatto fittizio.' })
	).toContainText('New in this round');
	await expect(
		rounds.getByRole('heading', { name: 'Left out since the previous round' })
	).toBeVisible();
	await expect(rounds.getByText('Prima bozza.').first()).toBeVisible();
	// Every earlier round can be opened.
	await rounds.getByText(/^Round 1, submitted on/).click();
	await expect(rounds.getByText('Prima bozza.').first()).toBeVisible();
});

test('AC 52: the comparison is in Italian under its own address', async ({ page }, info) => {
	await moderator(page, info, PATHS.it.submission(SUBMISSIONS.movedLocation), 'it');

	await expect(page.getByRole('region', { name: 'Geometria' })).toContainText(
		'Spostamento massimo: 30 m verso nord.'
	);
	await expect(page.getByRole('region', { name: 'Geometria' })).toContainText(
		'Vertici: 1 prima, 1 dopo.'
	);
	await page.goto(PATHS.it.submission(SUBMISSIONS.addedImage));
	await expect(page.getByRole('region', { name: 'Immagini' })).toContainText('Immagine attuale');
});

// Criterion 41: axe on the pages of the Moderation area, in both languages.

for (const language of ['it', 'en'] as const) {
	for (const colorScheme of ['light', 'dark'] as const) {
		test(`AC 41: the ${language} queue passes axe in the ${colorScheme} theme, with results and without`, async ({
			page
		}, info) => {
			await page.emulateMedia({ colorScheme });
			await moderator(page, info, PATHS[language].queue, language);
			await expect(page.locator('tbody tr').first()).toBeVisible();
			await expectNoViolations(page);

			await page
				.getByLabel(language === 'en' ? 'Submitter (User number)' : 'Autore (numero utente)')
				.fill('999');
			await apply(page, language);
			await expect(page.locator('tbody tr')).toHaveCount(0);
			await expectNoViolations(page);
		});
	}

	test(`AC 41: the ${language} Submission page of a Moderator passes axe in every state`, async ({
		page
	}, info) => {
		await moderator(page, info, PATHS[language].queue, language);
		for (const id of Object.values(SUBMISSIONS)) {
			await page.goto(PATHS[language].submission(id));
			await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
			await expect(page.locator('.map[data-state="loading"]')).toHaveCount(0);
			await expectNoViolations(page);
		}
	});

	test(`AC 41: the ${language} Submission page passes axe with an error and with a note`, async ({
		page
	}, info) => {
		await moderator(page, info, PATHS[language].submission(SUBMISSIONS.newArtwork), language);
		await page.getByRole('button', { name: language === 'en' ? 'Reject' : 'Rifiuta' }).click();
		await expect(page.getByRole('alert')).toBeVisible();
		await expectNoViolations(page);

		await page
			.getByRole('region', { name: language === 'en' ? 'Moderation notes' : 'Note di moderazione' })
			.getByLabel(language === 'en' ? 'New note' : 'Nuova nota')
			.fill('Una nota fittizia.');
		await page
			.getByRole('button', { name: language === 'en' ? 'Add the note' : 'Aggiungi la nota' })
			.click();
		await expect(page.getByText('Una nota fittizia.')).toBeVisible();
		await expectNoViolations(page);
	});
}

test('AC 41: the Submission page of a Moderator passes axe in the dark theme', async ({
	page
}, info) => {
	await page.emulateMedia({ colorScheme: 'dark' });
	await moderator(page, info, PATHS.en.submission(SUBMISSIONS.addedImage));
	await expectNoViolations(page);
	await page.goto(PATHS.en.submission(SUBMISSIONS.movedLocation));
	await expect(page.locator('.map[data-state="ready"]')).toBeVisible();
	await expectNoViolations(page);
});
