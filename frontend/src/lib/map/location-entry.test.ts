import { describe, expect, it } from 'vitest';
import { describePoint, parseRadius } from './location-entry';

// Discovery criteria 42 and 43: the parsed point is confirmed in words; the radius is optional.
describe('AC 42, 43: the Location entry rules', () => {
	it('confirms a point in words, with hemisphere letters, in the UI language', () => {
		expect(describePoint([12.4769, 41.8986], 'en')).toEqual({
			latitude: '41.8986 N',
			longitude: '12.4769 E'
		});
		expect(describePoint([12.4769, 41.8986], 'it')).toEqual({
			latitude: '41,8986 N',
			longitude: '12,4769 E'
		});
		expect(describePoint([-43.2, -22.9], 'en')).toEqual({
			latitude: '22.9 S',
			longitude: '43.2 W'
		});
	});

	it('takes an uncertainty radius as whole metres above zero, or none', () => {
		expect(parseRadius('')).toEqual({ metres: null });
		expect(parseRadius(' 150 ')).toEqual({ metres: 150 });
		for (const text of ['0', '-5', '1.5', '10 m', 'abc']) {
			expect(parseRadius(text)).toEqual({ error: 'invalid' });
		}
	});
});
