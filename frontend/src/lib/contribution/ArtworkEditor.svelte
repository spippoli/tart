<script lang="ts">
	import { untrack } from 'svelte';
	import * as api from './api';
	import ArtworkStep from './ArtworkStep.svelte';
	import AttachedPreview from './AttachedPreview.svelte';
	import AttributionStep from './AttributionStep.svelte';
	import ChangeStep from './ChangeStep.svelte';
	import CreationStep from './CreationStep.svelte';
	import DocumentationStep from './DocumentationStep.svelte';
	import Editor from './Editor.svelte';
	import EventStep from './EventStep.svelte';
	import EvidenceStep from './EvidenceStep.svelte';
	import { placementKey } from './form';
	import LocationStep from './LocationStep.svelte';
	import Preview from './Preview.svelte';
	import ReviewStep from './ReviewStep.svelte';
	import SourcesStep from './SourcesStep.svelte';
	import { EditorState, type EditorConfig } from './state.svelte';

	/**
	 * The editor of an Artwork (Contribution and moderation spec, Submission form): a new
	 * Artwork, or documentation or a History event added to one that exists. The shell is
	 * `Editor`; this holds the state and says which component draws each step.
	 */
	let {
		config,
		workingCopy,
		lastAutosave
	}: {
		config: EditorConfig;
		workingCopy: unknown;
		/** When the draft was last saved by its Submitter, if it ever was. */
		lastAutosave: string | null;
	} = $props();

	// The editor is made once, from what the page loaded; a draft does not change under it.
	// svelte-ignore state_referenced_locally
	const editor = new EditorState(config, workingCopy, lastAutosave !== null);

	// ---- the duplicate warning: candidates for the placement, wherever the person is ----

	let token = 0;
	$effect(() => {
		if (editor.flavour !== 'new') return;
		const location = editor.form.location;
		const key = placementKey(location);
		const place = location.existing
			? { locationId: location.existing.id }
			: location.geometry
				? { geometry: location.geometry, radius: location.radius }
				: null;
		untrack(() => {
			if (!place || !key) {
				editor.candidates = [];
				editor.candidatesFor = null;
				return;
			}
			if (editor.candidatesFor === key) return;
			const mine = ++token;
			void api.locationCandidates(place).then((out) => {
				if (mine !== token) return;
				editor.candidates = out.ok ? out.value.candidates : [];
				editor.candidatesFor = key;
			});
		});
	});
</script>

{#snippet panel(step: string, submit: () => void)}
	{#if step === 'location'}
		<LocationStep {editor} />
	{:else if step === 'documentation'}
		<DocumentationStep {editor} />
	{:else if step === 'artwork'}
		<ArtworkStep {editor} />
	{:else if step === 'attribution'}
		<AttributionStep {editor} />
	{:else if step === 'creation'}
		<CreationStep {editor} />
	{:else if step === 'sources'}
		<SourcesStep {editor} />
	{:else if step === 'change'}
		<ChangeStep {editor} />
	{:else if step === 'event'}
		<EventStep {editor} />
	{:else if step === 'evidence'}
		<EvidenceStep {editor} />
	{:else}
		<ReviewStep {editor} onsubmit={submit}>
			{#if editor.flavour === 'new'}
				<Preview {editor} />
			{:else}
				<AttachedPreview {editor} />
			{/if}
		</ReviewStep>
	{/if}
{/snippet}

<Editor {editor} {lastAutosave} {panel} />
