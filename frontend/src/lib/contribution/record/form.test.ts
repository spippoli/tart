import { describe, expect, it } from 'vitest';
import { emptyDate } from '../date-field';
import {
	artworkEditorOf,
	emptyForm,
	fromWorkingCopy as artworkFrom,
	toWorkingCopy as artworkCopy
} from '../form';
import {
	emptyRecordForm,
	fromWorkingCopy,
	initialValue,
	toWorkingCopy,
	type RecordForm
} from './form';
import { SPECS } from './spec';
import { validateRecord, type RecordContext } from './validate';

const TODAY = '2026-10-17';
const context = (over: Partial<RecordContext> = {}): RecordContext => ({
	kind: 'location',
	current: { geometry: { type: 'Point', coordinates: [12.48, 41.89] }, approximate: false },
	creating: false,
	today: TODAY,
	surfaceTypes: new Set(['wall']),
	expressionTypes: new Set(['stencil']),
	acceptanceRequired: false,
	termsAccepted: false,
	...over
});
const operations = (copy: Record<string, unknown>) => copy.operations as Record<string, unknown>[];

describe('the working copy of an edit', () => {
	it('sets only the fields that are edited (46, 48)', () => {
		const form = emptyRecordForm();
		form.fields.geometry = { type: 'Point', coordinates: [12.49, 41.9] };
		const copy = toWorkingCopy({ kind: 'location', id: 7 }, form, TODAY);
		expect(operations(copy)).toEqual([
			{
				op: 'set',
				target: 7,
				field: 'geometry',
				value: { type: 'Point', coordinates: [12.49, 41.9] }
			}
		]);
	});

	it('creates a Site from the Location field, with the Location as its only member (46)', () => {
		const form = emptyRecordForm();
		form.sites.push({ key: 'site-1', name: 'Legal wall', description: '', sources: [] });
		form.fields.site = { kind: 'new', key: 'site-1' };
		const ops = operations(toWorkingCopy({ kind: 'location', id: 7 }, form, TODAY));
		expect(ops[0]).toMatchObject({ op: 'create', ref: 'site-1', kind: 'site' });
		expect(ops[1]).toEqual({ op: 'set', target: 7, field: 'site', value: { new: 'site-1' } });
		// A Site's edit has no field or collection for its members.
		expect(SPECS.site.fields.map((each) => each.name)).toEqual(['name', 'description']);
		expect(SPECS.site.collections.map((each) => each.name)).toEqual(['sources']);
		expect(SPECS.series.collections.map((each) => each.name)).toEqual(['sources']);
	});

	it('creates a Series from the Artwork field and adds it as an item (46)', () => {
		const form = emptyRecordForm();
		form.series.push({ key: 'series-1', name: 'Cats', description: '', sources: [] });
		form.links.series = { added: [{ id: null, key: 'series-1', name: 'Cats' }], removed: [3] };
		const ops = operations(toWorkingCopy({ kind: 'artwork', id: 9 }, form, TODAY));
		expect(ops.map((each) => each.op)).toEqual(['create', 'remove', 'add']);
		expect(ops[2]).toMatchObject({ collection: 'series', item: { new: 'series-1' } });
	});

	it('removes an Alias and adds a Crew membership as items (50)', () => {
		const form = emptyRecordForm();
		form.aliases.removed.push('Mano');
		form.crew.added.push({
			key: 'crew-1',
			collective: { id: 4, name: 'Crew' },
			period: { start: emptyDate(), end: emptyDate() }
		});
		const ops = operations(
			toWorkingCopy({ kind: 'artist', id: 2 }, form, TODAY, { crew_memberships: [] })
		);
		expect(ops).toEqual([
			{ op: 'remove', target: 2, collection: 'aliases', key: 'Mano' },
			{
				op: 'add',
				target: 2,
				collection: 'crew_memberships',
				item: { collective: 4, period: null }
			}
		]);
	});

	it('keeps the form beside the operations and resumes from it', () => {
		const form = emptyRecordForm();
		form.fields.name = 'Nuovo nome';
		const copy = toWorkingCopy({ kind: 'site', id: 1 }, form, TODAY);
		expect(fromWorkingCopy(copy).fields).toEqual({ name: 'Nuovo nome' });
		expect(fromWorkingCopy(null)).toEqual(emptyRecordForm());
	});
});

describe('the working copy of a new Area (47)', () => {
	it('is one create with its polygon', () => {
		const form = emptyRecordForm();
		for (const field of SPECS.area.fields) form.fields[field.name] = initialValue(field);
		form.fields.name = 'Rione fittizio';
		form.fields.geometry = {
			type: 'Polygon',
			coordinates: [
				[
					[12.47, 41.88],
					[12.49, 41.88],
					[12.49, 41.9],
					[12.47, 41.88]
				]
			]
		};
		const [create] = operations(toWorkingCopy({ kind: 'area', id: null }, form, TODAY));
		expect(create).toMatchObject({ op: 'create', kind: 'area' });
	});

	it('asks for a name and a polygon', () => {
		const form: RecordForm = emptyRecordForm();
		for (const field of SPECS.area.fields) form.fields[field.name] = initialValue(field);
		const codes = validateRecord(form, context({ kind: 'area', creating: true, current: {} })).map(
			(each) => each.code
		);
		expect(codes).toEqual(['field.required', 'geometry.required']);
	});
});

describe('the validation of an edit', () => {
	it('refuses an edit that changes nothing', () => {
		const errors = validateRecord(emptyRecordForm(), context());
		expect(errors.map((each) => each.code)).toEqual(['edit.empty']);
	});

	it('refuses a radius on a position that is not an approximate point', () => {
		const form = emptyRecordForm();
		form.fields.uncertainty_radius = '30';
		expect(validateRecord(form, context()).map((each) => each.code)).toEqual([
			'location.radius_requires_approximate_point'
		]);
		form.fields.approximate = true;
		expect(validateRecord(form, context())).toEqual([]);
	});

	it('wants a certainty on an Attribution and a citation on a confirmed one', () => {
		const form = emptyRecordForm();
		form.attributions.added.push({
			key: 'a-1',
			artist: { kind: 'existing', id: 5, key: null, name: 'Mano' },
			certainty: 'confirmed',
			alias: '',
			note: '',
			citations: []
		});
		const codes = validateRecord(form, context({ kind: 'artwork', current: {} })).map(
			(each) => each.code
		);
		expect(codes).toEqual(['attribution.confirmed_requires_citation']);
	});

	it('keeps at least one Artwork on a Documentation item', () => {
		const form = emptyRecordForm();
		form.links.artworks = { added: [], removed: [11] };
		const codes = validateRecord(
			form,
			context({ kind: 'documentation_item', current: { medium: 'image', artworks: [11] } })
		).map((each) => each.code);
		expect(codes).toEqual(['documentation_item.artworks_required']);
	});
});

describe('the Artwork editors', () => {
	it('adds documentation with a History event that cites it', () => {
		const form = emptyForm();
		form.target = { id: 9, title: 'Gatto' };
		form.sources.push({
			key: 'source-1',
			title: 'Zine',
			author: '',
			publication: '',
			url: '',
			note: ''
		});
		form.event.shows = true;
		form.event.type = 'damaged';
		const copy = artworkCopy(form, TODAY, 'documentation');
		const ops = operations(copy);
		expect(ops.at(-1)).toMatchObject({
			op: 'add',
			target: 9,
			collection: 'history_events',
			item: { type: 'damaged', citations: [{ new: 'source-1' }] }
		});
		expect(artworkEditorOf(copy)).toBe('documentation');
		expect(artworkFrom(copy).target).toEqual({ id: 9, title: 'Gatto' });
	});

	it('reads the editor of a round that has no editor part', () => {
		expect(
			artworkEditorOf({ operations: [{ op: 'set', target: 1, field: 'title', value: 'x' }] })
		).toBe('edit');
		expect(
			artworkEditorOf({
				operations: [{ op: 'add', target: 1, collection: 'history_events', item: {} }]
			})
		).toBe('event');
		expect(artworkEditorOf(null)).toBe('edit');
	});
});
