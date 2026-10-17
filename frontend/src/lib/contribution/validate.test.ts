import { describe, expect, it } from 'vitest';
import { emptyDate, fromUncertainDate } from './date-field';
import { emptyForm, nextKey, STEPS, type ArtworkForm } from './form';
import {
	firstIncomplete,
	isBlank,
	serverError,
	stepStates,
	validate,
	type Context,
	type FieldError
} from './validate';

const context: Context = {
	today: '2026-10-16',
	licences: ['CC-BY-SA-4.0', 'CC-BY-4.0'],
	expressionTypes: new Set(['mural']), // `stencil` is retired in the fictional Instance
	surfaceTypes: new Set(['wall']),
	acceptanceRequired: false,
	termsAccepted: false,
	uploads: {},
	duplicatesShown: false
};

/** A fictional new Artwork that satisfies every rule. */
function valid(): ArtworkForm {
	const form = emptyForm();
	form.location.geometry = { type: 'Point', coordinates: [12.49, 41.9] };
	form.location.surfaceType = 'wall';
	form.documentation.push({
		key: nextKey(form, 'doc'),
		medium: 'link',
		file: null,
		fileName: '',
		observed: fromUncertainDate({ precision: 'year', qualifier: 'exact', first: '2020-01-01' }),
		suggested: false,
		rightsBasis: '',
		creatorCredit: '',
		licence: '',
		originUrl: '',
		altText: '',
		url: 'https://example.org/pagina'
	});
	form.initialCondition = 'intact';
	form.title = 'Il gatto di prova';
	form.expressionTypes = ['mural'];
	form.attributed = false;
	return form;
}

const codes = (errors: FieldError[]) => errors.map((each) => each.code);
const image = (form: ArtworkForm) => {
	form.documentation.push({
		key: nextKey(form, 'doc'),
		medium: 'image',
		file: 'a-file',
		fileName: 'foto.jpg',
		observed: fromUncertainDate({ precision: 'day', qualifier: 'exact', first: '2024-05-17' }),
		suggested: false,
		rightsBasis: 'own_work',
		creatorCredit: 'Fotografa di prova',
		licence: 'CC-BY-4.0',
		originUrl: '',
		altText: 'Un muro dipinto.',
		url: ''
	});
	return form.documentation.at(-1)!;
};

describe('validating a new Artwork on submit', () => {
	it('passes a complete one, and a single link is enough documentation (criterion 14)', () => {
		expect(validate(valid(), context)).toEqual([]);
	});

	it('lists every error of an empty form at once, in the order of the steps', () => {
		const errors = validate(emptyForm(), context);
		expect(codes(errors)).toEqual([
			'location.required',
			'documentation.required',
			'condition.required',
			'artwork.title_required',
			'artwork.expression_types_required',
			'attribution.choice_required'
		]);
		const order = errors.map((each) => STEPS.indexOf(each.step));
		expect(order).toEqual([...order].sort((a, b) => a - b));
	});

	it('refuses a new Artwork without an initial Condition, which is never implied (14)', () => {
		const form = valid();
		form.initialCondition = '';
		expect(codes(validate(form, context))).toEqual(['condition.required']);
	});

	it('wants a title or an explicit Untitled', () => {
		const form = valid();
		form.title = '  ';
		expect(codes(validate(form, context))).toEqual(['artwork.title_required']);
		form.untitled = true;
		expect(validate(form, context)).toEqual([]);
	});

	it('does not offer or accept a retired Expression type (21)', () => {
		const form = valid();
		form.expressionTypes = ['stencil'];
		expect(codes(validate(form, context))).toEqual(['artwork.expression_type_unknown']);
	});

	it('refuses a confirmed Attribution without a citation, and reads one with it (16)', () => {
		const form = valid();
		form.attributed = true;
		form.attributions.push({
			key: nextKey(form, 'attribution'),
			artist: { kind: 'existing', id: 7, name: 'Nebbia Finta' },
			certainty: 'confirmed',
			alias: '',
			note: '',
			citations: []
		});
		expect(codes(validate(form, context))).toEqual(['attribution.confirmed_requires_citation']);
		form.attributions[0].citations = [form.documentation[0].key];
		expect(validate(form, context)).toEqual([]);
		form.attributions[0].certainty = 'probable';
		form.attributions[0].citations = [];
		expect(validate(form, context)).toEqual([]);
	});

	it('wants unknown authorship said, and an Attribution when it is known', () => {
		const form = valid();
		form.attributed = true;
		expect(codes(validate(form, context))).toEqual(['attribution.required']);
	});

	it('refuses the same Artist twice, and a new Artist without a name', () => {
		const form = valid();
		form.attributed = true;
		for (const name of ['Nebbia Finta', 'Nebbia Finta']) {
			form.attributions.push({
				key: nextKey(form, 'attribution'),
				artist: { kind: 'existing', id: 7, name },
				certainty: 'probable',
				alias: '',
				note: '',
				citations: []
			});
		}
		form.attributions.push({
			key: nextKey(form, 'attribution'),
			artist: { kind: 'new', key: 'artist-x', name: ' ', artistKind: 'individual' },
			certainty: 'probable',
			alias: '',
			note: '',
			citations: []
		});
		expect(codes(validate(form, context))).toEqual([
			'attribution.artist_duplicated',
			'attribution.artist_name_required'
		]);
	});
});

describe('the rights of an uploaded file (criterion 17)', () => {
	it('wants an Observed date, a Rights basis, a Creator credit, and an allowlisted licence', () => {
		const form = valid();
		const item = image(form);
		item.observed = emptyDate();
		item.rightsBasis = '';
		item.creatorCredit = '';
		item.licence = 'GPL-3.0';
		expect(codes(validate(form, context))).toEqual([
			'documentation.observed_required',
			'documentation.rights_required',
			'documentation.credit_required',
			'documentation.licence_not_allowed'
		]);
	});

	it('wants the origin address of third-party work', () => {
		const form = valid();
		const item = image(form);
		item.rightsBasis = 'third_party';
		expect(codes(validate(form, context))).toEqual(['documentation.origin_required']);
		item.originUrl = 'not an address';
		expect(codes(validate(form, context))).toEqual(['documentation.origin_invalid']);
		item.originUrl = 'https://example.org/origine';
		expect(validate(form, context)).toEqual([]);
	});

	it('wants alt text of at most 250 characters for an image', () => {
		const form = valid();
		const item = image(form);
		item.altText = ' ';
		expect(codes(validate(form, context))).toEqual(['documentation.alt_required']);
		item.altText = 'x'.repeat(251);
		expect(validate(form, context)[0]).toMatchObject({
			code: 'documentation.alt_too_long',
			params: { max: 250 }
		});
	});

	it('holds back a file still uploading or refused, and counts the files', () => {
		const form = valid();
		const item = image(form);
		expect(codes(validate(form, { ...context, uploads: { [item.key]: 'processing' } }))).toEqual([
			'documentation.file_processing'
		]);
		expect(codes(validate(form, { ...context, uploads: { [item.key]: 'rejected' } }))).toEqual([
			'documentation.file_rejected'
		]);
		for (let count = 0; count < 20; count++) image(form);
		expect(codes(validate(form, context))).toEqual(['documentation.too_many_files']);
	});

	it('refuses a link without a valid address, and a date in the future', () => {
		const form = valid();
		form.documentation[0].url = 'ftp://example.org';
		form.documentation[0].observed = fromUncertainDate({
			precision: 'year',
			qualifier: 'exact',
			first: '2030-01-01'
		});
		expect(codes(validate(form, context))).toEqual(['date.in_future', 'documentation.url_invalid']);
	});
});

describe('the Location (criterion 19)', () => {
	it('refuses a radius on anything but an approximate point', () => {
		const form = valid();
		form.location.radius = 30;
		expect(codes(validate(form, context))).toEqual(['location.radius_requires_approximate_point']);
		form.location.approximate = true;
		expect(validate(form, context)).toEqual([]);
		form.location.geometry = {
			type: 'LineString',
			coordinates: [
				[12.49, 41.9],
				[12.5, 41.91]
			]
		};
		expect(codes(validate(form, context))).toEqual(['location.radius_requires_approximate_point']);
	});

	it('wants a Surface type for a new Location, not for an existing one', () => {
		const form = valid();
		form.location.surfaceType = '';
		expect(codes(validate(form, context))).toEqual(['location.surface_type_required']);
		form.location.geometry = null;
		form.location.existing = { id: 200, title: 'Parete di prova' };
		expect(validate(form, context)).toEqual([]);
	});

	it('wants the duplicate warning confirmed for the placement it was shown for', () => {
		const form = valid();
		const shown = { ...context, duplicatesShown: true };
		expect(codes(validate(form, shown))).toEqual(['location.different_surface_unconfirmed']);
		form.location.geometry = null;
		form.location.existing = { id: 200, title: 'Parete di prova' };
		expect(codes(validate(form, shown))).toEqual(['location.different_artwork_unconfirmed']);
		form.location.confirmedKey = 'location:200';
		expect(validate(form, shown)).toEqual([]);
	});
});

describe('the terms', () => {
	it('are asked only when the Review step carries the acceptance', () => {
		const form = valid();
		expect(validate(form, context)).toEqual([]);
		const asked = { ...context, acceptanceRequired: true };
		expect(codes(validate(form, asked))).toEqual(['terms.required']);
		expect(validate(form, { ...asked, termsAccepted: true })).toEqual([]);
	});
});

describe('step states', () => {
	it('say complete, to complete, or to fix, in words, and never block a step (12)', () => {
		const errors = validate(emptyForm(), context);
		const before = stepStates(errors, false);
		expect(before.location).toBe('to_complete');
		expect(before.creation).toBe('complete');
		expect(before.sources).toBe('complete');
		// Review waits for the steps before it.
		expect(before.review).toBe('to_complete');
		const after = stepStates(errors, true);
		expect(after.location).toBe('to_fix');
		expect(after.creation).toBe('complete');
		expect(Object.values(stepStates([], true))).toEqual(STEPS.map(() => 'complete'));
	});

	it('open a resumed draft on its first step that is not complete', () => {
		expect(firstIncomplete(validate(emptyForm(), context))).toBe('location');
		const form = valid();
		form.location.geometry = null;
		form.location.existing = { id: 1, title: 'x' };
		form.initialCondition = '';
		expect(firstIncomplete(validate(form, context))).toBe('documentation');
		expect(firstIncomplete([])).toBe('review');
	});

	it('know a draft just started', () => {
		expect(isBlank(emptyForm())).toBe(true);
		const form = emptyForm();
		form.title = 'x';
		expect(isBlank(form)).toBe(false);
	});
});

describe('a refusal by the server', () => {
	it('is placed at the step of its record, and otherwise at the Review step', () => {
		expect(serverError('location.outside_boundary').step).toBe('location');
		expect(serverError('geometry.self_intersecting').step).toBe('location');
		expect(serverError('moderation.initial_condition_required')).toMatchObject({
			step: 'documentation',
			id: 'editor-condition'
		});
		expect(serverError('documentation_item.alt_text_too_long').step).toBe('documentation');
		expect(serverError('moderation.something_new').step).toBe('review');
	});
});
