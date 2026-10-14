/**
 * Discovery spec, the filter state, list entries, and the Archive view: criteria 4, 17,
 * 30, 31, 33, 34, 35, 38, 51, 52, and 59, against the stand-in API's thirty fictional
 * Artworks (`/api/discovery/artworks`). The query itself is the backend's tests; the
 * map is not here (Explore's list does not follow the viewport yet).
 */
import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';

const WCAG_22_AA = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];

const list = (page: Page) => page.getByRole('list', { name: 'Artwork list' });
const entries = (page: Page) => list(page).getByRole('article');
const isMobile = (info: { project: { name: string } }) => info.project.name === 'mobile';

/** The filter form is inline on a wide screen and in a dialog behind a button on a narrow one. */
async function openFilters(page: Page, mobile: boolean) {
	if (!mobile) return page.getByRole('search', { name: 'Filters' });
	await page.getByRole('button', { name: /^Filters/ }).click();
	return page.getByRole('dialog', { name: 'Filters' });
}

/** Applies what the form holds: at once on a wide screen, on "Show results" on a narrow one. */
async function apply(page: Page, mobile: boolean) {
	if (mobile) await page.getByRole('button', { name: 'Show results' }).click();
}

async function axe(page: Page, label: string) {
	const results = await new AxeBuilder({ page }).withTags(WCAG_22_AA).analyze();
	expect(results.violations, label).toEqual([]);
}

test.describe('with JavaScript', () => {
	// Criterion 4: disappeared Artworks appear by default; the group switches them off.
	test('AC 4: disappeared Artworks are listed by default and the group hides them', async ({
		page
	}, info) => {
		const mobile = isMobile(info);
		await page.goto('/en/archive');
		await expect(list(page)).toContainText('Covered');
		await expect(list(page)).toContainText('Destroyed');

		const form = await openFilters(page, mobile);
		await form.getByRole('checkbox', { name: 'disappeared', exact: true }).uncheck();
		await apply(page, mobile);

		await expect(page).toHaveURL(/condition=intact/);
		await expect(list(page)).not.toContainText('Covered');
		await expect(list(page)).not.toContainText('Destroyed');
		await expect(list(page)).toContainText('Intact');
	});

	// Criterion 17: the Archive view ignores the viewport, pages by 24, and shares the filter state.
	test('AC 17: the Archive view ignores the viewport, has pages of 24, and keeps filters across views', async ({
		page
	}) => {
		await page.goto('/en/archive?map=14/41.9/12.5&location=3');
		await expect(page).not.toHaveURL(/map=/);
		await expect(page).not.toHaveURL(/location=/);
		await expect(entries(page)).toHaveCount(24);
		await expect(page.getByRole('status')).toHaveText('30 artworks · page 1 of 2');

		await page.getByRole('link', { name: 'Page 2' }).click();
		await expect(page).toHaveURL(/page=2/);
		await expect(entries(page)).toHaveCount(6);
		await expect(page.getByRole('status')).toHaveText('30 artworks · page 2 of 2');

		// Filters travel to Explore with the entry's "Show on map" link; the viewport and page do not.
		await page.goto('/en/archive?type=stencil&map=14/41.9/12.5');
		const show = page.getByRole('link', { name: 'Show on map: Opera di prova 01' });
		await expect(show).toHaveAttribute('href', /^\/en\/\?type=stencil&location=200$/);
	});

	// Criterion 30: live apply on a wide screen; the dialog on a narrow one.
	test('AC 30: changes apply live without moving focus, or on "Show results" returning focus', async ({
		page
	}, info) => {
		const mobile = isMobile(info);
		await page.goto('/en/archive');
		const form = await openFilters(page, mobile);
		const stencil = form.getByRole('checkbox', { name: 'Stencil' });
		await stencil.check();

		if (mobile) {
			// Nothing changes under the thumb until "Show results".
			await expect(page).not.toHaveURL(/type=/);
			await page.getByRole('button', { name: 'Show results' }).click();
			await expect(page).toHaveURL(/type=stencil/);
			await expect(page.getByRole('dialog')).toBeHidden();
			await expect(page.getByRole('button', { name: 'Filters (1 active)' })).toBeFocused();
		} else {
			await expect(page).toHaveURL(/type=stencil/);
			await expect(stencil).toBeFocused();
		}
		await expect(page.getByRole('status')).toHaveText('15 artworks · page 1 of 1');
	});

	test('AC 30: the text field applies after a pause and keeps focus', async ({ page }, info) => {
		test.skip(isMobile(info), 'on a narrow screen the text applies on "Show results"');
		await page.goto('/en/archive');
		const search = page.getByRole('searchbox', { name: 'Search the archive' });
		await search.fill('prova 05');
		await expect(page).toHaveURL(/q=prova\+05/);
		await expect(search).toBeFocused();
		await expect(page.getByRole('status')).toHaveText('1 artwork · page 1 of 1');
		// "Relevance" is offered next to a search, and is the default.
		await expect(page.getByRole('combobox', { name: 'Sort by' })).toHaveValue('relevance');
	});

	// Criterion 31: every filter is a removable chip, and "Clear all filters" is offered.
	test('AC 31: active filters are removable chips with accessible names and can be cleared', async ({
		page
	}) => {
		await page.goto('/en/archive?type=stencil&q=prova&created-from=2015&attribution=unknown');
		const chips = page.getByRole('navigation', { name: 'Active filters' });
		for (const name of [
			'Remove filter: Search: prova',
			'Remove filter: Stencil',
			'Remove filter: Unknown artist',
			'Remove filter: Created from 2015'
		]) {
			await expect(chips.getByRole('link', { name })).toBeVisible();
		}

		await chips.getByRole('link', { name: 'Remove filter: Stencil' }).click();
		await expect(page).not.toHaveURL(/type=/);
		await expect(page).toHaveURL(/q=prova/);

		await page.getByRole('link', { name: 'Clear all filters' }).click();
		await expect(page).toHaveURL(/\/en\/archive$/);
		await expect(page.getByRole('link', { name: 'Clear all filters' })).toHaveCount(0);
	});

	// Criterion 33: the no-results state and the empty archive.
	test('AC 33: no results shows the text, the chips, and the exits', async ({ page }) => {
		await page.goto('/en/archive?q=zzzz&type=stencil');
		await expect(page.getByText('No artworks match these filters')).toBeVisible();
		await expect(page.getByRole('link', { name: 'Remove filter: Stencil' })).toBeVisible();
		await expect(page.getByRole('link', { name: 'Clear all filters' })).toBeVisible();

		await page.getByRole('link', { name: 'Search the whole archive' }).click();
		await expect(page).toHaveURL(/\/en\/archive\?q=zzzz$/);
	});

	test('AC 33: in an empty archive the filter bar and search are hidden', async ({
		page,
		context,
		baseURL
	}) => {
		await context.addCookies([{ name: 'tart_session', value: 'archivio-vuoto', url: baseURL! }]);
		for (const path of ['/en/archive', '/en/']) {
			await page.goto(path);
			await expect(
				page.getByText('The archive has just started: document the first artwork.')
			).toBeVisible();
			await expect(page.getByRole('search')).toHaveCount(0);
			await expect(page.getByRole('searchbox')).toHaveCount(0);
			await expect(page.getByRole('button', { name: /^Filters/ })).toHaveCount(0);
			await expect(entries(page)).toHaveCount(0);
		}
	});

	// Criterion 34: the header search field.
	test('AC 34: the header search is absent on Explore and Archive and submits to the Archive elsewhere', async ({
		page
	}, info) => {
		const mobile = isMobile(info);
		const headerSearch = page.locator('header').getByRole('searchbox');
		const openMenu = async () => {
			if (mobile) await page.getByRole('button', { name: /^Menu$/ }).click();
		};
		for (const path of ['/en/', '/en/archive', '/it/', '/it/archivio']) {
			await page.goto(path);
			await openMenu();
			await expect(headerSearch, path).toHaveCount(0);
			// The filter bar's field is the only one.
			await expect(page.getByRole('searchbox')).toHaveCount(mobile ? 0 : 1);
		}

		await page.goto('/en/about');
		await openMenu();
		await headerSearch.fill('gatto');
		await expect(headerSearch).not.toHaveAttribute('list');
		await page.locator('header').getByRole('button', { name: 'Search' }).click();
		await expect(page).toHaveURL(/\/en\/archive\?q=gatto$/);
	});

	// Criterion 35: keys are localized and remapped by the language switcher.
	test('AC 35: the query-string keys follow the UI language and the switcher remaps them', async ({
		page
	}, info) => {
		const mobile = isMobile(info);
		await page.goto('/it/archivio?tipo=stencil&condizione=intact&creata-dal=2015&pagina=1');
		await expect(page).toHaveURL(/\/it\/archivio\?condizione=intact&tipo=stencil&creata-dal=2015$/);
		if (mobile) await page.getByRole('button', { name: /^Menu$/ }).click();
		const english = page.getByRole('link', { name: 'English' });
		const href = await english.getAttribute('href');
		expect(href).toBe('/en/archive?condition=intact&type=stencil&created-from=2015');
		await english.click();
		await expect(page).toHaveURL(/\/en\/archive\?condition=intact&type=stencil&created-from=2015$/);
		// The values are the same keys, never a translated label.
		expect(page.url()).not.toMatch(/Stencil|Intact/);
	});

	// Criterion 51: canonical URLs.
	test('AC 51: unknown keys and bad values are dropped, defaults omitted, the other language accepted', async ({
		page
	}) => {
		await page.goto('/en/archive?foo=1&type=stencil&sort=recent&page=1&condition=sparito&area=abc');
		await expect(page).toHaveURL(/\/en\/archive\?type=stencil$/);
		await expect(page.getByRole('status')).toContainText('15 artworks');

		await page.goto('/en/archive?tipo=mural&tipo=stencil');
		await expect(page).toHaveURL(/\/en\/archive\?type=mural&type=stencil$/);

		await page.goto('/en/archive?sort=relevance');
		await expect(page).toHaveURL(/\/en\/archive$/);
		await page.goto('/en/archive?q=prova&sort=title');
		await expect(page).toHaveURL(/\/en\/archive\?q=prova&sort=title$/);
	});

	// Criterion 52: the Condition groups are shortcuts over single Conditions.
	test('AC 52: a group checkbox is checked, mixed, or unchecked from its Conditions and toggles them', async ({
		page
	}, info) => {
		const mobile = isMobile(info);
		await page.goto('/en/archive');
		const form = await openFilters(page, mobile);
		const group = form.getByRole('checkbox', { name: 'disappeared', exact: true });
		const covered = form.getByRole('checkbox', { name: 'Covered' });
		await expect(group).toBeChecked();
		await expect(page).not.toHaveURL(/condition=/);

		await covered.uncheck();
		await expect(group).toHaveJSProperty('indeterminate', true);
		await apply(page, mobile);
		await expect(page).toHaveURL(/condition=/);
		// The complete groups are one chip each; the rest are single Conditions.
		const chips = page.getByRole('navigation', { name: 'Active filters' });
		await expect(chips.getByRole('link', { name: 'Remove filter: present' })).toBeVisible();
		await expect(chips.getByRole('link', { name: 'Remove filter: unknown' })).toBeVisible();
		await expect(chips.getByRole('link', { name: 'Remove filter: Destroyed' })).toBeVisible();
		await expect(chips.getByRole('link', { name: 'Remove filter: Covered' })).toHaveCount(0);

		const reopened = await openFilters(page, mobile);
		const again = reopened.getByRole('checkbox', { name: 'disappeared', exact: true });
		await expect(again).toHaveJSProperty('indeterminate', true);
		await again.check();
		await expect(again).toBeChecked();
		await expect(reopened.getByRole('checkbox', { name: 'Covered' })).toBeChecked();
		if (!mobile) await expect(page).not.toHaveURL(/condition=/);
		await again.uncheck();
		for (const name of ['Covered', 'Removed', 'Destroyed', 'Missing']) {
			await expect(reopened.getByRole('checkbox', { name })).not.toBeChecked();
		}
		await apply(page, mobile);
		await expect(chips.getByRole('link', { name: 'Remove filter: disappeared' })).toHaveCount(0);

		// No key means all nine: selecting all nine removes the key.
		const final = await openFilters(page, mobile);
		await final.getByRole('checkbox', { name: 'disappeared', exact: true }).check();
		await apply(page, mobile);
		await expect(page).not.toHaveURL(/condition=/);
	});

	// Criterion 59: the thumbnail rules.
	test('AC 59: the thumbnail is the latest image, else a neutral box that names the item', async ({
		page
	}) => {
		await page.goto('/en/archive');
		const entry = (title: string) => entries(page).filter({ hasText: title });

		await expect(entry('Opera di prova 05').getByRole('img')).toHaveAttribute(
			'alt',
			'Una fotografia fittizia di un muro dipinto.'
		);
		await expect(entry('Opera di prova 02')).toContainText('Text document');
		await expect(entry('Opera di prova 01')).toContainText('Link');

		// No public Documentation item: the Condition sign, the words, and no date.
		const none = entry('Opera di prova 03');
		await expect(none).toContainText('No documentation available');
		await expect(none).toContainText('Destroyed');
		await expect(none).not.toContainText('last documented');
		await expect(entry('Opera di prova 02')).toContainText('last documented');
	});

	test('the entry shows the title link, Condition, attribution, and where line', async ({
		page
	}) => {
		await page.goto('/en/archive');
		const first = entries(page).first();
		await expect(first.getByRole('link', { name: 'Opera di prova 01' })).toHaveAttribute(
			'href',
			'/en/artworks/100-opera-di-prova-1'
		);
		await expect(first).toContainText('Nebbia Finta');
		await expect(first).toContainText('Deposito fittizio');
		await expect(first).toContainText('approximate location');
		await expect(entries(page).nth(1)).toContainText('Disputed attribution');
		await expect(entries(page).nth(2)).toContainText('Unknown artist');
		await page.goto('/en/archive?page=2');
		await expect(entries(page).last()).toContainText('Untitled');
	});

	test('"Created between" says how many Artworks are left out; "Also matching" links to the index', async ({
		page
	}) => {
		await page.goto('/en/archive?created-from=2015');
		await expect(
			page.getByText('10 artworks without a creation date are not included')
		).toBeVisible();

		await page.goto('/en/archive?q=nebbia');
		const also = page.getByRole('region', { name: 'Also matching' });
		await expect(also.getByRole('link', { name: 'Nebbia Finta' })).toBeVisible();
		await expect(also).toContainText('(also: Nebbia)');
		await expect(also.getByRole('link', { name: 'Show all (4)' })).toHaveAttribute(
			'href',
			'/en/artists?name=nebbia'
		);
	});

	for (const language of ['it', 'en'] as const) {
		const path = {
			it: ['/it/archivio?tipo=stencil', '/it/'],
			en: ['/en/archive?type=stencil', '/en/']
		}[language];
		test(`the Archive and Explore lists pass axe in ${language}`, async ({ page }, info) => {
			for (const url of path) {
				await page.goto(url);
				await axe(page, url);
			}
			if (isMobile(info)) {
				await page.getByRole('button', { name: /^(Filters|Filtri)/ }).click();
				await axe(page, `${path[0]} with the filter dialog`);
			}
			await page.goto(language === 'it' ? '/it/archivio?q=zzzz' : '/en/archive?q=zzzz');
			await axe(page, 'no results');
		});
	}
});

test.describe('without JavaScript', () => {
	test.use({ javaScriptEnabled: false });

	// Criterion 30 and 38: the form is a plain GET form, and Explore renders the list.
	test('AC 38: Explore renders the list and every filter works through the form', async ({
		page
	}) => {
		await page.goto('/en/');
		await expect(entries(page)).toHaveCount(24);

		await page.getByRole('checkbox', { name: 'Stencil' }).check();
		await page.getByRole('searchbox', { name: 'Search the archive' }).fill('prova');
		await page.getByLabel('From year').first().fill('2010');
		await page.getByRole('button', { name: 'Show results' }).click();

		await expect(page).toHaveURL(/\/en\/\?q=prova&sort=recent&type=stencil&documented-from=2010$/);
		await expect(page.getByRole('status')).toContainText('artworks');
		await expect(page.getByRole('link', { name: 'Remove filter: Stencil' })).toBeVisible();
	});

	test('AC 30: the form works without JavaScript on the Archive view, with plain links for pages', async ({
		page
	}) => {
		await page.goto('/en/archive');
		await page.getByRole('combobox', { name: 'Sort by' }).selectOption('title');
		await page.getByRole('checkbox', { name: 'Mural' }).check();
		await page.getByRole('button', { name: 'Show results' }).click();
		await expect(page).toHaveURL(/\/en\/archive\?sort=title&type=mural$/);
		await expect(entries(page).first()).toContainText('Opera di prova 02');

		await page.goto('/en/archive');
		await page.getByRole('link', { name: 'Next page' }).click();
		await expect(page).toHaveURL(/page=2/);
		await expect(entries(page)).toHaveCount(6);
		// The group shortcut is a script-only convenience; the Conditions work alone.
		await expect(page.getByRole('checkbox', { name: 'disappeared', exact: true })).toHaveCount(0);
	});
});
