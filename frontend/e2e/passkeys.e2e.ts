import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';

// Passkeys on the Account page and the sign-in page (Foundations spec, 2), with
// Chromium's virtual authenticator standing in for a phone or laptop passkey. The
// stand-in API keeps passkeys by credential id (e2e/mock-api.ts).

const WCAG_22_AA = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];

function address(local: string, info: { project: { name: string }; title: string }) {
	const slug = `${info.project.name}-${info.title}`.toLowerCase().replace(/[^a-z0-9]+/g, '-');
	return `${local}-${slug}@example.org`.slice(-120);
}

/** A platform authenticator that verifies the user (a fingerprint, face, or PIN). */
async function addVirtualAuthenticator(page: Page) {
	const cdp = await page.context().newCDPSession(page);
	await cdp.send('WebAuthn.enable');
	await cdp.send('WebAuthn.addVirtualAuthenticator', {
		options: {
			protocol: 'ctap2',
			transport: 'internal',
			hasResidentKey: true,
			hasUserVerification: true,
			isUserVerified: true,
			automaticPresenceSimulation: true
		}
	});
}

async function signInWithCode(page: Page, email: string, next = '/en/account') {
	await page.goto(`/en/sign-in?next=${encodeURIComponent(next)}`);
	await page.getByLabel('Email address').fill(email);
	await page.getByRole('button', { name: 'Send the code' }).click();
	await page.getByLabel('Code', { exact: true }).fill('123456');
	await page.getByRole('main').getByRole('button', { name: 'Sign in' }).click();
	await expect(page).toHaveURL(next);
}

async function addPasskey(page: Page, name: string) {
	await page.getByLabel('Passkey name').fill(name);
	await page.getByRole('button', { name: 'Add the passkey' }).click();
}

test('AC 12: a User adds a passkey on the Account page and then signs in with it', async ({
	page,
	context
}, info) => {
	await addVirtualAuthenticator(page);
	await signInWithCode(page, address('persona', info));
	await expect(page.getByText('You have not added any passkeys yet.')).toBeVisible();

	await addPasskey(page, 'Phone');

	await expect(page.getByRole('region', { name: 'Passkeys' }).getByRole('status')).toHaveText(
		'Passkey “Phone” added: next time you can sign in with it.'
	);
	const item = page.getByRole('listitem').filter({ hasText: 'Phone' });
	await expect(item).toContainText(/Added on \w+ \d{1,2}, \d{4}/);

	await context.clearCookies();
	await page.goto('/en/sign-in?next=%2Fen%2Faccount');
	await page.getByRole('button', { name: 'Sign in with a passkey' }).click();

	await expect(page).toHaveURL('/en/account');
	await expect(page.getByRole('listitem').filter({ hasText: 'Phone' })).toBeVisible();
});

test('a passkey is removed from the Account page', async ({ page }, info) => {
	await addVirtualAuthenticator(page);
	await signInWithCode(page, address('persona', info));
	await addPasskey(page, 'Laptop');
	await expect(page.getByRole('listitem').filter({ hasText: 'Laptop' })).toBeVisible();

	const remove = page.getByRole('button', { name: 'Remove' });
	await expect(remove).toHaveAccessibleDescription('Laptop');
	await remove.click();

	await expect(page.getByRole('region', { name: 'Passkeys' }).getByRole('status')).toHaveText(
		'Passkey “Laptop” removed.'
	);
	await expect(page.getByText('You have not added any passkeys yet.')).toBeVisible();
});

test('a passkey name that is too long is said in words on the field', async ({ page }, info) => {
	await addVirtualAuthenticator(page);
	await signInWithCode(page, address('persona', info));

	await addPasskey(page, 'x'.repeat(41));

	await expect(page.getByRole('alert')).toHaveText(
		'The passkey name must be 1 to 40 characters long.'
	);
	await expect(page.getByLabel('Passkey name')).toHaveAttribute('aria-invalid', 'true');
});

test('a passkey that is not registered does not sign in', async ({ page }) => {
	await addVirtualAuthenticator(page);
	// A passkey the browser holds for this site, but which no account has.
	await page.goto('/en/sign-in');
	await page.evaluate(async () => {
		await navigator.credentials.create({
			publicKey: {
				rp: { id: 'localhost', name: 'Archivio di prova' },
				user: { id: new Uint8Array(8), name: 'nessuno', displayName: 'Nessuno' },
				challenge: new Uint8Array(32),
				pubKeyCredParams: [{ type: 'public-key', alg: -7 }],
				authenticatorSelection: { residentKey: 'required', userVerification: 'required' }
			}
		});
	});

	await page.getByRole('button', { name: 'Sign in with a passkey' }).click();

	await expect(page.getByRole('alert')).toHaveText(
		'Signing in with this passkey did not work. Try again, or sign in with the email code.'
	);
	await expect(page).toHaveURL('/en/sign-in');
	await expect(page.getByLabel('Email address')).not.toHaveAttribute('aria-invalid');
});

test('an anonymous user goes from the Account page to sign-in and back', async ({ page }, info) => {
	await page.goto('/it/account');

	await expect(page).toHaveURL('/it/accedi?next=%2Fit%2Faccount');
	await page.getByLabel('Indirizzo email').fill(address('persona', info));
	await page.getByRole('button', { name: 'Invia il codice' }).click();
	await page.getByLabel('Codice', { exact: true }).fill('123456');
	await page.getByRole('main').getByRole('button', { name: 'Accedi', exact: true }).click();

	await expect(page).toHaveURL('/it/account');
	await expect(page.getByRole('heading', { level: 2, name: 'Passkey' })).toBeVisible();
});

// Foundations criterion 37 for the Account page, in both UI languages and themes.
for (const language of ['it', 'en'] as const) {
	for (const colorScheme of ['light', 'dark'] as const) {
		test(`AC 37: the ${language} Account page passes axe in the ${colorScheme} theme`, async ({
			page
		}, info) => {
			await page.emulateMedia({ colorScheme });
			await addVirtualAuthenticator(page);
			await signInWithCode(page, address(`persona-${language}-${colorScheme}`, info));
			const check = async (label: string) => {
				const results = await new AxeBuilder({ page }).withTags(WCAG_22_AA).analyze();
				expect(results.violations, label).toEqual([]);
			};
			await page.goto(`/${language}/account`);
			await check('no passkeys');
			const labels = {
				it: { name: 'Nome della passkey', add: 'Aggiungi la passkey' },
				en: { name: 'Passkey name', add: 'Add the passkey' }
			}[language];
			await page.getByLabel(labels.name).fill('x'.repeat(41));
			await page.getByRole('button', { name: labels.add }).click();
			await expect(page.getByRole('alert')).toBeVisible();
			await check('name error');
			await page.getByLabel(labels.name).fill('Telefono');
			await page.getByRole('button', { name: labels.add }).click();
			await expect(page.getByRole('listitem').filter({ hasText: 'Telefono' })).toBeVisible();
			await check('one passkey, added');
		});
	}
}
