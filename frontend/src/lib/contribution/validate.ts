/**
 * What a new Artwork must satisfy before it is submitted (Contribution and moderation
 * spec, Validation rules): the Archive records model's rules and the Submission model's,
 * run in the browser so that one failed submit lists every error at once, each linked to
 * its field. The server validates again and answers with a stable error code for the
 * first rule broken (ADR 0008); `serverError` places that code in the form.
 *
 * It runs on submit only (acceptance criterion 12), never while the person types.
 */
import { toUncertainDate, isEmptyDate, type DateField } from './date-field';
import {
	ALT_TEXT_MAX,
	MAX_UPLOADED,
	PLACE_DESCRIPTION_MAX,
	placementKey,
	STEPS,
	type ArtworkForm,
	type DocForm,
	type Flavour,
	type Step
} from './form';
import type { StepError, StepState } from './session';

export type { StepState };

export type FieldError = StepError & { step: Step };

export interface Context {
	/** The date of the Submission, ISO, in the Instance time zone. */
	today: string;
	/** The licences of the Instance's allowlist. */
	licences: readonly string[];
	/** Keys of the Expression types and Surface types that are not retired. */
	expressionTypes: ReadonlySet<string>;
	surfaceTypes: ReadonlySet<string>;
	/** Whether the Review step asks for the terms, and whether the box is ticked. */
	acceptanceRequired: boolean;
	termsAccepted: boolean;
	/** The state of each upload by Documentation item key; one that is missing is taken as ready. */
	uploads: Readonly<
		Record<string, 'uploading' | 'processing' | 'ready' | 'rejected' | 'deleted' | undefined>
	>;
	/** The duplicate warning shows candidates for the current placement. */
	duplicatesShown: boolean;
}

export const ids = {
	location: 'editor-location',
	coordinates: 'editor-location-coordinates',
	radius: 'editor-location-radius',
	surfaceType: 'editor-surface-type',
	placeDescription: 'editor-place-description',
	duplicateConfirm: 'editor-duplicate-confirm',
	documentationAdd: 'editor-documentation-add',
	condition: 'editor-condition',
	title: 'editor-title',
	expressionTypes: 'editor-expression-types',
	attributedChoice: 'editor-attributed-known',
	attributionAdd: 'editor-attribution-add',
	creationDate: 'editor-created',
	terms: 'editor-terms',
	eventShows: 'editor-event-shows',
	eventType: 'editor-event-type',
	eventObserved: 'editor-event-observed',
	eventCondition: 'editor-event-condition',
	eventCovering: 'editor-event-covering',
	doc: (key: string, field: string) => `editor-doc-${key}-${field}`,
	attribution: (key: string, field: string) => `editor-attribution-${key}-${field}`,
	source: (key: string, field: string) => `editor-source-${key}-${field}`,
	series: (key: string) => `editor-series-${key}`
};

const URL_PATTERN = /^https?:\/\/\S+$/;

function dateErrors(
	field: DateField,
	idFirst: string,
	step: Step,
	today: string,
	required: boolean,
	requiredCode: string
): FieldError[] {
	const outcome = toUncertainDate(field, today);
	if ('problem' in outcome) {
		const id =
			outcome.field === 'second'
				? `${idFirst}-second`
				: outcome.field === 'qualifier'
					? `${idFirst}-qualifier`
					: idFirst;
		return [{ id, step, code: `date.${outcome.problem}` }];
	}
	if (required && outcome.date === null) return [{ id: idFirst, step, code: requiredCode }];
	return [];
}

function documentErrors(item: DocForm, context: Context): FieldError[] {
	const step: Step = 'documentation';
	const id = (field: string) => ids.doc(item.key, field);
	const errors = dateErrors(
		item.observed,
		id('observed'),
		step,
		context.today,
		true,
		'documentation.observed_required'
	);
	if (item.medium === 'link') {
		if (!item.url.trim()) errors.push({ id: id('url'), step, code: 'documentation.url_required' });
		else if (!URL_PATTERN.test(item.url.trim())) {
			errors.push({ id: id('url'), step, code: 'documentation.url_invalid' });
		}
		return errors;
	}
	const upload = context.uploads[item.key];
	if (upload === 'uploading' || upload === 'processing') {
		errors.push({ id: id('file'), step, code: 'documentation.file_processing' });
	} else if (upload === 'rejected') {
		errors.push({ id: id('file'), step, code: 'documentation.file_rejected' });
	} else if (!item.file || upload === 'deleted') {
		errors.push({ id: id('file'), step, code: 'documentation.file_missing' });
	}
	if (!item.rightsBasis)
		errors.push({ id: id('rights'), step, code: 'documentation.rights_required' });
	if (!item.creatorCredit.trim()) {
		errors.push({ id: id('credit'), step, code: 'documentation.credit_required' });
	}
	if (!item.licence) {
		errors.push({ id: id('licence'), step, code: 'documentation.licence_required' });
	} else if (!context.licences.includes(item.licence)) {
		errors.push({ id: id('licence'), step, code: 'documentation.licence_not_allowed' });
	}
	if (item.rightsBasis === 'third_party') {
		if (!item.originUrl.trim()) {
			errors.push({ id: id('origin'), step, code: 'documentation.origin_required' });
		} else if (!URL_PATTERN.test(item.originUrl.trim())) {
			errors.push({ id: id('origin'), step, code: 'documentation.origin_invalid' });
		}
	}
	if (item.medium === 'image') {
		if (!item.altText.trim())
			errors.push({ id: id('alt'), step, code: 'documentation.alt_required' });
		else if (item.altText.length > ALT_TEXT_MAX) {
			errors.push({
				id: id('alt'),
				step,
				code: 'documentation.alt_too_long',
				params: { max: ALT_TEXT_MAX }
			});
		}
	}
	return errors;
}

/** Every rule broken, in the order of the steps and of the fields in each. */
export function validate(form: ArtworkForm, context: Context): FieldError[] {
	const errors: FieldError[] = [];

	// Location
	const { location } = form;
	const placed = location.existing !== null || location.geometry !== null;
	if (!placed) errors.push({ id: ids.coordinates, step: 'location', code: 'location.required' });
	if (location.radius !== null) {
		if (location.geometry?.type !== 'Point' || !location.approximate || location.existing) {
			errors.push({
				id: ids.radius,
				step: 'location',
				code: 'location.radius_requires_approximate_point'
			});
		}
	}
	if (!location.existing && location.geometry) {
		if (!location.surfaceType) {
			errors.push({
				id: ids.surfaceType,
				step: 'location',
				code: 'location.surface_type_required'
			});
		} else if (!context.surfaceTypes.has(location.surfaceType)) {
			errors.push({ id: ids.surfaceType, step: 'location', code: 'location.surface_type_unknown' });
		}
		if (location.placeDescription.length > PLACE_DESCRIPTION_MAX) {
			errors.push({
				id: ids.placeDescription,
				step: 'location',
				code: 'location.place_description_too_long',
				params: { max: PLACE_DESCRIPTION_MAX }
			});
		} else if (/[\r\n]/.test(location.placeDescription)) {
			errors.push({
				id: ids.placeDescription,
				step: 'location',
				code: 'location.place_description_not_one_line'
			});
		}
	}
	if (placed && context.duplicatesShown && location.confirmedKey !== placementKey(location)) {
		errors.push({
			id: ids.duplicateConfirm,
			step: 'location',
			code: location.existing
				? 'location.different_artwork_unconfirmed'
				: 'location.different_surface_unconfirmed'
		});
	}

	// Documentation
	if (form.documentation.length === 0) {
		errors.push({
			id: ids.documentationAdd,
			step: 'documentation',
			code: 'documentation.required'
		});
	}
	const uploaded = form.documentation.filter((each) => each.medium !== 'link').length;
	if (uploaded > MAX_UPLOADED) {
		errors.push({
			id: ids.documentationAdd,
			step: 'documentation',
			code: 'documentation.too_many_files',
			params: { max: MAX_UPLOADED }
		});
	}
	for (const item of form.documentation) errors.push(...documentErrors(item, context));
	if (!form.initialCondition) {
		errors.push({ id: ids.condition, step: 'documentation', code: 'condition.required' });
	}

	// The Artwork
	if (!form.untitled && !form.title.trim()) {
		errors.push({ id: ids.title, step: 'artwork', code: 'artwork.title_required' });
	}
	if (form.expressionTypes.length === 0) {
		errors.push({
			id: ids.expressionTypes,
			step: 'artwork',
			code: 'artwork.expression_types_required'
		});
	} else if (form.expressionTypes.some((key) => !context.expressionTypes.has(key))) {
		errors.push({
			id: ids.expressionTypes,
			step: 'artwork',
			code: 'artwork.expression_type_unknown'
		});
	}
	for (const series of form.series) {
		if (series.id === null && !series.name.trim()) {
			errors.push({
				id: ids.series(series.key ?? ''),
				step: 'artwork',
				code: 'series.name_required'
			});
		}
	}

	// Attribution
	if (form.attributed === null) {
		errors.push({
			id: ids.attributedChoice,
			step: 'attribution',
			code: 'attribution.choice_required'
		});
	} else if (form.attributed && form.attributions.length === 0) {
		errors.push({ id: ids.attributionAdd, step: 'attribution', code: 'attribution.required' });
	}
	if (form.attributed) {
		const seen = new Set<string>();
		for (const each of form.attributions) {
			const artist = each.artist;
			const id = (field: string) => ids.attribution(each.key, field);
			if (!artist) {
				errors.push({ id: id('artist'), step: 'attribution', code: 'attribution.artist_required' });
			} else if (artist.kind === 'new' && !artist.name.trim()) {
				errors.push({
					id: id('artist'),
					step: 'attribution',
					code: 'attribution.artist_name_required'
				});
			} else {
				const identity = artist.kind === 'existing' ? `artist:${artist.id}` : artist.key;
				if (seen.has(identity)) {
					errors.push({
						id: id('artist'),
						step: 'attribution',
						code: 'attribution.artist_duplicated'
					});
				}
				seen.add(identity);
			}
			if (!each.certainty) {
				errors.push({
					id: id('certainty'),
					step: 'attribution',
					code: 'attribution.certainty_required'
				});
			} else if (each.certainty === 'confirmed' && each.citations.length === 0) {
				errors.push({
					id: id('citations'),
					step: 'attribution',
					code: 'attribution.confirmed_requires_citation'
				});
			}
		}
	}

	// Creation date (optional)
	errors.push(
		...dateErrors(form.created.date, ids.creationDate, 'creation', context.today, false, '')
	);

	// Sources
	for (const source of form.sources) {
		const id = (field: string) => ids.source(source.key, field);
		if (!source.title.trim())
			errors.push({ id: id('title'), step: 'sources', code: 'source.title_required' });
		if (source.url.trim() && !URL_PATTERN.test(source.url.trim())) {
			errors.push({ id: id('url'), step: 'sources', code: 'source.url_invalid' });
		}
	}

	// Review and submit
	if (context.acceptanceRequired && !context.termsAccepted) {
		errors.push({ id: ids.terms, step: 'review', code: 'terms.required' });
	}
	return errors;
}

/**
 * The state of each step, a word and never a colour alone: *complete* with no error,
 * *to fix* once a submit has listed errors in it, *to complete* before that. The Review
 * step is complete when everything before it is.
 */
export function stepStates(
	errors: readonly StepError[],
	attempted: boolean,
	steps: readonly string[] = STEPS
): Record<string, StepState> {
	const states: Record<string, StepState> = {};
	for (const step of steps) {
		const own = errors.filter((each) => each.step === step);
		states[step] = own.length === 0 ? 'complete' : attempted ? 'to_fix' : 'to_complete';
	}
	const others = steps.filter((step) => step !== 'review');
	if (states.review === 'complete' && others.some((step) => states[step] !== 'complete')) {
		states.review = 'to_complete';
	}
	return states;
}

/** The first step that is not complete: where a resumed draft opens. */
export function firstIncomplete(
	errors: readonly StepError[],
	steps: readonly string[] = STEPS
): string {
	return steps.find((step) => errors.some((each) => each.step === step)) ?? 'review';
}

/**
 * What documentation added to an Artwork, or a History event reported on it, must satisfy.
 * The files and the Sources follow the rules of a new Artwork's; the event is asked in the
 * `change` step (add documentation) or the `event` step, with its evidence on the next.
 */
export function validateAttached(
	form: ArtworkForm,
	context: Context,
	flavour: Exclude<Flavour, 'new'>
): FieldError[] {
	const errors: FieldError[] = [];
	const files: Step = flavour === 'event' ? 'evidence' : 'documentation';
	const sources: Step = flavour === 'event' ? 'evidence' : 'sources';
	const { event } = form;

	if (flavour === 'documentation') {
		if (form.documentation.length === 0) {
			errors.push({
				id: ids.documentationAdd,
				step: 'documentation',
				code: 'documentation.required'
			});
		}
		if (event.shows === null) {
			errors.push({ id: ids.eventShows, step: 'change', code: 'event.shows_required' });
		}
	}
	const uploaded = form.documentation.filter((each) => each.medium !== 'link').length;
	if (uploaded > MAX_UPLOADED) {
		errors.push({
			id: ids.documentationAdd,
			step: files,
			code: 'documentation.too_many_files',
			params: { max: MAX_UPLOADED }
		});
	}
	for (const item of form.documentation) {
		errors.push(...documentErrors(item, context).map((each) => ({ ...each, step: files })));
	}

	if (flavour === 'event' || event.shows === true) {
		const step: Step = flavour === 'event' ? 'event' : 'change';
		if (!event.type) errors.push({ id: ids.eventType, step, code: 'event.type_required' });
		errors.push(
			...dateErrors(
				event.observed,
				ids.eventObserved,
				step,
				context.today,
				true,
				'event.observed_required'
			)
		);
		if (event.type === 'condition_recorded' && !event.condition) {
			errors.push({ id: ids.eventCondition, step, code: 'condition.required' });
		}
	}

	for (const source of form.sources) {
		const id = (field: string) => ids.source(source.key, field);
		if (!source.title.trim())
			errors.push({ id: id('title'), step: sources, code: 'source.title_required' });
		if (source.url.trim() && !URL_PATTERN.test(source.url.trim())) {
			errors.push({ id: id('url'), step: sources, code: 'source.url_invalid' });
		}
	}

	if (context.acceptanceRequired && !context.termsAccepted) {
		errors.push({ id: ids.terms, step: 'review', code: 'terms.required' });
	}
	return errors;
}

/** Whether nothing the person entered is in the form of an Artwork that exists. */
export function isBlankAttached(form: ArtworkForm): boolean {
	return (
		form.documentation.length === 0 &&
		form.sources.length === 0 &&
		form.event.shows === null &&
		form.event.type === '' &&
		isEmptyDate(form.event.observed) &&
		form.event.note === ''
	);
}

/** Whether nothing the person entered is in the form: a draft just started. */
export function isBlank(form: ArtworkForm): boolean {
	return (
		form.location.existing === null &&
		form.location.geometry === null &&
		form.documentation.length === 0 &&
		form.initialCondition === '' &&
		form.title === '' &&
		!form.untitled &&
		form.expressionTypes.length === 0 &&
		form.description === '' &&
		form.series.length === 0 &&
		form.attributed === null &&
		form.attributions.length === 0 &&
		isEmptyDate(form.created.date) &&
		form.sources.length === 0
	);
}

/**
 * Where a refusal by the server belongs: its stable code, as `{code}`. The client has
 * already listed everything it can; a code it did not foresee points at the step that
 * owns its record kind, and otherwise at the Review step.
 */
export function serverError(code: string, flavour: Flavour = 'new'): FieldError {
	if (flavour !== 'new') return attachedServerError(code, flavour);
	const prefix = code.split('.')[0];
	const byPrefix: Record<string, [Step, string]> = {
		location: ['location', ids.coordinates],
		geometry: ['location', ids.coordinates],
		documentation_item: ['documentation', ids.documentationAdd],
		artwork: ['artwork', ids.title],
		attribution: ['attribution', ids.attributedChoice],
		history_event: ['creation', ids.creationDate],
		source: ['sources', 'editor-sources-add'],
		series: ['artwork', ids.title],
		artist: ['attribution', ids.attributedChoice],
		uncertain_date: ['documentation', ids.documentationAdd]
	};
	const special: Record<string, [Step, string]> = {
		'moderation.documentation_required': ['documentation', ids.documentationAdd],
		'moderation.initial_condition_required': ['documentation', ids.condition],
		'moderation.too_many_files': ['documentation', ids.documentationAdd],
		'moderation.terms_not_accepted': ['review', ids.terms]
	};
	const [step, id] = special[code] ?? byPrefix[prefix] ?? ['review', 'editor-submit'];
	return { id, step, code };
}

/** The same for the two editors of an Artwork that exists. */
function attachedServerError(code: string, flavour: Exclude<Flavour, 'new'>): FieldError {
	const event: Step = flavour === 'event' ? 'event' : 'change';
	const files: Step = flavour === 'event' ? 'evidence' : 'documentation';
	const sources: Step = flavour === 'event' ? 'evidence' : 'sources';
	const byPrefix: Record<string, [Step, string]> = {
		documentation_item: [files, ids.documentationAdd],
		history_event: [event, ids.eventType],
		source: [sources, 'editor-sources-add'],
		uncertain_date: [event, ids.eventObserved]
	};
	const special: Record<string, [Step, string]> = {
		'moderation.empty_changeset': [files, ids.documentationAdd],
		'moderation.too_many_files': [files, ids.documentationAdd],
		'moderation.terms_not_accepted': ['review', ids.terms]
	};
	const [step, id] = special[code] ?? byPrefix[code.split('.')[0]] ?? ['review', 'editor-submit'];
	return { id, step, code };
}
