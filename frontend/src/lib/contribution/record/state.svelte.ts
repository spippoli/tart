/**
 * The state of the editor of an existing record, or of a new Area or Artist: the form, what
 * the person has been told (errors, the autosave status), and the record it starts from.
 * The steps read and write it; `Editor.svelte` owns the autosave and the submit.
 */
import { untrack } from 'svelte';
import type { Kind, RecordLink } from '#lib/archive/records.ts';
import type { Bounds } from '#lib/map/bounds.ts';
import type { View } from '#lib/map/engine.ts';
import { m } from '#lib/paraglide/messages.js';
import type { Locale } from '#lib/paraglide/runtime.js';
import { todayIn } from '../date-field';
import type { SaveStatus, Session, SourcesHost, StepError, TermsState } from '../session';
import type { Vocabulary } from '../state.svelte';
import { firstIncomplete } from '../validate';
import {
	emptyRecordForm,
	fromWorkingCopy,
	initialValue,
	isBlankRecord,
	nextRecordKey,
	toWorkingCopy,
	type Json,
	type RecordForm
} from './form';
import { editSteps, SPECS } from './spec';
import {
	recordServerError,
	recordStepStates,
	validateRecord,
	type RecordContext
} from './validate';

export interface RecordEditorConfig {
	submissionId: number;
	locale: Locale;
	timeZone: string;
	contentLanguage: string;
	terms: TermsState;
	kind: Kind;
	/** A new Area or Artist; otherwise an edit of `targetId`. */
	creating: boolean;
	targetId: number | null;
	/** The record as stored, in the changeset's JSON; empty for a new record. */
	current: { [key: string]: Json };
	/** The words of the records it links to, by id. */
	links: Record<string, RecordLink>;
	redactedFields: string[];
	/** For a Location: how many Artworks it carries. */
	artworkCount: number | null;
	/**
	 * What holds a membership in the record and is only listed here: the Locations of a Site,
	 * the Artworks of a Series, the members of a collective. They join through their own edits.
	 */
	related: {
		kind: 'locations' | 'artworks' | 'members';
		items: { name: string; href: string }[];
	} | null;
	surfaceTypes: Vocabulary[];
	expressionTypes: Vocabulary[];
	licences: string[];
	boundary: Bounds;
	view: View;
	attribution: readonly { text: string; url: string }[];
}

const STEP_NAMES = {
	changes: m.editor_step_changes,
	identity: m.editor_step_identity,
	geometry: m.editor_step_polygon,
	activity: m.editor_step_activity,
	review: m.editor_step_review
};

export class RecordEditorState implements Session, SourcesHost {
	readonly config: RecordEditorConfig;
	readonly today: string;
	form: RecordForm = $state(emptyRecordForm());
	step: string = $state('');
	note = $state('');
	termsAccepted = $state(false);
	attempted = $state(false);
	submitted: StepError[] = $state([]);
	refused: StepError[] = $state([]);
	submitting = $state(false);
	save: SaveStatus = $state({ kind: 'idle' });
	resumed: string | null = $state(null);
	announcement = $state('');

	constructor(config: RecordEditorConfig, workingCopy: unknown, hadAutosave: boolean) {
		this.config = config;
		this.today = todayIn(config.timeZone);
		this.step = this.steps[0];
		this.form = fromWorkingCopy(workingCopy);
		// Every collection of links starts with nothing added or removed, so the steps only read.
		for (const collection of SPECS[config.kind].collections) {
			if (collection.type === 'links') {
				this.form.links[collection.name] ??= { added: [], removed: [] };
			}
		}
		if (config.creating) {
			// A new record asks every field of its kind: each starts empty.
			for (const field of SPECS[config.kind].fields) {
				this.form.fields[field.name] ??= initialValue(field);
			}
		}
		if (hadAutosave && !this.blank) {
			const first = firstIncomplete(this.live, this.steps);
			this.step = first;
			this.resumed = first;
		}
	}

	get creating(): boolean {
		return this.config.creating;
	}

	get steps(): readonly string[] {
		return this.config.creating
			? (SPECS[this.config.kind].create ?? [])
			: editSteps(this.config.kind);
	}

	/** Whether nothing the person entered is in the form: a draft just started. */
	get blank(): boolean {
		if (!this.creating) return isBlankRecord(this.form);
		const untouched = Object.fromEntries(
			SPECS[this.kind].fields.map((field) => [field.name, initialValue(field)])
		);
		return (
			JSON.stringify(this.form.fields) === JSON.stringify(untouched) &&
			isBlankRecord({ ...this.form, fields: {} })
		);
	}

	get kind(): Kind {
		return this.config.kind;
	}

	stepName(step: string): string {
		if (step === 'sources') {
			return this.creating ? m.editor_step_sources() : m.editor_step_supporting_sources();
		}
		if (step === 'identity') {
			return this.kind === 'area' ? m.editor_step_area_identity() : m.editor_step_identity();
		}
		return (STEP_NAMES[step as keyof typeof STEP_NAMES] ?? (() => step))();
	}

	get context(): RecordContext {
		const active = (vocabulary: Vocabulary[]) =>
			// A value computed on demand, not state: nothing observes the set itself.
			// eslint-disable-next-line svelte/prefer-svelte-reactivity
			new Set(vocabulary.filter((each) => !each.retired).map((each) => each.key));
		return {
			kind: this.kind,
			current: this.config.current,
			creating: this.creating,
			today: this.today,
			surfaceTypes: active(this.config.surfaceTypes),
			expressionTypes: active(this.config.expressionTypes),
			acceptanceRequired: this.config.terms.acceptanceRequired,
			termsAccepted: this.termsAccepted
		};
	}

	/** Every rule broken now. Computed on demand, shown only after a submit. */
	live: StepError[] = $derived(validateRecord(this.form, this.context));

	/** The errors of the last submit that still hold, and the server's. */
	shown: StepError[] = $derived([
		...this.submitted.filter((each) =>
			this.live.some((now) => now.id === each.id && now.code === each.code)
		),
		...this.refused
	]);

	states = $derived(recordStepStates(this.live, this.attempted, this.steps));

	errorAt(id: string): StepError | undefined {
		return this.shown.find((each) => each.id === id);
	}

	serverError(code: string): StepError {
		return recordServerError(code, this.creating, this.kind);
	}

	get workingCopy(): Record<string, unknown> {
		return toWorkingCopy(
			{ kind: this.kind, id: this.config.targetId },
			this.form,
			this.today,
			this.config.current
		);
	}

	announce(text: string): void {
		// The same words twice in a row would not be read again.
		this.announcement = text === untrack(() => this.announcement) ? `${text}\u00a0` : text;
	}

	newKey(prefix: string): string {
		return nextRecordKey(this.form, prefix);
	}

	/** The name of a record the current one links to. */
	name(id: number): string {
		const link = this.config.links[String(id)];
		if (!link) return m.archive_location_fallback({ id: String(id) });
		return link.name ?? (link.location_title?.place_description || m.archive_untitled());
	}

	/** Whether a field of the record is hidden from the person by a Redaction. */
	redacted(field: string): boolean {
		return this.config.redactedFields.includes(field);
	}

	// ---- Sources of the Submission ----

	removeSource(key: string): void {
		this.form.sources = this.form.sources.filter((each) => each.key !== key);
		for (const each of [...this.form.sites, ...this.form.series]) {
			each.sources = each.sources.filter((cited) => cited !== key);
		}
		const drop = (cited: { key: string | null }) => cited.key !== key;
		for (const each of [
			...Object.values(this.form.attributions.changed),
			...this.form.attributions.added
		]) {
			each.citations = each.citations.filter(drop);
		}
	}
}
