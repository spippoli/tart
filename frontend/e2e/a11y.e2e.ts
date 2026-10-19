import AxeBuilder from '@axe-core/playwright';
import { expect, test } from './test';

const WCAG_22_AA = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];

const shellPages = {
	it: [
		'/it/',
		'/it/informazioni',
		'/it/informazioni/linee-guida',
		'/it/informazioni/termini',
		'/it/informazioni/privacy',
		'/it/informazioni/contatti',
		'/it/informazioni/licenza-dati',
		'/it/informazioni/tart',
		'/it/accedi',
		'/it/pagina-inesistente'
	],
	en: [
		'/en/',
		'/en/about',
		'/en/about/guidelines',
		'/en/about/terms',
		'/en/about/privacy',
		'/en/about/contact',
		'/en/about/data-licence',
		'/en/about/tart',
		'/en/sign-in',
		'/en/no-such-page'
	]
};

// Foundations criterion 37, at the desktop and mobile widths of the two projects.
for (const [language, paths] of Object.entries(shellPages)) {
	for (const colorScheme of ['light', 'dark'] as const) {
		test(`AC 37: ${language} shell pages pass axe in the ${colorScheme} theme`, async ({
			page,
			isMobile
		}) => {
			await page.emulateMedia({ colorScheme });
			for (const path of paths) {
				await page.goto(path);
				const states = [false];
				if (isMobile) states.push(true);
				for (const menuOpen of states) {
					if (menuOpen) await page.getByRole('button', { name: /^Menu$/ }).click();
					const results = await new AxeBuilder({ page }).withTags(WCAG_22_AA).analyze();
					expect(results.violations, `${path}${menuOpen ? ' (menu open)' : ''}`).toEqual([]);
				}
			}
		});
	}
}

test('AC 37: every shell control is keyboard-operable with a visible focus indicator', async ({
	page
}) => {
	await page.goto('/en/about');
	// Hydration collapses the narrow-screen navigation; tabbing must start after it.
	await expect(page.locator('header.site-header.enhanced')).toBeAttached();
	const visited: string[] = [];
	for (let step = 0; step < 40; step++) {
		await page.keyboard.press('Tab');
		const focused = await page.evaluate(() => {
			const element = document.activeElement as HTMLElement | null;
			if (!element || element === document.body) return null;
			const style = getComputedStyle(element);
			return {
				name: element.textContent?.trim() || element.getAttribute('aria-label') || element.id,
				outline: style.outlineStyle !== 'none' && parseFloat(style.outlineWidth) >= 2,
				collapsed: element.getAttribute('aria-expanded') === 'false'
			};
		});
		if (focused === null) break;
		expect(focused.outline, `focus indicator on ${focused.name}`).toBe(true);
		visited.push(focused.name);
		// On narrow screens, open the Menu from the keyboard and go on into it.
		if (focused.collapsed) await page.keyboard.press('Enter');
	}
	expect(visited[0]).toBe('Skip to content');
	for (const control of ['About', 'Search', 'Italiano', 'Sign in', 'Powered by TART 0.0.0']) {
		expect(visited).toContain(control);
	}
});

// The sign-in steps after the first, and the pages of a signed-in User.
for (const colorScheme of ['light', 'dark'] as const) {
	test(`AC 37: the sign-in steps and the signed-in shell pass axe in the ${colorScheme} theme`, async ({
		page
	}, info) => {
		await page.emulateMedia({ colorScheme });
		const check = async (label: string) => {
			const results = await new AxeBuilder({ page }).withTags(WCAG_22_AA).analyze();
			expect(results.violations, label).toEqual([]);
		};
		const email = `nuova-${info.project.name}-${colorScheme}@example.org`;
		await page.goto('/en/sign-in');
		await page.getByLabel('Email address').fill('not-an-address');
		await page.getByRole('button', { name: 'Send the code' }).click();
		await check('email step with an error');
		await page.getByLabel('Email address').fill(email);
		await page.getByRole('button', { name: 'Send the code' }).click();
		await check('code step');
		await page.getByLabel('Code', { exact: true }).fill('000000');
		await page.getByRole('main').getByRole('button', { name: 'Sign in' }).click();
		await check('code step with an error');
		await page.getByLabel('Code', { exact: true }).fill('123456');
		await page.getByRole('main').getByRole('button', { name: 'Sign in' }).click();
		await check('registration step');
		await page.getByLabel('Display name').fill('Utente eliminato 3');
		await page.getByLabel(/at least 14 years old/).check();
		await page.getByRole('button', { name: 'Create the account' }).click();
		await check('registration step with an error');
		await page.getByLabel('Display name').fill('Lettrice di prova');
		await page.getByLabel(/at least 14 years old/).check();
		await page.getByRole('button', { name: 'Create the account' }).click();
		await expect(page).toHaveURL('/en/');
		await check('signed-in home page');
		await page.goto('/it/moderazione');
		await check('403 page');
	});
}
