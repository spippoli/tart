import AxeBuilder from '@axe-core/playwright';
import type { Page } from '@playwright/test';
import { expect, hydrated, test } from './test';

// The Invitations page (Contribution and moderation spec, Invitations). The third server of
// the Playwright configuration is an Instance with `registration = invite`; the stand-in API
// keeps its list (e2e/mock-api.ts): a pending Invitation of the Operator, a used one, and an
// expired one. The API's own tests cover redemption, expiry, and revocation.

const INVITE = 'http://localhost:4275';
const CODE = '123456';
const WCAG_22_AA = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];

const PAGES = {
	it: { path: '/it/moderazione/inviti', signIn: '/it/accedi' },
	en: { path: '/en/moderation/invitations', signIn: '/en/sign-in' }
} as const;

/** An address of its own for each test and project, since the stand-in API keeps state. */
function address(local: string, info: { project: { name: string }; title: string }) {
	const slug = `${info.project.name}-${info.title}`.toLowerCase().replace(/[^a-z0-9]+/g, '-');
	return `${local}-${slug}@example.org`.slice(-120);
}

async function signIn(page: Page, email: string, language: 'it' | 'en' = 'en') {
	const labels = {
		it: { email: 'Indirizzo email', send: 'Invia il codice', code: 'Codice', submit: 'Accedi' },
		en: { email: 'Email address', send: 'Send the code', code: 'Code', submit: 'Sign in' }
	}[language];
	const next = PAGES[language].path;
	await page.goto(`${INVITE}${PAGES[language].signIn}?next=${encodeURIComponent(next)}`);
	await page.getByLabel(labels.email).fill(email);
	await page.getByRole('button', { name: labels.send }).click();
	await page.getByLabel(labels.code, { exact: true }).fill(CODE);
	await page.getByRole('main').getByRole('button', { name: labels.submit, exact: true }).click();
	await expect(page).toHaveURL(`${INVITE}${next}`);
	await hydrated(page);
}

test('AC 36: the Moderator sees every Invitation with its status and issuer', async ({
	page
}, info) => {
	await signIn(page, address('moderatrice', info));

	await expect(page).toHaveURL(`${INVITE}${PAGES.en.path}`);
	await expect(page.getByRole('heading', { level: 1 })).toHaveText('Invitations');
	const rows = page.getByRole('row');
	const operator = rows.filter({ hasText: 'dal-terminale@example.org' });
	await expect(operator).toContainText('Pending');
	await expect(operator).toContainText('The Operator');
	const used = rows.filter({ hasText: 'usata@example.org' });
	await expect(used).toContainText('Used');
	await expect(used).toContainText('Altra Moderatrice (User #7)');
	await expect(rows.filter({ hasText: 'scaduta@example.org' })).toContainText('Expired');
	await expect(
		page.getByRole('navigation', { name: 'Moderation sections' }).getByRole('link', {
			name: 'Invitations'
		})
	).toHaveAttribute('aria-current', 'page');
});

test('AC 36: issuing an Invitation says it in words and offers the link to copy', async ({
	page
}, info) => {
	await signIn(page, address('moderatrice', info));
	const email = address('invitata', info);

	await page.getByLabel('Email address to invite').fill(email);
	await page.getByRole('button', { name: 'Create the Invitation' }).click();

	await expect(page.getByRole('status').filter({ hasText: 'Invitation created' })).toContainText(
		email
	);
	await expect(page.getByLabel('Link to the registration page')).toHaveValue(
		`${INVITE}/en/sign-in`
	);
	const row = page.getByRole('row').filter({ hasText: email });
	await expect(row).toContainText('Pending');
	await expect(row).toContainText('Moderatrice di prova (User #1)');

	await page.getByLabel('Email address to invite').fill(email);
	await page.getByRole('button', { name: 'Create the Invitation' }).click();
	await expect(page.getByRole('alert')).toHaveText(
		'This address already has a pending Invitation.'
	);
	await expect(page.getByLabel('Email address to invite')).toHaveAttribute('aria-invalid', 'true');
});

test('AC 36: a pending Invitation can be revoked', async ({ page }, info) => {
	await signIn(page, address('moderatrice', info));
	const email = address('ripensata', info);
	await page.getByLabel('Email address to invite').fill(email);
	await page.getByRole('button', { name: 'Create the Invitation' }).click();
	const row = page.getByRole('row').filter({ hasText: email });
	await expect(row).toContainText('Pending');

	await row.getByRole('button', { name: 'Revoke' }).click();

	await expect(page.getByRole('status').filter({ hasText: 'revoked' })).toHaveText(
		`Invitation for ${email} revoked.`
	);
	await expect(row).toContainText('Revoked');
	await expect(row.getByRole('button')).toHaveCount(0);
	await expect(
		page.getByRole('row').filter({ hasText: 'usata@example.org' }).getByRole('button')
	).toHaveCount(0);
});

test('AC 36: the page is in Italian under its own address', async ({ page }, info) => {
	await signIn(page, address('moderatrice', info), 'it');

	await expect(page).toHaveURL(`${INVITE}/it/moderazione/inviti`);
	await expect(page.getByRole('heading', { level: 1 })).toHaveText('Inviti');
	await expect(page.getByRole('row').filter({ hasText: 'usata@example.org' })).toContainText(
		'Altra Moderatrice (Utente n. 7)'
	);
	await expect(page.getByLabel('Link alla pagina di registrazione')).toHaveCount(0);
	await page.getByLabel('Indirizzo email da invitare').fill(address('invitata', info));
	await page.getByRole('button', { name: "Crea l'invito" }).click();
	await expect(page.getByLabel('Link alla pagina di registrazione')).toHaveValue(
		`${INVITE}/it/accedi`
	);
});

test('AC 36: a User who is not a Moderator is refused', async ({ page }, info) => {
	await signIn(page, address('persona', info));

	await page.goto(`${INVITE}${PAGES.en.path}`);
	await expect(page.getByRole('heading', { level: 1 })).toHaveText('Access denied');
});

test('AC 36: an anonymous visitor is sent to sign-in and comes back', async ({ page }) => {
	await page.goto(`${INVITE}${PAGES.en.path}`);

	await expect(page).toHaveURL(/\/en\/sign-in\?next=/);
});

test('AC 36: the page answers 404 and the menu entry is absent unless registration is invite', async ({
	page
}, info) => {
	await page.goto('/en/sign-in');
	await page.getByLabel('Email address').fill(address('moderatrice', info));
	await page.getByRole('button', { name: 'Send the code' }).click();
	await page.getByLabel('Code', { exact: true }).fill(CODE);
	await page.getByRole('main').getByRole('button', { name: 'Sign in', exact: true }).click();

	const response = await page.goto(PAGES.en.path);
	expect(response?.status()).toBe(404);
	await page.goto('/en/moderation');
	await expect(page.getByRole('heading', { level: 1 })).toHaveText('Moderation queue');
	const sections = page.getByRole('navigation', { name: 'Moderation sections' });
	await expect(sections.getByRole('link', { name: 'Queue' })).toBeVisible();
	await expect(sections.getByRole('link', { name: 'Invitations' })).toHaveCount(0);
});

for (const language of ['it', 'en'] as const) {
	for (const colorScheme of ['light', 'dark'] as const) {
		test(`AC 36: the ${language} Invitations page passes axe in the ${colorScheme} theme`, async ({
			page
		}, info) => {
			await page.emulateMedia({ colorScheme });
			await signIn(page, address('moderatrice', info), language);
			await page
				.getByLabel(/Email address to invite|Indirizzo email da invitare/)
				.fill(address('invitata', info));
			await page
				.getByRole('button')
				.filter({ hasText: /Create the Invitation|Crea l'invito/ })
				.click();
			await expect(page.locator('#invitation-link')).toBeVisible({ timeout: 15_000 });

			const results = await new AxeBuilder({ page }).withTags(WCAG_22_AA).analyze();
			expect(results.violations).toEqual([]);
		});
	}
}
