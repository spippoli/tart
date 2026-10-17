import { describe, expect, it } from 'vitest';
import { operationRows } from './rows';

const snapshot = {
	operations: [
		{ op: 'set', target: 7, field: 'title', value: 'Gatto sul portone' },
		{ op: 'unknown' },
		{ op: 'set', target: 7, field: 'description', value: 'Un gatto fittizio.' }
	]
};

describe('operationRows', () => {
	it('sets what an operation replaces beside it, by the operation’s position in the round', () => {
		const rows = operationRows(snapshot, [
			{ index: 0, current: 'Gatto' },
			{ index: 2, current: null }
		]);

		expect(rows.map((row) => [row.operation.subject, row.current, row.compared])).toEqual([
			['title', 'Gatto', true],
			['description', null, true]
		]);
	});

	it('leaves an operation with nothing to compare uncompared', () => {
		const rows = operationRows(snapshot, []);

		expect(rows.every((row) => !row.compared && row.current === null)).toBe(true);
	});

	it('carries which operations are new in the round', () => {
		const rows = operationRows(snapshot, [], [true, false, false]);

		expect(rows.map((row) => row.fresh)).toEqual([true, false]);
	});
});
