import { describe, expect, it } from 'vitest';
import {
	chooseAttribution,
	chooseField,
	creationEvents,
	editAdded,
	isKept,
	isRepointed,
	keyOf,
	recordsOf,
	setKept,
	setRepointed,
	usesSourceAttribution,
	usesSourceField,
	type Entry,
	type Op
} from './ops';

const INTO = 2;
const MERGE: Op = { op: 'merge', source: 1, into: INTO };
const fromSource: Entry = { collection: 'aliases', key: 'FH', item: 'FH', origin: 'source' };
const fromInto: Entry = { collection: 'aliases', key: 'FB', item: 'FB', origin: 'into' };
const added: Op = { op: 'add', target: INTO, collection: 'aliases', item: 'FH' };

describe('the choices of a Merge', () => {
	it('keeps an item of the folded record when an add operation names it', () => {
		expect(isKept([added, MERGE], INTO, fromSource)).toBe(true);
		expect(isKept([MERGE], INTO, fromSource)).toBe(false);
	});

	it('drops and restores an item of the folded record by removing and adding its operation', () => {
		const dropped = setKept([added, MERGE], INTO, fromSource, false);
		expect(dropped).toEqual([MERGE]);
		expect(setKept(dropped, INTO, fromSource, true)).toEqual([added, MERGE]);
	});

	it('drops an item of the survivor with a remove operation, placed before the Merge', () => {
		const dropped = setKept([MERGE], INTO, fromInto, false);
		expect(dropped).toEqual([
			{ op: 'remove', target: INTO, collection: 'aliases', key: 'FB' },
			MERGE
		]);
		expect(isKept(dropped, INTO, fromInto)).toBe(false);
		expect(setKept(dropped, INTO, fromInto, true)).toEqual([MERGE]);
	});

	it('edits an added Alias in place', () => {
		const edited = editAdded([added, MERGE], INTO, fromSource, 'F. H.');
		expect(edited[0]).toEqual({ ...added, item: 'F. H.' });
		expect(isKept(edited, INTO, fromSource)).toBe(false);
	});

	it('leaves its argument alone', () => {
		const before: Op[] = [added, MERGE];
		setKept(before, INTO, fromSource, false);
		expect(before).toEqual([added, MERGE]);
	});

	it('takes a field of the folded record with a set operation', () => {
		const chosen = chooseField([MERGE], INTO, 'name', 'Fictional Hand', true);
		expect(chosen).toEqual([
			{ op: 'set', target: INTO, field: 'name', value: 'Fictional Hand' },
			MERGE
		]);
		expect(usesSourceField(chosen, INTO, 'name')).toBe(true);
		expect(chooseField(chosen, INTO, 'name', 'Fictional Hand', false)).toEqual([MERGE]);
	});

	it('takes the folded record Attribution to an Artist with a change operation', () => {
		const item = { artist: 9, certainty: 'probable' };
		const chosen = chooseAttribution([MERGE], INTO, 9, item, true);
		expect(usesSourceAttribution(chosen, INTO, 9)).toBe(true);
		expect(chooseAttribution(chosen, INTO, 9, item, false)).toEqual([MERGE]);
	});

	it('counts the Creation events the merged result would hold', () => {
		const created = (id: number, origin: Entry['origin']): Entry => ({
			collection: 'history_events',
			key: { new: `e${id}` },
			item: { id: { new: `e${id}` }, type: 'created' },
			origin
		});
		const entries = [created(1, 'source'), created(2, 'into')];
		const keep = { op: 'add', target: INTO, collection: 'history_events', item: entries[0].item };
		expect(creationEvents([keep, MERGE], INTO, entries)).toBe(2);
		expect(creationEvents([MERGE], INTO, entries)).toBe(1);
	});

	it('names the key of an item as the API does', () => {
		expect(keyOf('attributions', { artist: 4 })).toBe(4);
		expect(keyOf('history_events', { id: 12 })).toBe(12);
		expect(keyOf('crew_memberships', { collective: 5 })).toEqual([5, null]);
		expect(keyOf('sources', 8)).toBe(8);
	});

	it('finds the records of the Submission in its Merge operation', () => {
		expect(recordsOf([added, MERGE])).toEqual({ source: 1, into: INTO });
	});
});

describe('the choices of an Unmerge', () => {
	const back: Op = { op: 'add', target: 7, collection: 'attributions', item: { artist: 1 } };
	const initial: Op[] = [back, { op: 'unmerge', source: 1, into: INTO }];

	it('points a record back by the operations that target it', () => {
		expect(isRepointed(initial, 7)).toBe(true);
		const left = setRepointed(initial, initial, 7, false);
		expect(isRepointed(left, 7)).toBe(false);
		expect(left).toEqual([{ op: 'unmerge', source: 1, into: INTO }]);
		expect(setRepointed(left, initial, 7, true)).toEqual(initial);
	});
});
