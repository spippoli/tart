import { describe, expect, it } from 'vitest';
import { SIGN_KINDS, SMALL_SIGN_SIZE, signShapes } from './signs';

const TOKENS = {
	'map.paper': '#F3EEE2',
	'map.ink': '#2A2521',
	'marker.ink': '#1F1B18',
	'map.label.district': '#5E4636',
	'marker.accent': '#7A2E1C'
};

describe('the archive signs', () => {
	it('tells the three Condition signs apart by shape, not colour', () => {
		const [present, unknown, disappeared] = (['present', 'unknown', 'disappeared'] as const).map(
			(kind) => signShapes(kind, TOKENS, SMALL_SIGN_SIZE)
		);
		// Solid and filled; dotted with a "?" drawn as a path; dashed.
		expect(present).toHaveLength(1);
		expect(present[0].dash).toBeUndefined();
		expect(present[0].fill).toBe(TOKENS['marker.ink']);
		expect(unknown).toHaveLength(2);
		expect(unknown[0].dash).toBeDefined();
		expect(disappeared[0].dash).toBeDefined();
		expect(unknown[0].dash).not.toEqual(disappeared[0].dash);
	});

	it('colours every sign from the style tokens only', () => {
		const colours = new Set(Object.values(TOKENS));
		for (const kind of SIGN_KINDS) {
			for (const shape of signShapes(kind, TOKENS)) {
				for (const colour of [shape.fill, shape.stroke]) {
					if (colour !== undefined) expect(colours).toContain(colour);
				}
			}
		}
	});

	it('draws the cluster as a neutral circle, never in the accent', () => {
		const [circle] = signShapes('cluster', TOKENS);
		expect(circle.stroke).toBe(TOKENS['map.ink']);
		expect(circle.fill).toBe(TOKENS['map.paper']);
	});
});
