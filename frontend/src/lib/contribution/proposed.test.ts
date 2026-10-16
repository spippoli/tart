import { describe, expect, it } from 'vitest';
import { describeValue, proposedOperations } from './proposed';

describe('proposedOperations', () => {
	it('reads each operation of a snapshot', () => {
		const operations = proposedOperations({
			operations: [
				{
					op: 'create',
					ref: 'a',
					kind: 'artwork',
					record: { title: 'Muro', notes: null, tags: [] }
				},
				{ op: 'set', target: 7, field: 'title', value: 'Nuovo titolo' },
				{ op: 'add', target: 7, collection: 'history', item: { type: 'overpainted' } },
				{ op: 'remove', target: 7, collection: 'history', key: 3 },
				{ op: 'unknown' }
			]
		});

		expect(operations).toEqual([
			{ type: 'create', subject: 'artwork', entries: [['title', 'Muro']] },
			{ type: 'set', subject: 'title', entries: [['title', 'Nuovo titolo']] },
			{ type: 'add', subject: 'history', entries: [['type', 'overpainted']] },
			{ type: 'remove', subject: 'history', entries: [['history', '3']] }
		]);
	});

	it('answers nothing for what is not a snapshot', () => {
		expect(proposedOperations(null)).toEqual([]);
		expect(proposedOperations({ operations: 'x' })).toEqual([]);
	});

	it('shows structured values as JSON', () => {
		expect(describeValue({ a: 1 })).toBe('{"a":1}');
		expect(describeValue(null)).toBe('');
	});
});
