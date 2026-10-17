import { expect, test, type Page } from '@playwright/test';

// The stand-in API's rules (e2e/mock-api.ts): every code is 123456; `persona…` and
// `moderatrice…` (a Moderator) are Users; any other address registers.
const CODE = '123456';

/** An address of its own for each test and project, since the stand-in API keeps state. */
function address(local: string, info: { project: { name: string }; title: string }) {
	const slug = `${info.project.name}-${info.title}`.toLowerCase().replace(/[^a-z0-9]+/g, '-');
	return `${local}-${slug}@example.org`.slice(-120);
}

async function openMenu(page: Page, isMobile: boolean) {
	if (isMobile) await page.getByRole('button', { name: /^Menu$/ }).click();
}

async function signInOnPage(page: Page, email: string, language: 'it' | 'en' = 'en') {
	const labels = {
		en: { email: 'Email address', send: 'Send the code', code: 'Code', submit: 'Sign in' },
		it: { email: 'Indirizzo email', send: 'Invia il codice', code: 'Codice', submit: 'Accedi' }
	}[language];
	await page.getByLabel(labels.email).fill(email);
	await page.getByRole('button', { name: labels.send }).click();
	await page.getByLabel(labels.code, { exact: true }).fill(CODE);
	await page.getByRole('main').getByRole('button', { name: labels.submit }).click();
}

test('AC 16: sign-in returns to the page given in ?next=', async ({ page }, info) => {
	await page.goto('/en/sign-in?next=%2Fen%2Fabout%2Fcontact');
	await signInOnPage(page, address('persona', info));

	await expect(page).toHaveURL('/en/about/contact');
});

test('AC 16: the header sign-in link returns to the current page', async ({
	page,
	isMobile
}, info) => {
	await page.goto('/en/about/data-licence');
	await openMenu(page, isMobile);
	await page.getByRole('link', { name: 'Sign in' }).click();
	await expect(page).toHaveURL('/en/sign-in?next=%2Fen%2Fabout%2Fdata-licence');

	await signInOnPage(page, address('persona', info));

	await expect(page).toHaveURL('/en/about/data-licence');
});

test('?next= never leaves the site', async ({ page }, info) => {
	await page.goto('/en/sign-in?next=%2F%2Fevil.example%2F');
	await signInOnPage(page, address('persona', info));

	await expect(page).toHaveURL('/en/');
});

test.describe('AC 15: server-rendered pages show the signed-in state', () => {
	test.use({ javaScriptEnabled: false });

	test('without JavaScript, through sign-in and on every page after', async ({ page }, info) => {
		await page.goto('/it/accedi');
		await signInOnPage(page, address('persona', info), 'it');
		await expect(page).toHaveURL('/it/');

		await page.goto('/it/informazioni');
		const userMenu = page.getByRole('navigation', { name: 'Il tuo account' });
		await expect(userMenu).toContainText('Accesso come Persona di prova');
		await expect(userMenu.getByRole('link', { name: 'Account' })).toHaveAttribute(
			'href',
			'/it/account'
		);
		await expect(page.getByRole('link', { name: 'Accedi' })).toHaveCount(0);

		await userMenu.getByRole('button', { name: 'Esci' }).click();
		await expect(page).toHaveURL('/it/');
		await expect(page.getByRole('link', { name: 'Accedi' })).toBeVisible();
	});
});

test('the session cookie is HttpOnly and SameSite=Lax', async ({ page, context }, info) => {
	await page.goto('/en/sign-in');
	await signInOnPage(page, address('persona', info));
	await expect(page).toHaveURL('/en/');

	const session = (await context.cookies()).find((cookie) => cookie.name === 'tart_session');
	expect(session?.httpOnly).toBe(true);
	expect(session?.sameSite).toBe('Lax');
	expect(session?.path).toBe('/');
});

test.describe('AC 17: the Moderation area', () => {
	test('sends an anonymous user to sign-in and back', async ({ page }, info) => {
		await page.goto('/it/moderazione');
		await expect(page).toHaveURL('/it/accedi?next=%2Fit%2Fmoderazione');

		await signInOnPage(page, address('moderatrice', info), 'it');

		await expect(page).toHaveURL('/it/moderazione');
		await expect(page.getByRole('heading', { level: 1 })).toHaveText('Coda di moderazione');
	});

	test('answers a signed-in non-Moderator with a translated, explanatory 403', async ({
		page,
		isMobile
	}, info) => {
		await page.goto('/en/sign-in');
		await signInOnPage(page, address('persona', info));
		await expect(page).toHaveURL('/en/');

		const response = await page.goto('/en/moderation');

		expect(response?.status()).toBe(403);
		await expect(page.getByRole('heading', { level: 1 })).toHaveText('Access denied');
		await expect(page.getByText("This area is for the archive's Moderators")).toBeVisible();
		await openMenu(page, isMobile);
		await expect(page.getByRole('link', { name: 'Moderation' })).toHaveCount(0);
	});

	test('shows the Moderation menu entry only to Moderators', async ({ page, isMobile }, info) => {
		await page.goto('/it/');
		await openMenu(page, isMobile);
		await expect(page.getByRole('link', { name: 'Moderazione' })).toHaveCount(0);

		await page.goto('/it/accedi');
		await signInOnPage(page, address('moderatrice', info), 'it');
		await expect(page).toHaveURL('/it/');
		await openMenu(page, isMobile);
		await page
			.getByRole('navigation', { name: 'Principale' })
			.getByRole('link', {
				name: 'Moderazione'
			})
			.click();
		await expect(page).toHaveURL('/it/moderazione');
	});
});

test.describe('registration', () => {
	test('a new address registers with a display name and the age declaration', async ({
		page,
		isMobile
	}, info) => {
		await page.goto('/en/sign-in');
		await expect(
			page.getByText('If you do not have an account yet, you will create one')
		).toBeVisible();
		await signInOnPage(page, address('nuova', info));

		await expect(page.getByRole('heading', { name: 'Create your account' })).toBeVisible();
		await page.getByLabel('Display name').fill('Deleted user 12');
		await page.getByLabel('I declare that I am at least 14 years old').check();
		await page.getByRole('button', { name: 'Create the account' }).click();
		await expect(page.getByRole('alert')).toHaveText(
			'This display name is reserved: choose another one.'
		);
		await expect(page.getByLabel('Display name')).toHaveAttribute('aria-invalid', 'true');

		await page.getByLabel('Display name').fill('Lettrice di prova');
		await page.getByLabel('I declare that I am at least 14 years old').check();
		await page.getByRole('button', { name: 'Create the account' }).click();

		await expect(page).toHaveURL('/en/');
		await openMenu(page, isMobile);
		await expect(page.getByRole('navigation', { name: 'Your account' })).toContainText(
			'Signed in as Lettrice di prova'
		);
	});

	test('a wrong code is said in words, and the code can be asked again', async ({ page }, info) => {
		await page.goto('/en/sign-in');
		await page.getByLabel('Email address').fill(address('persona', info));
		await page.getByRole('button', { name: 'Send the code' }).click();
		await expect(page.getByText(/We have sent an email to persona-/)).toBeVisible();

		await page.getByLabel('Code', { exact: true }).fill('000000');
		await page.getByRole('main').getByRole('button', { name: 'Sign in' }).click();

		await expect(page.getByRole('alert')).toHaveText(
			'The code is wrong or has expired. Check it, or ask for a new code.'
		);
		await expect(page.getByRole('button', { name: 'Send a new code' })).toBeVisible();
		await expect(page.getByRole('link', { name: 'Use another email address' })).toBeVisible();
	});

	test('a rate-limited request says how long to wait, in the UI language', async ({ page }) => {
		await page.goto('/it/accedi');
		await page.getByLabel('Indirizzo email').fill('limitata@example.org');
		await page.getByRole('button', { name: 'Invia il codice' }).click();

		await expect(page.getByRole('alert')).toHaveText(
			'Troppe richieste di codice per questo indirizzo o questa rete. Potrai chiederne un altro tra 4 minuti.'
		);
	});

	test('the honeypot is hidden from view and labelled to be left empty', async ({ page }) => {
		await page.goto('/en/sign-in');
		const honeypot = page.getByLabel('Leave this field empty');

		await expect(honeypot).toHaveAttribute('tabindex', '-1');
		expect(
			await honeypot.evaluate((element) => element.getBoundingClientRect().right)
		).toBeLessThan(0);
	});
});
