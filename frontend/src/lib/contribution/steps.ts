/** The names of the steps of the Artwork editor, in the UI language. */
import { m } from '#lib/paraglide/messages.js';
import type { Step } from './form';

export const stepNames: Record<Step, () => string> = {
	location: m.editor_step_location,
	documentation: m.editor_step_documentation,
	artwork: m.editor_step_artwork,
	attribution: m.editor_step_attribution,
	creation: m.editor_step_creation,
	sources: m.editor_step_sources,
	change: m.editor_step_change,
	event: m.editor_step_event,
	evidence: m.editor_step_evidence,
	review: m.editor_step_review
};

/** The three words a step state is shown with. */
export const stateWords = {
	complete: m.editor_state_complete,
	to_complete: m.editor_state_to_complete,
	to_fix: m.editor_state_to_fix
};
