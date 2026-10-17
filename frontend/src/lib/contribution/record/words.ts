/**
 * The words of the editor of a record: a field's label, and what the record holds now,
 * said as the page of the record would say it (Contribution and moderation spec, Other
 * editors: "per field: Edit reveals current vs proposed").
 */
import { vocabularyLabels } from '#lib/archive/records.ts';
import {
	formatPeriod,
	formatUncertainDate,
	type Period,
	type UncertainDate
} from '#lib/archive/uncertain-date.ts';
import { describePoint } from '#lib/map/location-entry.ts';
import { m } from '#lib/paraglide/messages.js';
import type { Json } from './form';
import type { RecordEditorState } from './state.svelte';
import type { FieldSpec } from './spec';

const labels: Record<string, () => string> = {
	title: m.editor_field_title,
	expression_types: m.editor_field_expression_types,
	description: m.editor_field_description,
	location: m.editor_field_location,
	geometry: m.editor_field_geometry,
	approximate: m.editor_field_approximate,
	uncertainty_radius: m.editor_field_uncertainty_radius,
	surface_type: m.editor_field_surface_type,
	site: m.editor_field_site,
	place_description: m.editor_field_place_description,
	name: m.editor_field_name,
	kind: m.editor_field_kind,
	biography: m.editor_field_biography,
	period: m.editor_field_period,
	author: m.editor_field_author,
	publication: m.editor_field_publication,
	date: m.editor_field_date,
	url: m.editor_field_url,
	note: m.editor_field_note,
	language: m.editor_field_language,
	observed_date: m.editor_field_observed_date,
	alt_text: m.editor_field_alt_text,
	text: m.editor_field_text
};

export function fieldLabel(name: string): string {
	return (labels[name] ?? (() => name))();
}

const collections: Record<string, () => string> = {
	attributions: m.editor_collection_attributions,
	series: m.editor_collection_series,
	sources: m.editor_collection_sources,
	aliases: m.editor_collection_aliases,
	areas: m.editor_collection_areas,
	crew_memberships: m.editor_collection_crew,
	artworks: m.editor_collection_artworks
};

export function collectionLabel(name: string): string {
	return (collections[name] ?? (() => name))();
}

const isObject = (value: unknown): value is Record<string, unknown> =>
	typeof value === 'object' && value !== null && !Array.isArray(value);

/** A geometry in a few words: its shape, and where a point is. */
export function geometryWords(geometry: unknown, locale: string): string {
	if (!isObject(geometry)) return m.editor_value_none();
	if (geometry.type === 'Point' && Array.isArray(geometry.coordinates)) {
		const { latitude, longitude } = describePoint(
			[Number(geometry.coordinates[0]), Number(geometry.coordinates[1])],
			locale
		);
		return `${m.draw_shape_point()} · ${latitude}, ${longitude}`;
	}
	const ring = Array.isArray(geometry.coordinates)
		? geometry.type === 'Polygon'
			? ((geometry.coordinates[0] as unknown[]) ?? []).length - 1
			: geometry.coordinates.length
		: 0;
	const shape = geometry.type === 'LineString' ? m.draw_shape_line() : m.draw_shape_polygon();
	return `${shape} · ${m.draw_status_count({ count: ring })}`;
}

/** What the record holds in a field now, for the "current" line; free text is left as it is. */
export function currentText(
	spec: FieldSpec,
	json: Json | undefined,
	editor: RecordEditorState
): string {
	return editor.redacted(spec.name) ? m.editor_value_redacted() : describeJson(spec, json, editor);
}

/** A field's value, as the changeset says it, in words. */
export function describeJson(
	spec: FieldSpec,
	json: Json | undefined,
	editor: RecordEditorState
): string {
	const none = m.editor_value_none();
	if (json === null || json === undefined || json === '') {
		return spec.type === 'title' ? m.archive_untitled() : none;
	}
	const { locale, timeZone } = editor.config;
	switch (spec.type) {
		case 'select': {
			if (spec.vocabulary === 'artist_kinds') {
				return json === 'collective'
					? m.archive_artist_collective()
					: m.archive_artist_individual();
			}
			const vocabulary =
				spec.vocabulary === 'surface_types'
					? editor.config.surfaceTypes
					: editor.config.expressionTypes;
			return vocabularyLabels(vocabulary, locale)(String(json));
		}
		case 'choices': {
			const label = vocabularyLabels(editor.config.expressionTypes, locale);
			const keys = Array.isArray(json) ? json.map(String) : [];
			return keys.length ? keys.map(label).join(', ') : none;
		}
		case 'approximate':
			return json === true ? m.editor_location_approximate() : m.editor_location_exact();
		case 'radius':
			return m.editor_value_metres({ metres: Number(json) });
		case 'date':
			return isObject(json)
				? formatUncertainDate(json as UncertainDate, { locale, timeZone })
				: none;
		case 'period':
			return (isObject(json) && formatPeriod(json as Period, { locale, timeZone })) || none;
		case 'geometry':
			return geometryWords(json, locale);
		case 'site':
		case 'location':
			return typeof json === 'number' ? editor.name(json) : none;
		default:
			return String(json);
	}
}
