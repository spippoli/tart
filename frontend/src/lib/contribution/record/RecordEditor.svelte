<script lang="ts">
	import { m } from '#lib/paraglide/messages.js';
	import Editor from '../Editor.svelte';
	import ReviewStep from '../ReviewStep.svelte';
	import SourcesStep from '../SourcesStep.svelte';
	import FieldsStep from './FieldsStep.svelte';
	import RecordPreview from './RecordPreview.svelte';
	import { RecordEditorState, type RecordEditorConfig } from './state.svelte';

	/**
	 * The editor of a record that exists, and of a new Area or Artist (Contribution and
	 * moderation spec, Other editors). The shell is `Editor`; this holds the state and says
	 * which component draws each step: the fields (What changes, or the steps of a new
	 * record), the Sources the Submission creates, and Review and submit.
	 */
	let {
		config,
		workingCopy,
		lastAutosave
	}: {
		config: RecordEditorConfig;
		workingCopy: unknown;
		/** When the draft was last saved by its Submitter, if it ever was. */
		lastAutosave: string | null;
	} = $props();

	// The editor is made once, from what the page loaded; a draft does not change under it.
	// svelte-ignore state_referenced_locally
	const editor = new RecordEditorState(config, workingCopy, lastAutosave !== null);
</script>

{#snippet panel(step: string, submit: () => void)}
	{#if step === 'review'}
		<ReviewStep {editor} onsubmit={submit}>
			<RecordPreview {editor} />
		</ReviewStep>
	{:else if step === 'sources'}
		<SourcesStep
			{editor}
			intro={editor.creating ? m.editor_sources_intro_record() : m.editor_sources_intro_edit()}
		/>
	{:else}
		<FieldsStep {editor} {step} />
	{/if}
{/snippet}

<Editor {editor} {lastAutosave} {panel} />
