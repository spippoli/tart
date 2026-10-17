import { describe, expect, it } from 'vitest';
import {
	emptyDate,
	fromUncertainDate,
	isEmptyDate,
	toUncertainDate,
	todayIn,
	type DateField
} from './date-field';

const TODAY = '2026-10-16';
const field = (overrides: Partial<DateField>): DateField => ({ ...emptyDate(), ...overrides });

describe('the Uncertain date input', () => {
	it('gives the first day of the unit each precision names', () => {
		const date = (precision: DateField['precision'], first: string) =>
			toUncertainDate(field({ precision, first }), TODAY);
		expect(date('day', '2019-03-12')).toEqual({
			date: { precision: 'day', qualifier: 'exact', first: '2019-03-12', second: null }
		});
		expect(date('month', '2019-03')).toMatchObject({ date: { first: '2019-03-01' } });
		expect(date('year', '2019')).toMatchObject({ date: { first: '2019-01-01' } });
		// Any year of a decade names the decade.
		expect(date('decade', '1995')).toMatchObject({ date: { first: '1990-01-01' } });
	});

	it('keeps the qualifier, and a range only with exact', () => {
		expect(
			toUncertainDate(field({ qualifier: 'circa', precision: 'year', first: '2019' }), TODAY)
		).toMatchObject({ date: { qualifier: 'circa' } });
		expect(
			toUncertainDate(field({ precision: 'year', first: '2010', second: '2012' }), TODAY)
		).toEqual({
			date: { precision: 'year', qualifier: 'exact', first: '2010-01-01', second: '2012-01-01' }
		});
		expect(
			toUncertainDate(
				field({ qualifier: 'circa', precision: 'year', first: '2010', second: '2012' }),
				TODAY
			)
		).toMatchObject({ problem: 'range_needs_exact' });
		expect(
			toUncertainDate(field({ precision: 'year', first: '2012', second: '2010' }), TODAY)
		).toMatchObject({ problem: 'second_not_later', field: 'second' });
	});

	it('stores "Unknown date" with no value and no qualifier', () => {
		expect(toUncertainDate(field({ unknown: true, first: '2019' }), TODAY)).toEqual({
			date: { precision: 'unknown' }
		});
		expect(isEmptyDate(field({ unknown: true }))).toBe(false);
	});

	it('says nothing for an empty field, and names what is wrong otherwise', () => {
		expect(toUncertainDate(emptyDate(), TODAY)).toEqual({ date: null });
		expect(toUncertainDate(field({ first: '2019-02-30' }), TODAY)).toMatchObject({
			problem: 'invalid'
		});
		expect(toUncertainDate(field({ precision: 'month', first: '2019-13' }), TODAY)).toMatchObject({
			problem: 'invalid'
		});
		expect(toUncertainDate(field({ precision: 'year', first: '19' }), TODAY)).toMatchObject({
			problem: 'invalid'
		});
		expect(toUncertainDate(field({ precision: 'year', first: '2027' }), TODAY)).toMatchObject({
			problem: 'in_future'
		});
	});

	it('reads a stored date back into the field', () => {
		const stored = {
			precision: 'month',
			qualifier: 'circa',
			first: '2016-03-01',
			second: null
		} as const;
		const back = fromUncertainDate(stored);
		expect(back).toMatchObject({ precision: 'month', qualifier: 'circa', first: '2016-03' });
		expect(toUncertainDate(back, TODAY)).toEqual({ date: stored });
		expect(fromUncertainDate({ precision: 'unknown' }).unknown).toBe(true);
		expect(isEmptyDate(fromUncertainDate(null))).toBe(true);
	});

	it('takes today in the Instance time zone', () => {
		const instant = new Date('2026-10-16T23:30:00Z');
		expect(todayIn('Europe/Rome', instant)).toBe('2026-10-17');
		expect(todayIn('UTC', instant)).toBe('2026-10-16');
	});
});
