/**
 * The state of the editor of a new Artwork: the form, what the person has been told
 * (errors, the autosave status), and the uploads in flight. The steps read and write it;
 * `Editor.svelte` owns the autosave and the submit.
 */
import { untrack } from 'svelte';
import type { Bounds } from '#lib/map/bounds.ts';
import type { View } from '#lib/map/engine.ts';
import type { Locale } from '#lib/paraglide/runtime.js';
import { emptyDate, fromUncertainDate, todayIn } from './date-field';
import {
	emptyForm,
	fromWorkingCopy,
	nextKey,
	placementKey,
	toWorkingCopy,
	type ArtworkForm,
	type Citable,
	type DocForm,
	type Step
} from './form';
import * as api from './api';
import {
	firstIncomplete,
	isBlank,
	stepStates,
	validate,
	type Context,
	type FieldError
} from './validate';

export interface Vocabulary {
	key: string;
	label: Record<string, string>;
	retired: boolean;
}

export interface EditorConfig {
	submissionId: number;
	locale: Locale;
	timeZone: string;
	contentLanguage: string;
	boundary: Bounds;
	view: View;
	attribution: readonly { text: string; url: string }[];
	expressionTypes: Vocabulary[];
	surfaceTypes: Vocabulary[];
	licences: string[];
	terms: { version: number; acceptedVersion: number | null; acceptanceRequired: boolean };
}

export type UploadStatus = 'uploading' | 'processing' | 'ready' | 'rejected' | 'deleted';

export interface UploadView {
	status: UploadStatus;
	/** The code of why a file was refused. */
	error?: string;
	/** Where the camera was, from the file's metadata: a suggestion, never a Location. */
	point?: [number, number];
}

export type SaveStatus =
	| { kind: 'idle' }
	| { kind: 'saving' }
	| { kind: 'saved'; at: Date }
	| { kind: 'failed'; failure: api.Failure };

const POLL_MILLISECONDS = 1000;
const POLL_LIMIT = 120;

export class EditorState {
	readonly config: EditorConfig;
	readonly today: string;
	form: ArtworkForm = $state(emptyForm());
	step: Step = $state('location');
	note = $state('');
	termsAccepted = $state(false);
	/** A submit was tried: step states say "to fix" instead of "to complete". */
	attempted = $state(false);
	/** What the last submit listed, and what the server refused. */
	submitted: FieldError[] = $state([]);
	refused: FieldError[] = $state([]);
	submitting = $state(false);
	uploads: Record<string, UploadView> = $state({});
	save: SaveStatus = $state({ kind: 'idle' });
	/** The draft was reopened with content: a dismissible notice says where it resumed. */
	resumed: Step | null = $state(null);
	candidates: api.LocationCandidate[] = $state([]);
	candidatesFor: string | null = $state(null);
	/** Opening the Location entry again on the form's placement (after the warning acted). */
	entryVersion = $state(0);
	/** What the page's live region says: the duplicate warning, the result of a submit. */
	announcement = $state('');

	constructor(config: EditorConfig, workingCopy: unknown, hadAutosave: boolean) {
		this.config = config;
		this.today = todayIn(config.timeZone);
		this.form = fromWorkingCopy(workingCopy);
		this.termsAccepted = false;
		// Uploads the draft names are fetched again for their state: they were processed meanwhile.
		for (const item of this.form.documentation) if (item.file) void this.refreshUpload(item);
		if (hadAutosave && !isBlank(this.form)) {
			const first = firstIncomplete(this.live);
			this.step = first;
			this.resumed = first;
		}
	}

	/** The state of each upload by Documentation item, as the rules read them. */
	get uploadStatuses(): Context['uploads'] {
		return Object.fromEntries(
			Object.entries(this.uploads).map(([key, each]) => [key, each.status])
		);
	}

	get duplicatesShown(): boolean {
		return this.candidates.length > 0 && this.candidatesFor === placementKey(this.form.location);
	}

	get context(): Context {
		const active = (vocabulary: Vocabulary[]) =>
			// A value computed on demand, not state: nothing observes the set itself.
			// eslint-disable-next-line svelte/prefer-svelte-reactivity
			new Set(vocabulary.filter((each) => !each.retired).map((each) => each.key));
		return {
			today: this.today,
			licences: this.config.licences,
			expressionTypes: active(this.config.expressionTypes),
			surfaceTypes: active(this.config.surfaceTypes),
			acceptanceRequired: this.config.terms.acceptanceRequired,
			termsAccepted: this.termsAccepted,
			uploads: this.uploadStatuses,
			duplicatesShown: this.duplicatesShown
		};
	}

	/** Every rule broken now. Computed on demand, shown only after a submit. */
	live = $derived(validate(this.form, this.context));

	/** The errors of the last submit that still hold, and the server's. */
	shown = $derived([
		...this.submitted.filter((each) =>
			this.live.some((now) => now.id === each.id && now.code === each.code)
		),
		...this.refused
	]);

	states = $derived(stepStates(this.live, this.attempted));

	/** The error of a field, if the last submit listed one. */
	errorAt(id: string): FieldError | undefined {
		return this.shown.find((each) => each.id === id);
	}

	/** The working copy as the API stores it. */
	get workingCopy(): Record<string, unknown> {
		return toWorkingCopy(this.form, this.today);
	}

	/** The Sources and Documentation items that a Claim can cite. */
	citables(
		label: (item: DocForm, index: number) => string,
		sourceLabel: (title: string) => string
	): Citable[] {
		return [
			...this.form.sources.map((each) => ({
				key: each.key,
				kind: 'source' as const,
				label: sourceLabel(each.title)
			})),
			...this.form.documentation.map((each, index) => ({
				key: each.key,
				kind: 'documentation' as const,
				label: label(each, index)
			}))
		];
	}

	announce(text: string): void {
		// The same words twice in a row would not be read again.
		this.announcement = text === untrack(() => this.announcement) ? `${text}\u00a0` : text;
	}

	newKey(prefix: string): string {
		return nextKey(this.form, prefix);
	}

	/** A position the files' metadata suggests, the first there is. */
	get suggestedPoint(): [number, number] | null {
		for (const item of this.form.documentation) {
			const point = this.uploads[item.key]?.point;
			if (point) return point;
		}
		return null;
	}

	// ---- uploads ----

	/** Upload files: each becomes a Documentation item as soon as it is chosen. */
	addFiles(files: Iterable<File>): void {
		for (const file of files) void this.upload(file);
	}

	private async upload(file: File): Promise<void> {
		const key = this.newKey('doc');
		const item: DocForm = {
			key,
			medium: file.type === 'application/pdf' ? 'pdf' : 'image',
			file: null,
			fileName: file.name,
			observed: emptyDate(),
			suggested: false,
			rightsBasis: '',
			creatorCredit: '',
			licence: this.config.licences[0] ?? '',
			originUrl: '',
			altText: '',
			url: ''
		};
		this.form.documentation.push(item);
		this.uploads[key] = { status: 'uploading' };
		const sent = await api.uploadFile(file);
		if (!sent.ok) {
			this.uploads[key] = { status: 'rejected', error: sent.failure.code };
			return;
		}
		const target = this.form.documentation.find((each) => each.key === key);
		if (!target) return;
		target.file = sent.value.id;
		this.uploads[key] = { status: 'processing' };
		await this.poll(target);
	}

	private async refreshUpload(item: DocForm): Promise<void> {
		if (!item.file) return;
		const found = await api.uploadState(item.file);
		if (!found.ok) return;
		this.apply(item, found.value);
		if (found.value.status === 'processing') await this.poll(item);
	}

	private async poll(item: DocForm): Promise<void> {
		for (let attempt = 0; attempt < POLL_LIMIT; attempt++) {
			if (!this.form.documentation.some((each) => each.key === item.key)) return;
			const found = await api.uploadState(item.file ?? '');
			if (found.ok) {
				this.apply(item, found.value);
				if (found.value.status !== 'processing') return;
			}
			await new Promise((resolve) => setTimeout(resolve, POLL_MILLISECONDS));
		}
	}

	private apply(item: DocForm, state: api.UploadState): void {
		const target = this.form.documentation.find((each) => each.key === item.key);
		if (!target) return;
		const view: UploadView = { status: state.status, error: state.error ?? undefined };
		if (state.status === 'ready') {
			if (state.format === 'pdf') target.medium = 'pdf';
			const suggestions = state.suggestions;
			// The capture date is a suggestion for an empty field, and the notice says so.
			if (suggestions?.observed_date && !target.observed.first && !target.observed.unknown) {
				target.observed = fromUncertainDate({
					precision: 'day',
					qualifier: 'exact',
					first: suggestions.observed_date
				});
				target.suggested = true;
			}
			if (suggestions?.point) view.point = [suggestions.point[0], suggestions.point[1]];
		}
		this.uploads[item.key] = view;
	}

	removeDocumentation(key: string): void {
		this.form.documentation = this.form.documentation.filter((each) => each.key !== key);
		delete this.uploads[key];
		// A Claim cannot cite what is gone.
		for (const each of this.form.attributions) {
			each.citations = each.citations.filter((cited) => cited !== key);
		}
		this.form.created.citations = this.form.created.citations.filter((cited) => cited !== key);
	}

	removeSource(key: string): void {
		this.form.sources = this.form.sources.filter((each) => each.key !== key);
		for (const each of this.form.attributions) {
			each.citations = each.citations.filter((cited) => cited !== key);
		}
		this.form.created.citations = this.form.created.citations.filter((cited) => cited !== key);
	}
}
