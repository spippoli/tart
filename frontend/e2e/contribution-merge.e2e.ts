import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';
import { createHash } from 'node:crypto';
import { serveStyles } from './map-style';

/**
 * The Merge, Duplicate retirement, and Unmerge editors (Contribution and moderation spec,
 * Merge, Duplicate retirement, Unmerge; criteria 38, 40, 41, and 51). The stand-in API keeps
 * a draft of each kind (e2e/mock-api.ts); the real API's own tests cover what approval
 * writes. Every record here is fictional.
 */

const WCAG_22_AA = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];

const WORDS = {
	en: {
		chooser: '/en/contribute/merge?source=2000',
		retirementChooser: '/en/contribute/merge?source=2100',
		unmerge: '/en/contributions/703/edit',
		use: /Merge into this record/,
		numberLabel: 'Record number',
		next: 'Continue',
		steps: 'Steps of the form',
		reconcile: 'Reconcile',
		references: 'References to rewrite',
		review: 'Review and submit',
		separated: 'What is separated',
		submit: 'Submit for review',
		keepAlias: 'Alias to add, editable',
		submitted: 'Submitted: waiting for a decision',
		mergeTitle: 'Propose a Merge',
		retirementTitle: 'Propose a Duplicate retirement',
		unmergeTitle: 'Propose an Unmerge'
	},
	it: {
		chooser: '/it/contribuisci/unisci?source=2000',
		retirementChooser: '/it/contribuisci/unisci?source=2100',
		unmerge: '/it/contributi/703/modifica',
		use: /Fondi in questa scheda/,
		numberLabel: 'Numero della scheda',
		next: 'Continua',
		steps: 'Passaggi del modulo',
		reconcile: 'Riconciliazione',
		references: 'Riferimenti da riscrivere',
		review: 'Riepilogo e invio',
		separated: 'Cosa si separa',
		submit: 'Invia alla revisione',
		keepAlias: 'Pseudonimo da aggiungere, modificabile',
		submitted: 'Inviato: in attesa di una decisione',
		mergeTitle: "Proponi un'unione",
		retirementTitle: 'Proponi il ritiro di un duplicato',
		unmergeTitle: "Proponi l'annullamento di un'unione"
	}
} as const;

function address(info: { project: { name: string }; title: string }) {
	const slug = createHash('sha1').update(info.title).digest('hex').slice(0, 12);
	return `persona-fusione-${info.project.name}-${slug}-accettati@example.org`;
}

const MOCK = 'http://localhost:8795';
const BASE = 'http://localhost:4273';

/** A fictional signed-in User; the browser's calls to the API go to the stand-in API. */
async function signIn(page: Page, email: string) {
	await serveStyles(page);
	await page
		.context()
		.addCookies([{ name: 'tart_session', value: encodeURIComponent(email), url: BASE }]);
	await page.route(/\/api\/contributions(\/|\?|$)/, async (route) => {
		const url = new URL(route.request().url());
		try {
			const response = await route.fetch({
				url: MOCK + url.pathname + url.search,
				headers: { ...route.request().headers(), 'x-tart-client-ip': '127.0.0.1' }
			});
			await route.fulfill({ response });
		} catch {
			// The page navigated away while the request was in flight.
		}
	});
}

async function expectNoViolations(page: Page) {
	const results = await new AxeBuilder({ page }).withTags(WCAG_22_AA).analyze();
	expect(results.violations).toEqual([]);
}

for (const language of ['it', 'en'] as const) {
	const words = WORDS[language];

	test.describe(`Merge editors, ${language}`, () => {
		test.beforeEach(async ({ page }, info) => {
			await signIn(page, address(info));
		});

		test('the chooser lists the likeliest records and starts the draft in the editor', async ({
			page
		}) => {
			await page.goto(words.chooser);
			await expect(page.getByRole('heading', { level: 1, name: words.mergeTitle })).toBeVisible();
			await expectNoViolations(page);

			await page.getByRole('button', { name: words.use }).click();

			await expect(page).toHaveURL(/\/(contributions|contributi)\/\d+\/(edit|modifica)$/);
			await expect(page.getByRole('heading', { level: 1, name: words.mergeTitle })).toBeVisible();
		});

		test('a Merge is reconciled, reviewed, and submitted; every step passes axe', async ({
			page
		}) => {
			await page.goto(words.chooser);
			await page.getByRole('button', { name: words.use }).click();
			await expect(page.getByRole('navigation', { name: words.steps })).toBeVisible();
			await expectNoViolations(page);

			const steps = page.getByRole('navigation', { name: words.steps });
			await steps.getByRole('button', { name: new RegExp(words.reconcile) }).click();
			// The Alias of the folded record is pre-filled and editable.
			const alias = page.getByRole('textbox', { name: words.keepAlias });
			await expect(alias).toHaveValue('Artista Doppio');
			await alias.fill('Doppio');
			await expectNoViolations(page);

			await steps.getByRole('button', { name: new RegExp(words.references) }).click();
			await expect(page.getByRole('link', { name: /gatto/i })).toBeVisible();
			await expectNoViolations(page);

			await steps.getByRole('button', { name: new RegExp(words.review) }).click();
			await expectNoViolations(page);
			await page.getByRole('button', { name: words.submit }).click();

			await expect(page).toHaveURL(/\/(contributions|contributi)\/\d+$/);
			await expect(page.getByText(words.submitted)).toBeVisible();
			await expectNoViolations(page);
		});

		test('a refusal at submit is worded beside the action and takes focus', async ({ page }) => {
			await page.goto(words.chooser);
			await page.getByRole('button', { name: words.use }).click();
			await page
				.getByRole('navigation', { name: words.steps })
				.getByRole('button', { name: new RegExp(words.review) })
				.click();
			await page.getByRole('textbox').last().fill('rifiuta');
			await page.getByRole('button', { name: words.submit }).click();

			const alert = page.getByRole('alert');
			await expect(alert).toBeFocused();
			await expect(alert).toContainText(/Creation|creazione/);
			await expectNoViolations(page);
		});

		test('a Duplicate retirement has two steps and passes axe', async ({ page }) => {
			await page.goto(words.retirementChooser);
			await expectNoViolations(page);
			await page.getByRole('spinbutton', { name: words.numberLabel }).fill('2101');
			await page.getByRole('button', { name: words.next }).click();

			await expect(
				page.getByRole('heading', { level: 1, name: words.retirementTitle })
			).toBeVisible();
			await expect(
				page.getByRole('navigation', { name: words.steps }).getByRole('listitem')
			).toHaveCount(2);
			await expectNoViolations(page);
		});

		test('an Unmerge preselects what the Merge added and passes axe', async ({ page }) => {
			await page.goto(words.unmerge);

			await expect(page.getByRole('heading', { level: 1, name: words.unmergeTitle })).toBeVisible();
			await expect(page.getByRole('checkbox').first()).toBeChecked();
			await expectNoViolations(page);
		});
	});
}
