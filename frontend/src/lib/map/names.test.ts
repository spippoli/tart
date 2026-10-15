import { describe, expect, it } from 'vitest';
import type { LocationProperties } from './locations';
import { clusterName, signName } from './names';

const location = (values: Partial<LocationProperties>): LocationProperties => ({
	id: 1,
	present: 0,
	unknown: 0,
	disappeared: 0,
	point: [12.5, 41.9],
	approximate: false,
	radius: null,
	...values
});

describe('accessible names', () => {
	it('give the counts per Condition group', () => {
		expect(signName(location({ present: 1, disappeared: 2 }), 'en')).toBe(
			'Location, 3 artworks: 1 present, 2 disappeared'
		);
		expect(signName(location({ unknown: 1 }), 'en')).toBe('Location, 1 artwork: 1 unknown');
		expect(signName(location({ present: 2, disappeared: 1 }), 'it')).toBe(
			'Superficie, 3 opere: 2 presenti, 1 scomparsa'
		);
	});

	it('state an approximate position in words', () => {
		expect(signName(location({ present: 1, approximate: true }), 'en')).toBe(
			'Location, 1 artwork: 1 present, approximate position'
		);
	});

	it('name a cluster and tell how to use it', () => {
		expect(clusterName(24, 9, 'en')).toBe(
			'Cluster of 24 artworks in 9 Locations; activate to zoom in'
		);
		expect(clusterName(2, 1, 'it')).toBe(
			'Gruppo di 2 opere su 1 superficie; attiva per ingrandire'
		);
	});
});
