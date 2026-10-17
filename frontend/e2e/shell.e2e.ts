import { expect, test } from './test';

// The second server's Instance enables Italian only (playwright.config.ts).
const ITALIAN_ONLY = 'http://localhost:4274';

test.describe('AC 29: the root redirect', () => {
	const rootLanguage = async (
		request: import('@playwright/test').APIRequestContext,
		headers: Record<string, string>
	) => {
		const response = await request.get('/', { headers, maxRedirects: 0 });
		expect(response.status()).toBe(302);
		return response.headers()['location'];
	};

	test('follows the cookie, then Accept-Language, then the Instance default', async ({
		request
	}) => {
		expect(await rootLanguage(request, { Cookie: 'ui_language=en', 'Accept-Language': 'it' })).toBe(
			'/en/'
		);
		expect(await rootLanguage(request, { 'Accept-Language': 'en-GB,it;q=0.5' })).toBe('/en/');
		expect(await rootLanguage(request, { 'Accept-Language': 'de' })).toBe('/it/');
	});

	test('is the only page without a UI-language prefix', async ({ request }) => {
		expect((await request.get('/about', { maxRedirects: 0 })).status()).toBe(404);
		expect((await request.get('/it/informazioni')).status()).toBe(200);
		expect((await request.get('/en/about')).status()).toBe(200);
	});
});

test.describe('AC 30: enabled UI languages', () => {
	test('a disabled UI language prefix answers 404, in the Instance default', async ({ page }) => {
		const response = await page.goto(`${ITALIAN_ONLY}/en/about`);
		expect(response?.status()).toBe(404);
		await expect(page.locator('html')).toHaveAttribute('lang', 'it');
		await expect(page.getByRole('heading', { level: 1 })).toHaveText('Pagina non trovata');
		expect((await page.goto(`${ITALIAN_ONLY}/it/informazioni`))?.status()).toBe(200);
	});

	test('the switcher lists only the enabled UI languages', async ({ page, isMobile }) => {
		await page.goto(`${ITALIAN_ONLY}/it/informazioni`);
		await expect(page.getByRole('navigation', { name: 'Lingua' })).toHaveCount(0);
		await expect(page.locator('link[rel="alternate"][hreflang="en"]')).toHaveCount(0);

		await page.goto('/it/informazioni');
		if (isMobile) await page.getByRole('button', { name: 'Menu' }).click();
		const switcher = page.getByRole('navigation', { name: 'Lingua' });
		await expect(switcher.getByRole('link')).toHaveText(['Italiano', 'English']);
	});

	test('the switcher keeps the current page and remembers the choice', async ({
		page,
		isMobile
	}) => {
		await page.goto('/it/informazioni/contatti');
		if (isMobile) await page.getByRole('button', { name: 'Menu' }).click();
		await page.getByRole('link', { name: 'English' }).click();
		await expect(page).toHaveURL('/en/about/contact');
		await expect(page.locator('html')).toHaveAttribute('lang', 'en');
		await expect(page.getByRole('heading', { level: 1 })).toHaveText('Contact');

		await page.goto('/');
		await expect(page).toHaveURL('/en/');
	});
});

test('AC 31: every page carries hreflang alternates and an x-default', async ({ page }) => {
	for (const path of ['/it/', '/en/about/data-licence', '/it/pagina-inesistente']) {
		await page.goto(path);
		const alternates = await page
			.locator('link[rel="alternate"]')
			.evaluateAll((links) =>
				links.map((link) => [link.getAttribute('hreflang'), link.getAttribute('href')])
			);
		const origin = new URL(page.url()).origin;
		expect(alternates.map(([language]) => language)).toEqual(['it', 'en', 'x-default']);
		expect(alternates.at(-1)?.[1]).toBe(`${origin}/`);
	}
	await page.goto('/en/about/data-licence');
	await expect(page.locator('link[hreflang="it"]')).toHaveAttribute(
		'href',
		/\/it\/informazioni\/licenza-dati$/
	);
});

test('AC 33: content in the Content language carries its own lang', async ({ page }) => {
	await page.goto('/en/about');
	await expect(page.locator('html')).toHaveAttribute('lang', 'en');
	await expect(page.locator('.archive-name')).toHaveAttribute('lang', 'it');
	const operatorText = page.locator('main .prose');
	await expect(operatorText).toHaveAttribute('lang', 'it');
	await expect(operatorText).toHaveAttribute('dir', 'ltr');
	await expect(operatorText.getByRole('heading', { name: 'Chi siamo' })).toBeVisible();
	await expect(page.getByText('This text is in Italian.')).toBeVisible();

	await page.goto('/it/informazioni/termini');
	await expect(page.locator('main .prose')).toHaveAttribute('lang', 'it');
});

test('AC 35: header identity, footer, and browser title', async ({ page }) => {
	await page.goto('/en/about');
	await expect(page).toHaveTitle("About — Archivio di prova dell'arte urbana");

	const header = page.getByRole('banner');
	await expect(
		header.getByRole('img', { name: "Archivio di prova dell'arte urbana" })
	).toBeVisible();
	await expect(
		header.getByText("Archivio di prova dell'arte urbana", { exact: true })
	).toBeVisible();

	const footer = page.getByRole('contentinfo');
	await expect(footer.getByRole('link', { name: 'Powered by TART 0.0.0' })).toHaveAttribute(
		'href',
		'/en/about/tart'
	);
	await expect(footer.getByRole('link', { name: 'Data licence: CC BY-SA 4.0' })).toHaveAttribute(
		'href',
		'/en/about/data-licence'
	);
	await expect(footer.getByRole('link', { name: 'Contact' })).toHaveAttribute(
		'href',
		'/en/about/contact'
	);
	await expect(footer.getByRole('link', { name: 'Terms of use' })).toHaveAttribute(
		'href',
		'/en/about/terms'
	);
	await expect(footer.getByRole('link', { name: 'Privacy' })).toHaveAttribute(
		'href',
		'/en/about/privacy'
	);

	await page.goto('/it/informazioni/tart');
	await expect(page).toHaveTitle("Informazioni su TART — Archivio di prova dell'arte urbana");
});

test.describe('AC 36: navigation without hover', () => {
	test('narrow screens open the navigation from a labelled Menu button', async ({
		page,
		isMobile
	}) => {
		test.skip(!isMobile, 'narrow screens only');
		await page.goto('/it/');
		const menu = page.getByRole('button', { name: 'Menu' });
		const navigation = page.getByRole('navigation', { name: 'Principale' });
		await expect(menu).toHaveAttribute('aria-expanded', 'false');
		await expect(navigation).toBeHidden();

		await menu.focus();
		await page.keyboard.press('Enter');
		await expect(menu).toHaveAttribute('aria-expanded', 'true');
		await expect(navigation).toBeVisible();

		await page.keyboard.press('Tab');
		await expect(navigation.getByRole('link', { name: 'Esplora' })).toBeFocused();
		await page.keyboard.press('Escape');
		await expect(navigation).toBeHidden();
		await expect(menu).toBeFocused();
	});

	test('wide screens show the navigation with no Menu button', async ({ page, isMobile }) => {
		test.skip(isMobile, 'wide screens only');
		await page.goto('/it/');
		await expect(page.getByRole('button', { name: 'Menu' })).toHaveCount(0);
		await expect(page.getByRole('navigation', { name: 'Principale' })).toBeVisible();
	});
});

test('the platform backgrounds follow prefers-color-scheme', async ({ page }) => {
	await page.goto('/it/');
	const background = () => page.evaluate(() => getComputedStyle(document.body).backgroundColor);
	await page.emulateMedia({ colorScheme: 'light' });
	expect(await background()).toBe('rgb(255, 255, 255)');
	await page.emulateMedia({ colorScheme: 'dark' });
	expect(await background()).toBe('rgb(18, 18, 18)');
});

test('the About hub lists only the Operator texts that exist', async ({ page }) => {
	await page.goto('/it/informazioni');
	const subpages = page.getByRole('navigation', { name: 'Pagine informative' }).getByRole('link');
	await expect(subpages).toHaveText([
		'Linee guida editoriali',
		"Termini d'uso",
		'Informativa sulla privacy',
		'Contatti',
		'Licenza dei dati',
		'Informazioni su TART'
	]);
	expect((await page.goto('/it/informazioni/policy-contributi'))?.status()).toBe(404);
});
