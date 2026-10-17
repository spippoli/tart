import { test as base, type Page } from '@playwright/test';

export { expect } from '@playwright/test';

/**
 * Playwright's `test`, with a `page` that waits for hydration after every `goto` and
 * `reload`. The pages are server-rendered, so a button or a form can be on screen before
 * the browser has hydrated it; a click then does nothing, or the wrong thing. The root
 * layout marks `<html data-hydrated="true">` once mounted (`src/routes/+layout.svelte`).
 *
 * A page with JavaScript disabled never hydrates, and a response that is not one of the
 * app's HTML pages (the stand-in API, a file) has no layout, so neither is waited for.
 */
export const test = base.extend({
	page: async ({ page, javaScriptEnabled }, use) => {
		if (javaScriptEnabled) {
			const goto = page.goto.bind(page);
			const reload = page.reload.bind(page);
			page.goto = async (...args) => {
				const response = await goto(...args);
				await afterNavigation(page, response);
				return response;
			};
			page.reload = async (...args) => {
				const response = await reload(...args);
				await afterNavigation(page, response);
				return response;
			};
		}
		await use(page);
	}
});

async function afterNavigation(page: Page, response: Awaited<ReturnType<Page['goto']>>) {
	const html = (await response?.headerValue('content-type'))?.startsWith('text/html');
	if (html) await hydrated(page);
}

/**
 * Waits for the page to be hydrated. A test calls it itself after a navigation it did not
 * start with `goto` or `reload`, such as a sign-in form that redirects: a form that is
 * clicked before hydration posts natively, and a reload of its answer posts it again.
 */
export async function hydrated(page: Page) {
	await page.locator('html[data-hydrated="true"]').waitFor({ state: 'attached' });
}
