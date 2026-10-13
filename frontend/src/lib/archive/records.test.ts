import { describe, expect, it } from 'vitest';
import {
	attributionSummary,
	evidenceWords,
	linkText,
	locationTitleText,
	reportHref,
	type ShownAttribution
} from './records';

const artist = (id: number, name: string | null) => ({
	kind: 'artist' as const,
	id,
	path: `${id}`,
	name
});
const shown = (
	id: number,
	name: string,
	certainty: ShownAttribution['certainty']
): ShownAttribution => ({
	artist: artist(id, name),
	certainty,
	alias: null,
	note: null,
	evidence_level: 'reported',
	citations: []
});
const surface = (key: string) => ({ building_wall: 'Building wall' })[key] ?? key;

describe('Attribution summary (criterion 8)', () => {
	it('reads "Unknown artist" without Attributions', () => {
		expect(attributionSummary({ attributed: [], disputed: [] }, 'en')).toBe('Unknown artist');
	});

	it('lists a collaboration, marking probable ones', () => {
		const readout = {
			attributed: [shown(1, 'Nebbia Finta', 'confirmed'), shown(2, 'Lupo Inventato', 'probable')],
			disputed: []
		};
		expect(attributionSummary(readout, 'en')).toBe(
			'Nebbia Finta and Lupo Inventato — probable attribution'
		);
	});

	it('reads disputed alternatives as "A or B"', () => {
		const readout = {
			attributed: [],
			disputed: [shown(1, 'Lupo Inventato', 'disputed'), shown(2, 'Ombra Supposta', 'disputed')]
		};
		expect(attributionSummary(readout, 'it')).toBe(
			'Attribuzione contesa: Lupo Inventato o Ombra Supposta'
		);
	});
});

describe('Evidence level words', () => {
	it('counts sources in the UI language', () => {
		expect(evidenceWords('documented', 1, 'en')).toBe('documented · 1 source');
		expect(evidenceWords('documented', 2, 'it')).toBe('documentato · 2 fonti');
		expect(evidenceWords('reported', 0, 'en')).toBe('reported · no sources cited');
	});
});

describe('Location title (criterion 48)', () => {
	it('is the Place description, else Surface type · place, else "Location {id}"', () => {
		expect(locationTitleText(4, { place_description: 'Muro fittizio' }, surface, 'en')).toBe(
			'Muro fittizio'
		);
		expect(
			locationTitleText(
				4,
				{ surface_type: 'building_wall', place: 'Rione di Prova' },
				surface,
				'en'
			)
		).toBe('Building wall · Rione di Prova');
		expect(locationTitleText(4, {}, surface, 'it')).toBe('Superficie 4');
	});

	it('names an untitled Artwork "Untitled"', () => {
		expect(linkText({ kind: 'artwork', id: 3, path: '3', name: null }, surface, 'en')).toBe(
			'Untitled'
		);
	});
});

describe('Report link', () => {
	it('names the reported object in each language', () => {
		expect(reportHref('it', 'artwork', 16)).toBe('/it/segnala?oggetto=artwork%3A16');
		expect(reportHref('en', 'artwork', 16, 5)).toBe('/en/report?object=artwork%3A16%23revision-5');
	});
});
