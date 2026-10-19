import AxeBuilder from '@axe-core/playwright';
import type { Page } from '@playwright/test';
import { expect, hydrated, test } from './test';

// The Account page (Foundations spec, 2. Account and Email change): display name,
// preferred language, email change, and Sign out everywhere. The stand-in API takes
// `123456` for every code and treats `presa@…` addresses as in use (e2e/mock-api.ts);
// the API's own tests check the emails and the codes.

const WCAG_22_AA = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];

function address(local: string, info: { project: { name: string }; title: string }) {
	const slug = `${info.project.name}-${info.title}`.toLowerCase().replace(/[^a-z0-9]+/g, '-');
	return `${local}-${slug}@example.org`.slice(-120);
}

async function signIn(page: Page, email: string, language: 'it' | 'en' = 'en') {
	const labels = {
		it: { email: 'Indirizzo email', send: 'Invia il codice', code: 'Codice', submit: 'Accedi' },
		en: { email: 'Email address', send: 'Send the code', code: 'Code', submit: 'Sign in' }
	}[language];
	const next = `/${language}/account`;
	await page.goto(
		`/${language}/${language === 'it' ? 'accedi' : 'sign-in'}?next=${encodeURIComponent(next)}`
	);
	await page.getByLabel(labels.email).fill(email);
	await page.getByRole('button', { name: labels.send }).click();
	await page.getByLabel(labels.code, { exact: true }).fill('123456');
	await page.getByRole('main').getByRole('button', { name: labels.submit, exact: true }).click();
	await expect(page).toHaveURL(next);
	await hydrated(page);
}

const section = (page: Page, name: string) => page.getByRole('region', { name });

async function requestEmailChange(page: Page, email: string) {
	const region = section(page, 'Email address');
	await region.getByLabel('New email address').fill(email);
	await region.getByRole('button', { name: 'Send the code' }).click();
}

test('AC 55: a new display name is saved and shown at once', async ({ page }, info) => {
	await signIn(page, address('persona', info));
	const region = section(page, 'Display name');
	await expect(region.getByLabel('Display name')).toHaveValue('Persona di prova');

	await region.getByLabel('Display name').fill('  Nuova firma ');
	await region.getByRole('button', { name: 'Save the name' }).click();

	await expect(region.getByRole('status')).toHaveText('Display name saved.');
	await expect(page.getByRole('banner')).toContainText('Nuova firma');
	await page.reload();
	await expect(region.getByLabel('Display name')).toHaveValue('Nuova firma');
});

test('a display name that breaks the rules is said in words on the field', async ({
	page
}, info) => {
	await signIn(page, address('persona', info));
	const region = section(page, 'Display name');

	await region.getByLabel('Display name').fill('Deleted user 7');
	await region.getByRole('button', { name: 'Save the name' }).click();

	await expect(region.getByRole('alert')).toHaveText(
		'This display name is reserved: choose another one.'
	);
	await expect(region.getByLabel('Display name')).toHaveAttribute('aria-invalid', 'true');
	await expect(region.getByLabel('Display name')).toHaveValue('Deleted user 7');
});

test('the preferred language is saved', async ({ page }, info) => {
	await signIn(page, address('persona', info));
	const region = section(page, 'Language');
	await expect(region.getByLabel('Preferred language')).toHaveValue('it');

	await region.getByLabel('Preferred language').selectOption('en');
	await region.getByRole('button', { name: 'Save the language' }).click();

	await expect(region.getByRole('status')).toHaveText('Preferred language saved.');
	await page.reload();
	await expect(region.getByLabel('Preferred language')).toHaveValue('en');
});

test('AC 56: the address changes only once the code sent to it is entered', async ({
	page,
	context
}, info) => {
	const old = address('persona-vecchia', info);
	const fresh = address('nuova', info);
	await signIn(page, old);
	const region = section(page, 'Email address');
	await expect(region).toContainText(`Your address is ${old}.`);

	await requestEmailChange(page, fresh);

	await expect(region.getByRole('status')).toHaveText(
		`We have sent an email to ${fresh}. Enter the 6-digit code it contains: it is valid for 10 minutes.`
	);
	await expect(region.getByLabel('Code', { exact: true })).toBeFocused();
	await page.reload();
	await expect(region).toContainText(`Your address is ${old}.`);

	await requestEmailChange(page, fresh);
	await region.getByLabel('Code', { exact: true }).fill('123456');
	await region.getByRole('button', { name: 'Change the address' }).click();

	await expect(region.getByRole('status')).toHaveText(`Email address changed to ${fresh}.`);
	await expect(region).toContainText(`Your address is ${fresh}.`);

	await context.clearCookies();
	await signIn(page, fresh);
	await expect(region).toContainText(`Your address is ${fresh}.`);
});

test('a wrong email change code is said in words on the field', async ({ page }, info) => {
	await signIn(page, address('persona', info));
	const region = section(page, 'Email address');
	await requestEmailChange(page, address('nuova', info));

	await region.getByLabel('Code', { exact: true }).fill('000000');
	await region.getByRole('button', { name: 'Change the address' }).click();

	await expect(region.getByRole('alert')).toHaveText(
		'The code is wrong or has expired. Check it, or ask for a new code.'
	);
	await expect(region.getByLabel('Code', { exact: true })).toHaveAttribute('aria-invalid', 'true');
	await expect(region.getByLabel('Code', { exact: true })).toBeFocused();
});

test('AC 57: an address in use gets the same answer as a free one', async ({ page }, info) => {
	await signIn(page, address('persona', info));
	const region = section(page, 'Email address');
	const taken = address('presa', info);

	await requestEmailChange(page, taken);

	await expect(region.getByRole('status')).toHaveText(
		`We have sent an email to ${taken}. Enter the 6-digit code it contains: it is valid for 10 minutes.`
	);
	await expect(region.getByRole('alert')).toHaveCount(0);
	await expect(region.getByLabel('Code', { exact: true })).toBeVisible();
});

test('the current address is refused as a new one', async ({ page }, info) => {
	const email = address('persona', info);
	await signIn(page, email);
	const region = section(page, 'Email address');

	await requestEmailChange(page, email);

	await expect(region.getByRole('alert')).toHaveText('This is already your email address.');
	await expect(region.getByLabel('New email address')).toHaveAttribute('aria-invalid', 'true');
});

test('Sign out everywhere ends the sessions on other devices too', async ({
	page,
	browser
}, info) => {
	const email = address('persona', info);
	const other = await browser.newPage();
	await signIn(other, email);
	await signIn(page, email);

	await section(page, 'Sign out everywhere')
		.getByRole('button', { name: 'Sign out everywhere' })
		.click();

	await expect(page).toHaveURL('/en/');
	for (const device of [page, other]) {
		await device.goto('/en/account');
		await expect(device).toHaveURL('/en/sign-in?next=%2Fen%2Faccount');
	}
	await other.close();
});

// Foundations criterion 37 for the Account page, in both UI languages and themes.
for (const language of ['it', 'en'] as const) {
	for (const colorScheme of ['light', 'dark'] as const) {
		test(`AC 37: the ${language} Account page passes axe in the ${colorScheme} theme`, async ({
			page
		}, info) => {
			await page.emulateMedia({ colorScheme });
			await signIn(page, address(`persona-${language}-${colorScheme}`, info), language);
			const check = async (label: string) => {
				const results = await new AxeBuilder({ page }).withTags(WCAG_22_AA).analyze();
				expect(results.violations, label).toEqual([]);
			};
			const labels = {
				it: {
					name: 'Nome visualizzato',
					save: 'Salva il nome',
					email: 'Nuovo indirizzo email',
					send: 'Invia il codice'
				},
				en: {
					name: 'Display name',
					save: 'Save the name',
					email: 'New email address',
					send: 'Send the code'
				}
			}[language];
			await check('settings');
			await page.getByRole('textbox', { name: labels.name }).fill('');
			await page.getByRole('textbox', { name: labels.name }).fill(' ');
			await page.getByRole('button', { name: labels.save }).click();
			await expect(page.getByRole('alert')).toBeVisible();
			await check('display name error');
			await page.getByLabel(labels.email).fill(address('nuova', info));
			await page.getByRole('button', { name: labels.send }).click();
			await expect(
				page.getByLabel(language === 'it' ? 'Codice' : 'Code', { exact: true })
			).toBeVisible();
			await check('email code step');
		});
	}
}
