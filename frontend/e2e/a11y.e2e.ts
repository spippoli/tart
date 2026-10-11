import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

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
