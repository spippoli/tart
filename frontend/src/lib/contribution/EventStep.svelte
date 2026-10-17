<script lang="ts">
	import { m } from '#lib/paraglide/messages.js';
	import EventFields from './EventFields.svelte';
	import type { EditorState } from './state.svelte';

	/**
	 * The first step of a History event (Contribution and moderation spec, Form structure):
	 * what happened to the Artwork and when it was observed, a disappearance included. The
	 * evidence for it is the next step.
	 */
	let { editor }: { editor: EditorState } = $props();
	const target = $derived(editor.form.target);
</script>

<div class="step">
	<p>{m.editor_event_intro({ title: target?.title ?? '' })}</p>
	<EventFields {editor} />
</div>

<style>
	.step {
		display: grid;
		gap: 1.25rem;
	}

	.step > p {
		margin: 0;
		max-inline-size: var(--measure);
	}
</style>
