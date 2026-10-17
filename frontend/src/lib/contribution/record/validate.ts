/**
 * What an edit of a record, or a new Area or Artist, must satisfy before it is submitted
 * (Contribution and moderation spec, Validation rules): the rules of the archive that a form
 * can know, run in the browser so that one failed submit lists every error at once, each
 * linked to its field. The server validates again, against the archive as it is, and answers
 * with a stable error code; `recordServerError` places that code in the form.
 *
 * It runs on submit only (acceptance criterion 12), never while the person types.
 */
import type { Kind } from '#lib/archive/records.ts';
import { parseRadius } from '#lib/map/location-entry.ts';
import { toUncertainDate, type DateField } from '../date-field';
import { PLACE_DESCRIPTION_MAX, ALT_TEXT_MAX } from '../form';
import type { StepError, StepState } from '../session';
import { stepStates } from '../validate';
import {
	valueToJson,
	type AttributionEdit,
	type Json,
	type PeriodField,
	type RecordForm,
	type SiteValue,
	type TitleValue
} from './form';
import { SPECS, type CollectionSpec, type FieldSpec } from './spec';

export interface RecordContext {
	kind: Kind;
	/** The record an edit changes, as stored; empty for a new record. */
	current: { [key: string]: Json };
	creating: boolean;
	today: string;
	surfaceTypes: ReadonlySet<string>;
	expressionTypes: ReadonlySet<string>;
	acceptanceRequired: boolean;
	termsAccepted: boolean;
}

export const ids = {
	changes: 'editor-changes',
	field: (name: string) => `record-field-${name}`,
	collection: (name: string) => `record-${name}`,
	add: (name: string) => `record-${name}-add`,
	attribution: (key: string, field: string) => `record-attribution-${key}-${field}`,
	crew: (key: string) => `record-crew-${key}`,
	created: (key: string, field: string) => `record-new-${key}-${field}`,
	terms: 'editor-terms',
	source: (key: string, field: string) => `editor-source-${key}-${field}`
};

const URL_PATTERN = /^https?:\/\/\S+$/;

/** The step that asks a field of a new record. */
export function stepOfField(field: FieldSpec, creating: boolean): string {
	if (!creating) return 'changes';
	return field.step ?? (field.type === 'geometry' ? 'geometry' : 'identity');
}

export function stepOfCollection(collection: CollectionSpec, creating: boolean): string {
	return creating ? (collection.step ?? 'activity') : 'changes';
}

function dateProblem(
	field: DateField,
	id: string,
	step: string,
	today: string,
	required: boolean
): StepError[] {
	const outcome = toUncertainDate(field, today);
	if ('problem' in outcome) {
		const where =
			outcome.field === 'second'
				? `${id}-second`
				: outcome.field === 'qualifier'
					? `${id}-qualifier`
					: id;
		return [{ id: where, step, code: `date.${outcome.problem}` }];
	}
	return required && outcome.date === null ? [{ id, step, code: 'field.required' }] : [];
}

/** The value a field has after the change: the proposed one, else what the record holds. */
function effective(field: FieldSpec, form: RecordForm, context: RecordContext): Json {
	return field.name in form.fields
		? valueToJson(field, form.fields[field.name], context.today)
		: (context.current[field.name] ?? null);
}

function fieldErrors(field: FieldSpec, form: RecordForm, context: RecordContext): StepError[] {
	const { kind, creating, today } = context;
	const step = stepOfField(field, creating);
	const id = ids.field(field.name);
	const value = form.fields[field.name];
	const errors: StepError[] = [];
	const blank = (json: Json) =>
		json === null || json === '' || (Array.isArray(json) && !json.length);
	const json = valueToJson(field, value, today);

	switch (field.type) {
		case 'text':
		case 'oneline':
		case 'multiline':
		case 'language': {
			if (field.required && blank(json)) errors.push({ id, step, code: 'field.required' });
			const entered = typeof json === 'string' ? json : '';
			if (field.name === 'url' && entered) {
				if (!URL_PATTERN.test(entered)) {
					errors.push({
						id,
						step,
						code: kind === 'source' ? 'source.url_invalid' : 'documentation.url_invalid'
					});
				}
			} else if (field.name === 'url' && kind === 'documentation_item') {
				errors.push({ id, step, code: 'documentation.url_required' });
			}
			if (field.name === 'place_description') {
				const raw = typeof value === 'string' ? value : '';
				if (raw.length > PLACE_DESCRIPTION_MAX) {
					errors.push({
						id,
						step,
						code: 'location.place_description_too_long',
						params: { max: PLACE_DESCRIPTION_MAX }
					});
				} else if (/[\r\n]/.test(raw)) {
					errors.push({ id, step, code: 'location.place_description_not_one_line' });
				}
			}
			if (field.name === 'alt_text') {
				const raw = typeof value === 'string' ? value : '';
				if (!raw.trim()) errors.push({ id, step, code: 'documentation.alt_required' });
				else if (raw.length > ALT_TEXT_MAX) {
					errors.push({
						id,
						step,
						code: 'documentation.alt_too_long',
						params: { max: ALT_TEXT_MAX }
					});
				}
			}
			break;
		}
		case 'title': {
			const title = value as TitleValue;
			if (!title.untitled && !title.text.trim()) {
				errors.push({ id, step, code: 'artwork.title_required' });
			}
			break;
		}
		case 'select':
			if (field.vocabulary === 'surface_types') {
				if (!json) errors.push({ id, step, code: 'location.surface_type_required' });
				else if (!context.surfaceTypes.has(String(json))) {
					errors.push({ id, step, code: 'location.surface_type_unknown' });
				}
			} else if (field.required && blank(json)) {
				errors.push({ id, step, code: 'field.required' });
			}
			break;
		case 'choices':
			if (field.required && blank(json)) {
				errors.push({ id, step, code: 'artwork.expression_types_required' });
			} else if (
				field.vocabulary === 'expression_types' &&
				(json as string[]).some((key) => !context.expressionTypes.has(key))
			) {
				errors.push({ id, step, code: 'artwork.expression_type_unknown' });
			}
			break;
		case 'date':
			errors.push(...dateProblem(value as DateField, id, step, today, field.required === true));
			break;
		case 'period': {
			const period = value as PeriodField;
			errors.push(
				...dateProblem(period.start, `${id}-start`, step, today, false),
				...dateProblem(period.end, `${id}-end`, step, today, false)
			);
			break;
		}
		case 'geometry':
			if (json === null) {
				errors.push({
					id,
					step,
					code: kind === 'location' ? 'location.required' : 'geometry.required'
				});
			}
			break;
		case 'location':
			if (field.required && json === null) {
				errors.push({ id, step, code: 'location.required' });
			}
			break;
		case 'site': {
			const site = value as SiteValue;
			if (site.kind === 'new' && !form.sites.some((each) => each.key === site.key)) {
				errors.push({ id, step, code: 'site.name_required' });
			}
			break;
		}
		case 'approximate':
		case 'radius':
			break;
	}
	return errors;
}

/** The radius is for an approximate point only, whichever of the three fields is edited. */
function radiusErrors(form: RecordForm, context: RecordContext): StepError[] {
	if (context.kind !== 'location') return [];
	const specs = SPECS.location.fields;
	const [geometry, approximate, radius] = ['geometry', 'approximate', 'uncertainty_radius'].map(
		(name) =>
			effective(
				specs.find((each) => each.name === name)!,
				form,
				context
			)
	);
	const step = 'changes';
	const id = ids.field('uncertainty_radius');
	if (
		'uncertainty_radius' in form.fields &&
		typeof form.fields.uncertainty_radius === 'string' &&
		form.fields.uncertainty_radius.trim() !== '' &&
		'error' in parseRadius(form.fields.uncertainty_radius)
	) {
		return [{ id, step, code: 'location.radius_not_positive' }];
	}
	if (radius !== null) {
		const point =
			typeof geometry === 'object' && geometry !== null && !Array.isArray(geometry)
				? geometry.type === 'Point'
				: false;
		if (!(approximate === true && point)) {
			return [{ id, step, code: 'location.radius_requires_approximate_point' }];
		}
	}
	return [];
}

function attributionErrors(each: AttributionEdit, seen: Set<string>, step: string): StepError[] {
	const id = (field: string) => ids.attribution(each.key, field);
	const errors: StepError[] = [];
	const artist = each.artist;
	if (!artist) {
		errors.push({ id: id('artist'), step, code: 'attribution.artist_required' });
	} else {
		const identity = artist.id !== null ? `artist:${artist.id}` : String(artist.key);
		if (seen.has(identity)) {
			errors.push({ id: id('artist'), step, code: 'attribution.artist_duplicated' });
		}
		seen.add(identity);
	}
	if (!each.certainty) {
		errors.push({ id: id('certainty'), step, code: 'attribution.certainty_required' });
	} else if (each.certainty === 'confirmed' && each.citations.length === 0) {
		errors.push({ id: id('citations'), step, code: 'attribution.confirmed_requires_citation' });
	}
	return errors;
}

function collectionErrors(
	collection: CollectionSpec,
	form: RecordForm,
	context: RecordContext
): StepError[] {
	const step = stepOfCollection(collection, context.creating);
	const errors: StepError[] = [];
	const present = Array.isArray(context.current[collection.name])
		? (context.current[collection.name] as Json[]).length
		: 0;
	switch (collection.type) {
		case 'links': {
			const delta = form.links[collection.name];
			if (collection.required && !context.creating) {
				const left = present - (delta?.removed.length ?? 0) + (delta?.added.length ?? 0);
				if (left < 1) {
					errors.push({
						id: ids.add(collection.name),
						step,
						code: 'documentation_item.artworks_required'
					});
				}
			}
			break;
		}
		case 'attributions': {
			const seen = new Set<string>();
			const removed = new Set(form.attributions.removed);
			const current = Array.isArray(context.current.attributions)
				? (context.current.attributions as Json[])
				: [];
			for (const existing of current) {
				const artist = (existing as { artist: number }).artist;
				if (!removed.has(artist) && !(String(artist) in form.attributions.changed)) {
					seen.add(`artist:${artist}`);
				}
			}
			for (const each of Object.values(form.attributions.changed)) {
				errors.push(...attributionErrors(each, seen, step));
			}
			for (const each of form.attributions.added) {
				errors.push(...attributionErrors(each, seen, step));
			}
			break;
		}
		case 'crew':
			for (const each of form.crew.added) {
				if (!each.collective) {
					errors.push({
						id: ids.crew(each.key),
						step,
						code: 'crew_membership.collective_required'
					});
				}
				errors.push(
					...dateProblem(
						each.period.start,
						`${ids.crew(each.key)}-start`,
						step,
						context.today,
						false
					),
					...dateProblem(each.period.end, `${ids.crew(each.key)}-end`, step, context.today, false)
				);
			}
			break;
		case 'aliases':
			break;
	}
	return errors;
}

/** Every rule broken, in the order of the steps and of the fields in each. */
export function validateRecord(form: RecordForm, context: RecordContext): StepError[] {
	const spec = SPECS[context.kind];
	const errors: StepError[] = [];
	const { creating } = context;

	for (const field of spec.fields) {
		if (!creating && !(field.name in form.fields)) continue;
		if (creating && form.fields[field.name] === undefined) {
			// A field of a new record that was never touched is empty.
			if (field.required) {
				errors.push({
					id: ids.field(field.name),
					step: stepOfField(field, creating),
					code: field.type === 'geometry' ? 'geometry.required' : 'field.required'
				});
			}
			continue;
		}
		errors.push(...fieldErrors(field, form, context));
	}
	errors.push(...radiusErrors(form, context));
	for (const collection of spec.collections) {
		errors.push(...collectionErrors(collection, form, context));
	}

	for (const each of [...form.sites, ...form.series]) {
		if (!each.name.trim()) {
			errors.push({
				id: ids.created(each.key, 'name'),
				step: 'changes',
				code: form.sites.includes(each) ? 'site.name_required' : 'series.name_required'
			});
		}
	}
	for (const each of form.artists) {
		if (!each.name.trim()) {
			errors.push({
				id: ids.created(each.key, 'name'),
				step: 'changes',
				code: 'attribution.artist_name_required'
			});
		}
	}
	for (const source of form.sources) {
		const id = (field: string) => ids.source(source.key, field);
		if (!source.title.trim()) {
			errors.push({ id: id('title'), step: 'sources', code: 'source.title_required' });
		}
		if (source.url.trim() && !URL_PATTERN.test(source.url.trim())) {
			errors.push({ id: id('url'), step: 'sources', code: 'source.url_invalid' });
		}
	}

	if (!creating) {
		const changed =
			Object.keys(form.fields).length > 0 ||
			Object.values(form.links).some((each) => each.added.length + each.removed.length > 0) ||
			form.aliases.added.length + form.aliases.removed.length > 0 ||
			Object.keys(form.attributions.changed).length +
				form.attributions.removed.length +
				form.attributions.added.length >
				0 ||
			form.crew.added.length + form.crew.removed.length > 0 ||
			form.sources.length > 0;
		if (!changed) errors.push({ id: ids.changes, step: 'changes', code: 'edit.empty' });
	}

	if (context.acceptanceRequired && !context.termsAccepted) {
		errors.push({ id: ids.terms, step: 'review', code: 'terms.required' });
	}
	return errors;
}

export function recordStepStates(
	errors: readonly StepError[],
	attempted: boolean,
	steps: readonly string[]
): Record<string, StepState> {
	return stepStates(errors, attempted, steps);
}

/**
 * Where a refusal by the server belongs: its stable code, as `{code}`. The client has
 * already listed everything it can; a code it did not foresee points at the first step of
 * the editor, and otherwise at the Review step.
 */
export function recordServerError(code: string, creating: boolean, kind: Kind): StepError {
	const prefix = code.split('.')[0];
	const first = creating ? (kind === 'area' ? 'identity' : 'identity') : 'changes';
	const special: Record<string, [string, string]> = {
		'moderation.terms_not_accepted': ['review', ids.terms],
		'moderation.empty_changeset': ['changes', ids.changes],
		'area.outside_boundary': ['geometry', ids.field('geometry')],
		'location.outside_boundary': ['changes', ids.field('geometry')],
		'artist.alias_in_use': [creating ? 'identity' : 'changes', ids.collection('aliases')],
		'crew_membership.cycle': [
			creating ? 'activity' : 'changes',
			ids.collection('crew_memberships')
		],
		'crew_membership.not_a_collective': [
			creating ? 'activity' : 'changes',
			ids.collection('crew_memberships')
		],
		'crew_membership.periods_overlap': [
			creating ? 'activity' : 'changes',
			ids.collection('crew_memberships')
		]
	};
	const byPrefix: Record<string, [string, string]> = {
		geometry: [creating ? 'geometry' : 'changes', ids.field('geometry')],
		source: ['sources', 'editor-sources-add'],
		documentation_item: ['changes', ids.changes],
		attribution: ['changes', ids.collection('attributions')],
		uncertain_date: [first, ids.changes],
		period: [creating ? 'activity' : 'changes', ids.field('period')]
	};
	const [step, id] = special[code] ?? byPrefix[prefix] ?? [first, ids.changes];
	return { id, step, code };
}
