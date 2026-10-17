import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { fromUncertainDate } from './date-field';
import {
	emptyForm,
	fromWorkingCopy,
	nextKey,
	placementKey,
	toWorkingCopy,
	type ArtworkForm
} from './form';

const TODAY = '2026-10-16';

/** A fictional draft that uses every part of the form. */
function filled(): ArtworkForm {
	const form = emptyForm();
	form.location = {
		existing: null,
		geometry: { type: 'Point', coordinates: [12.49, 41.9] },
		approximate: true,
		radius: 30,
		surfaceType: 'building_wall',
		placeDescription: 'Muro di prova',
		confirmedKey: null
	};
	form.documentation.push({
		key: nextKey(form, 'doc'),
		medium: 'image',
		file: '6f1c1e0e-6a4b-4c0c-9a58-0d6a8c3e8b11',
		fileName: 'foto-fittizia.jpg',
		observed: fromUncertainDate({ precision: 'day', qualifier: 'exact', first: '2024-05-17' }),
		suggested: true,
		rightsBasis: 'third_party',
		creatorCredit: 'Fotografa di prova',
		licence: 'CC-BY-4.0',
		originUrl: 'https://example.org/origine',
		altText: 'Un muro dipinto, fittizio.',
		url: ''
	});
	form.documentation.push({
		key: nextKey(form, 'doc'),
		medium: 'link',
		file: null,
		fileName: '',
		observed: fromUncertainDate({ precision: 'year', qualifier: 'circa', first: '2021-01-01' }),
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
	form.series = [{ id: null, key: nextKey(form, 'series'), name: 'Serie di prova' }];
	form.attributed = true;
	form.sources.push({
		key: nextKey(form, 'source'),
		title: 'Libro fittizio',
		author: '',
		publication: '',
		url: '',
		note: ''
	});
	form.attributions.push({
		key: nextKey(form, 'attribution'),
		artist: {
			kind: 'new',
			key: nextKey(form, 'artist'),
			name: 'Nome Finto',
			artistKind: 'collective'
		},
		certainty: 'probable',
		alias: '',
		note: '',
		citations: [form.sources[0].key]
	});
	form.attributions.push({
		key: nextKey(form, 'attribution'),
		artist: { kind: 'existing', id: 7, name: 'Nebbia Finta' },
		certainty: 'disputed',
		alias: '',
		note: 'Forse.',
		citations: []
	});
	form.created.date = fromUncertainDate({
		precision: 'year',
		qualifier: 'circa',
		first: '2019-01-01'
	});
	return form;
}

const CONTRACT = new URL(
	'../../../e2e/fixtures/contribution/editor-new-artwork.json',
	import.meta.url
);

describe('the working copy of a new Artwork', () => {
	it('is what the API is tested with: the backend submits and approves this very copy', () => {
		// Every record it points to is created in the copy itself: the API's archive is empty.
		const form = filled();
		form.attributions = form.attributions.filter((each) => each.artist?.kind === 'new');
		const written = JSON.parse(JSON.stringify(toWorkingCopy(form, TODAY)));
		if (process.env.TART_WRITE_FIXTURES) {
			mkdirSync(new URL('./', CONTRACT), { recursive: true });
			writeFileSync(CONTRACT, JSON.stringify(written));
		}
		expect(JSON.parse(readFileSync(CONTRACT, 'utf8'))).toEqual(written);
	});

	it('is the archive changeset, with the new records referred to by key', () => {
		const copy = toWorkingCopy(filled(), TODAY) as {
			operations: { op: string; ref: string; kind: string; record: Record<string, unknown> }[];
			initial_condition: string;
		};
		expect(copy.initial_condition).toBe('intact');
		expect(copy.operations.map((each) => `${each.kind}:${each.ref}`)).toEqual([
			'location:location',
			'artist:artist-6',
			'series:series-3',
			'source:source-4',
			'documentation_item:doc-1',
			'documentation_item:doc-2',
			'artwork:artwork'
		]);
		const [location, , , , image, link, artwork] = copy.operations.map((each) => each.record);
		expect(location).toMatchObject({
			geometry: { type: 'Point', coordinates: [12.49, 41.9] },
			surface_type: 'building_wall',
			approximate: true,
			uncertainty_radius: 30
		});
		expect(image).toMatchObject({
			medium: 'image',
			file: '6f1c1e0e-6a4b-4c0c-9a58-0d6a8c3e8b11',
			rights_basis: 'third_party',
			origin_url: 'https://example.org/origine',
			alt_text: 'Un muro dipinto, fittizio.',
			artworks: [{ new: 'artwork' }]
		});
		// A link carries no file fields at all.
		expect(link).not.toHaveProperty('licence');
		expect(link).toMatchObject({ medium: 'link', url: 'https://example.org/pagina' });
		expect(artwork).toMatchObject({
			location: { new: 'location' },
			expression_types: ['mural'],
			title: 'Il gatto di prova',
			series: [{ new: 'series-3' }],
			sources: [{ new: 'source-4' }]
		});
		const attributions = (artwork as { attributions: unknown[] }).attributions;
		expect(attributions).toEqual([
			{
				artist: { new: 'artist-6' },
				certainty: 'probable',
				alias: null,
				note: null,
				citations: [{ new: 'source-4' }]
			},
			{ artist: 7, certainty: 'disputed', alias: null, note: 'Forse.', citations: [] }
		]);
		expect((artwork as { history_events: unknown[] }).history_events).toEqual([
			{
				id: { new: 'created' },
				type: 'created',
				observed_date: { precision: 'year', qualifier: 'circa', first: '2019-01-01', second: null },
				citations: []
			}
		]);
	});

	it('puts the Artwork on an existing Location by its id, and creates none', () => {
		const form = emptyForm();
		form.location.existing = { id: 200, title: 'Parete di prova' };
		const copy = toWorkingCopy(form, TODAY) as { operations: { kind: string; record: unknown }[] };
		expect(copy.operations.map((each) => each.kind)).toEqual(['artwork']);
		expect(copy.operations[0].record).toMatchObject({ location: 200 });
	});

	it('says unknown authorship with no Attribution, whatever was entered before', () => {
		const form = filled();
		form.attributed = false;
		const copy = toWorkingCopy(form, TODAY) as { operations: { kind: string; record: unknown }[] };
		const artwork = copy.operations.at(-1)?.record as { attributions: unknown[] };
		expect(artwork.attributions).toEqual([]);
		expect(copy.operations.some((each) => each.kind === 'artist')).toBe(false);
	});

	it('is stored by an empty draft as nothing but the Artwork', () => {
		const copy = toWorkingCopy(emptyForm(), TODAY) as {
			operations: { kind: string; record: Record<string, unknown> }[];
			initial_condition: null;
		};
		expect(copy.operations).toHaveLength(1);
		expect(copy.operations[0].record).toMatchObject({
			location: null,
			title: null,
			expression_types: []
		});
		expect(copy.initial_condition).toBeNull();
	});

	it('comes back as the form it was made from', () => {
		const form = filled();
		const back = fromWorkingCopy(JSON.parse(JSON.stringify(toWorkingCopy(form, TODAY))));
		expect(back.location).toEqual(form.location);
		expect(back.documentation).toEqual(form.documentation);
		expect(back.initialCondition).toBe('intact');
		expect(back.title).toBe('Il gatto di prova');
		expect(back.series).toEqual(form.series);
		expect(back.sources).toEqual(form.sources);
		expect(back.attributed).toBe(true);
		expect(
			back.attributions.map(({ artist, certainty, note, citations }) => ({
				artist,
				certainty,
				note,
				citations
			}))
		).toEqual(
			form.attributions.map(({ artist, certainty, note, citations }) => ({
				artist,
				certainty,
				note,
				citations
			}))
		);
		expect(back.created.date).toEqual(form.created.date);
		// New keys never collide with those already in the draft.
		const used = new Set([
			...back.documentation.map((each) => each.key),
			...back.sources.map((each) => each.key),
			...back.series.map((each) => each.key)
		]);
		expect(used.has(nextKey(back, 'doc'))).toBe(false);
	});

	it('keeps the explicit Untitled, which the changeset cannot say', () => {
		const form = emptyForm();
		form.untitled = true;
		form.expressionTypes = ['mural'];
		const back = fromWorkingCopy(JSON.parse(JSON.stringify(toWorkingCopy(form, TODAY))));
		expect(back.untitled).toBe(true);
		expect(back.title).toBe('');
	});

	it('reads a submitted round, which has no editor part, as complete choices', () => {
		const copy = JSON.parse(JSON.stringify(toWorkingCopy(filled(), TODAY)));
		delete copy.editor;
		const back = fromWorkingCopy(copy);
		expect(back.untitled).toBe(false);
		expect(back.attributed).toBe(true);
		expect(back.location.confirmedKey).toBe(placementKey(back.location));
		const untitled = JSON.parse(JSON.stringify(toWorkingCopy(emptyForm(), TODAY)));
		delete untitled.editor;
		expect(fromWorkingCopy(untitled).untitled).toBe(true);
	});

	it('gives the empty form for anything it did not write', () => {
		for (const copy of [null, undefined, 'x', [], {}, { operations: 'x' }]) {
			expect(fromWorkingCopy(copy)).toEqual(emptyForm());
		}
	});
});

describe('the placement the duplicate warning is about', () => {
	it('names a Location, or a place drawn with its radius', () => {
		const form = emptyForm();
		expect(placementKey(form.location)).toBeNull();
		form.location.existing = { id: 5, title: 'x' };
		expect(placementKey(form.location)).toBe('location:5');
		form.location.existing = null;
		form.location.geometry = { type: 'Point', coordinates: [12.5, 41.9] };
		const before = placementKey(form.location);
		form.location.radius = 20;
		expect(placementKey(form.location)).not.toBe(before);
	});
});
