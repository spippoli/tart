/**
 * What the editor shell needs of an editor's state, whatever the Submission is: the steps
 * and their words, the errors a submit listed, the autosave status, and the working copy to
 * save. `Editor.svelte` is the shell (stepper, autosave, summary, leaving); the state of an
 * Artwork (`EditorState`) and of any other record (`RecordEditorState`) are its two bodies.
 */
import type { Locale } from '#lib/paraglide/runtime.js';
import type * as api from './api';
import type { SourceForm } from './form';

export interface StepError {
	/** The DOM id of the field the error is about, which also names its message. */
	id: string;
	step: string;
	code: string;
	params?: Record<string, string | number>;
}

export type StepState = 'complete' | 'to_complete' | 'to_fix';

export type SaveStatus =
	| { kind: 'idle' }
	| { kind: 'saving' }
	| { kind: 'saved'; at: Date }
	| { kind: 'failed'; failure: api.Failure };

export interface TermsState {
	version: number;
	acceptedVersion: number | null;
	acceptanceRequired: boolean;
}

export interface Session {
	readonly config: {
		submissionId: number;
		locale: Locale;
		timeZone: string;
		contentLanguage: string;
		terms: TermsState;
	};
	readonly steps: readonly string[];
	/** The step's name in the UI language. */
	stepName(step: string): string;
	step: string;
	note: string;
	termsAccepted: boolean;
	/** A submit was tried: step states say "to fix" instead of "to complete". */
	attempted: boolean;
	/** What the last submit listed, and what the server refused. */
	submitted: StepError[];
	refused: StepError[];
	submitting: boolean;
	save: SaveStatus;
	/** The draft was reopened with content: a dismissible notice says where it resumed. */
	resumed: string | null;
	/** What the page's live region says. */
	announcement: string;
	/** Every rule broken now. */
	readonly live: StepError[];
	/** The errors of the last submit that still hold, and the server's. */
	readonly shown: StepError[];
	readonly states: Record<string, StepState>;
	/** The working copy as the API stores it. */
	readonly workingCopy: Record<string, unknown>;
	announce(text: string): void;
	errorAt(id: string): StepError | undefined;
	/** Where a refusal by the server belongs. */
	serverError(code: string): StepError;
}

/** What the Sources step needs: the editors that cite Sources created with the Submission. */
export interface SourcesHost {
	readonly config: { contentLanguage: string; locale: Locale };
	readonly form: { sources: SourceForm[] };
	newKey(prefix: string): string;
	errorAt(id: string): StepError | undefined;
	announce(text: string): void;
	/** Drops a Source of the Submission, and every citation of it. */
	removeSource(key: string): void;
}
