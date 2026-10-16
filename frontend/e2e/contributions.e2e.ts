import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';

// The Contribute hub, My contributions, and the Submission page as the Submitter sees it
// (Contribution and moderation spec, acceptance criteria 38, 40, and 41). The stand-in API
// keeps, for each User, one Submission of every status (e2e/mock-api.ts, `contributions`);
// the API's own tests cover the lifecycle and what is sent to whom.

const WCAG_22_AA = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];

type Language = 'it' | 'en';

const PATHS = {
	it: {
		hub: '/it/contribuisci',
		mine: '/it/account/contributi',
		submission: (id: number) => `/it/contributi/${id}`
	},
	en: {
		hub: '/en/contribute',
		mine: '/en/account/contributions',
		submission: (id: number) => `/en/contributions/${id}`
	}
} as const;

function address(local: string, info: { project: { name: string }; title: string }) {
	const slug = `${info.project.name}-${info.title}`.toLowerCase().replace(/[^a-z0-9]+/g, '-');
	return `${local}-${slug}@example.org`.slice(-120);
}

async function signIn(page: Page, email: string, next: string, language: Language = 'en') {
	const labels = {
		it: { email: 'Indirizzo email', send: 'Invia il codice', code: 'Codice', submit: 'Accedi' },
		en: { email: 'Email address', send: 'Send the code', code: 'Code', submit: 'Sign in' }
	}[language];
	await page.goto(
		`/${language}/${language === 'it' ? 'accedi' : 'sign-in'}?next=${encodeURIComponent(next)}`
	);
	await page.getByLabel(labels.email).fill(email);
	await page.getByRole('button', { name: labels.send }).click();
	await page.getByLabel(labels.code, { exact: true }).fill('123456');
	await page.getByRole('main').getByRole('button', { name: labels.submit, exact: true }).click();
	await expect(page).toHaveURL(next);
}

async function expectNoViolations(page: Page) {
	const results = await new AxeBuilder({ page }).withTags(WCAG_22_AA).analyze();
	expect(results.violations).toEqual([]);
}

/** Submission ids of the stand-in API, with the status each is in. */
const SUBMISSIONS = {
	draft: 101,
	submitted: 102,
	changes_requested: 103,
	approved: 104,
	rejected: 105,
	retracted: 106,
	outdated: 107
} as const;

const STATUS_WORDS = {
	en: {
		draft: 'Draft: not submitted yet',
		submitted: 'Submitted: waiting for a decision',
		changes_requested: 'Changes requested',
		approved: 'Approved',
		rejected: 'Rejected',
		retracted: 'Retracted'
	},
	it: {
		draft: 'Bozza: non ancora inviato',
		submitted: 'Inviato: in attesa di una decisione',
		changes_requested: 'Modifiche richieste',
		approved: 'Approvato',
		rejected: 'Rifiutato',
		retracted: 'Ritirato'
	}
} as const;

test('AC 38: My contributions lists every status in words and filters by status', async ({
	page
}, info) => {
	await signIn(page, address('persona', info), PATHS.en.mine);

	await expect(page.getByRole('heading', { level: 1 })).toHaveText('My contributions');
	const rows = page.getByRole('row');
	for (const [status, words] of Object.entries(STATUS_WORDS.en)) {
		const id = SUBMISSIONS[status as keyof typeof STATUS_WORDS.en];
		await expect(rows.filter({ hasText: `Submission ${id}` }).first()).toContainText(words);
	}
	// A draft opens in the editor, every other Submission on its page.
	await expect(page.getByRole('link', { name: /Submission 101/ })).toHaveAttribute(
		'href',
		'/en/contributions/101/edit'
	);
	await expect(page.getByRole('link', { name: /Submission 104/ })).toHaveAttribute(
		'href',
		'/en/contributions/104'
	);

	await page.getByLabel('Show Submissions with status').selectOption('rejected');
	await page.getByRole('button', { name: 'Filter' }).click();

	await expect(page).toHaveURL(/status=rejected/);
	await expect(page.getByRole('row')).toHaveCount(2);
	await expect(page.getByRole('status')).toHaveText('Contributions shown: 1');
});

test('AC 38: a User with no contributions reads an empty state', async ({ page }, info) => {
	await signIn(page, address('persona-vuota', info), PATHS.en.mine);

	await expect(page.getByText('You have not started any contribution yet.')).toBeVisible();
	await expect(page.getByRole('link', { name: 'Go to Contribute' })).toBeVisible();
});

test('AC 38: an anonymous visitor is sent to sign-in and comes back', async ({ page }) => {
	await page.goto(PATHS.en.mine);

	await expect(page).toHaveURL(/\/en\/sign-in\?next=%2Fen%2Faccount%2Fcontributions/);
});

test('AC 38: the hub offers a new Artwork, the guidelines, the licences, and My contributions', async ({
	page
}, info) => {
	await signIn(page, address('persona', info), PATHS.en.hub);

	await expect(page.getByRole('heading', { level: 1 })).toHaveText('Contribute');
	await expect(page.getByRole('button', { name: 'Start a new Artwork' })).toBeVisible();
	await expect(page.getByRole('link', { name: 'Read the editorial guidelines' })).toBeVisible();
	await expect(page.getByText('CC BY-SA 4.0').first()).toBeVisible();
	await expect(
		page.getByRole('main').getByRole('link', { name: 'My contributions' })
	).toHaveAttribute('href', PATHS.en.mine);
});

test('AC 38: an anonymous visitor who starts a contribution goes to sign-in and returns to the hub', async ({
	page
}, info) => {
	await page.goto(PATHS.en.hub);
	await page.getByRole('button', { name: 'Start a new Artwork' }).click();
	await expect(page).toHaveURL(/\/en\/sign-in\?next=%2Fen%2Fcontribute/);

	await page.getByLabel('Email address').fill(address('persona', info));
	await page.getByRole('button', { name: 'Send the code' }).click();
	await page.getByLabel('Code', { exact: true }).fill('123456');
	await page.getByRole('main').getByRole('button', { name: 'Sign in', exact: true }).click();

	await expect(page).toHaveURL(PATHS.en.hub);
});

test('AC 38: starting a new Artwork opens its draft in the editor', async ({ page }, info) => {
	await signIn(page, address('persona', info), PATHS.en.hub);

	await page.getByRole('button', { name: 'Start a new Artwork' }).click();

	await expect(page).toHaveURL(/\/en\/contributions\/\d+\/edit$/);
});

test('AC 38: the Submission page tells the status in words and the log reads "a Moderator"', async ({
	page
}, info) => {
	await signIn(page, address('persona', info), PATHS.en.submission(SUBMISSIONS.changes_requested));

	await expect(page.getByRole('heading', { level: 1 })).toHaveText('New Artwork (Submission 103)');
	await expect(page.getByText(STATUS_WORDS.en.changes_requested).first()).toBeVisible();
	await expect(page.getByText('it is retracted on')).toBeVisible();
	const log = page.getByRole('region', { name: 'Submission log' });
	await expect(log).toContainText('By you');
	await expect(log).toContainText('By a Moderator');
	await expect(log).toContainText('Foto del 2021.');
	// The Decision message is quoted in the language of the content, with the reason's label.
	const decision = page.getByRole('region', { name: 'Message from the Moderators' });
	await expect(decision).toContainText('Duplicate');
	await expect(decision.locator('blockquote')).toHaveAttribute('lang', 'it');
	await expect(decision).toContainText('Sembra la stessa opera');
});

test('AC 38: an Outdated Submission says so in words', async ({ page }, info) => {
	await signIn(page, address('persona', info), PATHS.en.submission(SUBMISSIONS.outdated));

	await expect(page.getByText('The record changed after you wrote this Submission')).toBeVisible();
	await expect(page.getByRole('link', { name: 'Record 42 in the archive' })).toHaveAttribute(
		'href',
		'/en/artworks/42'
	);
});

test('AC 38: retracting is operable by keyboard and asks for confirmation', async ({
	page
}, info) => {
	await signIn(page, address('persona', info), PATHS.en.submission(SUBMISSIONS.submitted));
	const summary = page.getByText('Retract this Submission', { exact: true });

	await summary.focus();
	await expect(summary).toBeFocused();
	await page.keyboard.press('Enter');
	await page.keyboard.press('Tab');
	await expect(page.getByRole('button', { name: 'Yes, retract it' })).toBeFocused();
	await page.keyboard.press('Enter');

	await expect(page.getByRole('status')).toHaveText('The Submission was retracted.');
	await expect(page.getByText(STATUS_WORDS.en.retracted).first()).toBeVisible();
	await expect(page.getByRole('button', { name: 'Start again from this' })).toBeVisible();
	await expect(page.getByRole('region', { name: 'Submission log' })).toContainText('Retracted');
});

test('AC 38: a rejected Submission offers "Start again from this", which opens the new draft', async ({
	page
}, info) => {
	await signIn(page, address('persona', info), PATHS.en.submission(SUBMISSIONS.rejected));
	await expect(page.getByRole('button', { name: 'Retract this Submission' })).toHaveCount(0);

	await page.getByRole('button', { name: 'Start again from this' }).click();

	await expect(page).toHaveURL(/\/en\/contributions\/\d+\/edit$/);
});

test('AC 38: a draft can be deleted after a confirmation', async ({ page }, info) => {
	await signIn(page, address('persona', info), PATHS.en.submission(SUBMISSIONS.draft));

	await page.getByText('Delete this draft', { exact: true }).click();
	await page.getByRole('button', { name: 'Yes, delete the draft' }).click();

	await expect(page).toHaveURL(PATHS.en.mine);
	await expect(page.getByRole('link', { name: /Submission 101/ })).toHaveCount(0);
});

test('AC 38: a Submission that is not the User’s answers 404', async ({ page }, info) => {
	await signIn(page, address('persona', info), PATHS.en.mine);

	const response = await page.goto(PATHS.en.submission(999));

	expect(response?.status()).toBe(404);
});

test('AC 40: the Submission page is in Italian under its own address, with the reason in Italian', async ({
	page
}, info) => {
	await signIn(
		page,
		address('persona', info),
		PATHS.it.submission(SUBMISSIONS.changes_requested),
		'it'
	);

	await expect(page.getByRole('heading', { level: 1 })).toHaveText('Nuova opera (contributo 103)');
	await expect(page.getByText(STATUS_WORDS.it.changes_requested).first()).toBeVisible();
	const log = page.getByRole('region', { name: 'Cronologia del contributo' });
	await expect(log).toContainText('Da un Moderatore');
	await expect(log).toContainText('Motivo: Duplicato');
	await expect(log).not.toContainText(/\bModerator\b/);
	await expect(page.getByText('Ritira questo contributo', { exact: true })).toBeVisible();
});

test('AC 40: My contributions and the hub are in Italian under their own addresses', async ({
	page
}, info) => {
	await signIn(page, address('persona', info), PATHS.it.mine, 'it');
	await expect(page.getByRole('heading', { level: 1 })).toHaveText('I miei contributi');
	for (const [status, words] of Object.entries(STATUS_WORDS.it)) {
		const id = SUBMISSIONS[status as keyof typeof STATUS_WORDS.it];
		await expect(
			page
				.getByRole('row')
				.filter({ hasText: `contributo ${id}` })
				.first()
		).toContainText(words);
	}

	await page.goto(PATHS.it.hub);
	await expect(page.getByRole('heading', { level: 1 })).toHaveText('Contribuisci');
	await expect(page.getByRole('button', { name: 'Inizia una nuova opera' })).toBeVisible();
});

for (const language of ['it', 'en'] as const) {
	for (const colorScheme of ['light', 'dark'] as const) {
		test(`AC 41: the ${language} hub and My contributions pass axe in the ${colorScheme} theme`, async ({
			page
		}, info) => {
			await page.emulateMedia({ colorScheme });
			await signIn(page, address('persona', info), PATHS[language].hub, language);
			await expectNoViolations(page);

			await page.goto(PATHS[language].mine);
			await expectNoViolations(page);
		});

		test(`AC 41: the ${language} empty My contributions passes axe in the ${colorScheme} theme`, async ({
			page
		}, info) => {
			await page.emulateMedia({ colorScheme });
			await signIn(page, address('persona-vuota', info), PATHS[language].mine, language);
			await expectNoViolations(page);
		});
	}

	test(`AC 41: the ${language} Submission page passes axe in every state`, async ({
		page
	}, info) => {
		await signIn(page, address('persona', info), PATHS[language].mine, language);
		for (const id of Object.values(SUBMISSIONS)) {
			await page.goto(PATHS[language].submission(id));
			await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
			await expectNoViolations(page);
		}
	});
}

test('AC 41: the Submission page passes axe in the dark theme, with a confirmation open', async ({
	page
}, info) => {
	await page.emulateMedia({ colorScheme: 'dark' });
	await signIn(page, address('persona', info), PATHS.en.submission(SUBMISSIONS.submitted));
	await page.getByText('Retract this Submission', { exact: true }).click();

	await expectNoViolations(page);
});
