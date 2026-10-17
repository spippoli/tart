/**
 * The Locations an editor can put a record on, found by a text (the Artworks matching it,
 * grouped by the Location they are on) or near a point (the proximity rule's candidates).
 */
import { locationTitleText } from '#lib/archive/records.ts';
import type { Point } from '#lib/map/coordinates.ts';
import type { LocationOption } from '#lib/map/LocationEntry.svelte';
import { m } from '#lib/paraglide/messages.js';
import type { Locale } from '#lib/paraglide/runtime.js';
import * as api from './api';

export async function findLocations(
	query: { text?: string; near?: Point },
	surfaceLabel: (key: string) => string,
	locale: Locale
): Promise<LocationOption[]> {
	if (query.near) {
		const found = await api.locationCandidates({
			geometry: { type: 'Point', coordinates: query.near },
			radius: null
		});
		if (!found.ok) return [];
		return found.value.candidates.map((candidate) => ({
			id: String(candidate.location.id),
			title: locationTitleText(
				candidate.location.id,
				candidate.location.title,
				surfaceLabel,
				locale
			)
		}));
	}
	const text = (query.text ?? '').trim();
	if (text.length < 2) return [];
	const found = await api.searchArtworks(text);
	if (!found.ok) return [];
	const byLocation: Record<number, { title: string; artworks: string[] }> = {};
	for (const entry of found.value.entries) {
		const place = entry.site?.name ?? entry.area?.name ?? null;
		byLocation[entry.location] ??= {
			title: place ?? m.archive_location_fallback({ id: String(entry.location) }),
			artworks: []
		};
		byLocation[entry.location].artworks.push(entry.title ?? m.archive_untitled());
	}
	return Object.entries(byLocation).map(([id, each]) => ({
		id,
		title: each.title,
		description: each.artworks.join(', ')
	}));
}
