import { test } from '@playwright/test';
import { serveStyles } from './map-style';
test('loop', async ({ page }) => {
	test.setTimeout(240000);
	page.on('console', (m) => console.log('console', m.type(), m.text().slice(0, 200)));
	await serveStyles(page);
	for (let i = 0; i < 30; i++) {
		await page.goto('/en/');
		await page.waitForTimeout(1500);
		const state = await page.evaluate(() => ({
			region: !!document.querySelector('.explore-map'),
			state: document.querySelector<HTMLElement>('.map')?.dataset.state,
			legend: !!document.querySelector('.legend')
		}));
		console.log(i, JSON.stringify(state));
	}
});
