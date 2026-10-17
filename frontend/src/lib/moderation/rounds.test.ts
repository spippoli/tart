import { describe, expect, it } from 'vitest';
import { diffRounds, operationsOf } from './rounds';

const title = { op: 'set', target: 7, field: 'title', value: 'Gatto' };
const description = { op: 'set', target: 7, field: 'description', value: 'Un gatto fittizio.' };

describe('operationsOf', () => {
	it('reads the operations of a snapshot and nothing else', () => {
		expect(operationsOf({ operations: [title] })).toEqual([title]);
		expect(operationsOf(null)).toEqual([]);
		expect(operationsOf({ operations: 'no' })).toEqual([]);
	});
});

describe('diffRounds', () => {
	it('marks what the round adds and lists what it leaves out', () => {
		const diff = diffRounds({ operations: [title, description] }, { operations: [title] });

		expect(diff.current).toEqual([{ operation: title, fresh: false }]);
		expect(diff.removed).toEqual([description]);
	});

	it('marks every operation of a first comparison as new', () => {
		const diff = diffRounds(null, { operations: [title] });

		expect(diff.current).toEqual([{ operation: title, fresh: true }]);
		expect(diff.removed).toEqual([]);
	});

	it('does not mind the order of the keys', () => {
		const same = { value: 'Gatto', field: 'title', target: 7, op: 'set' };

		expect(diffRounds({ operations: [title] }, { operations: [same] }).current[0].fresh).toBe(
			false
		);
	});

	it('sees a changed value as one operation out and one in', () => {
		const changed = { ...title, value: 'Gatto sul portone' };
		const diff = diffRounds({ operations: [title] }, { operations: [changed] });

		expect(diff.current).toEqual([{ operation: changed, fresh: true }]);
		expect(diff.removed).toEqual([title]);
	});
});
