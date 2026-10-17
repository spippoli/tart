<script lang="ts">
	import { m } from '#lib/paraglide/messages.js';
	import { errorText } from './errors';
	import EventFields from './EventFields.svelte';
	import Group from './Group.svelte';
	import type { EditorState } from './state.svelte';
	import { ids } from './validate';

	/**
	 * "Does it show a change?" of Add documentation (Contribution and moderation spec, Form
	 * structure): the new files may report a change in the Artwork, which adds a History
	 * event citing them. The question is asked, never assumed.
	 */
	let { editor }: { editor: EditorState } = $props();
	const event = $derived(editor.form.event);
	const target = $derived(editor.form.target);
	const found = $derived(editor.errorAt(ids.eventShows));
</script>

<div class="step">
	<p>{m.editor_change_intro({ title: target?.title ?? '' })}</p>

	<Group
		id={ids.eventShows}
		legend={m.editor_change_legend()}
		error={found ? errorText(found.code, found.params) : null}
		radiogroup
	>
		<label>
			<input
				id={ids.eventShows}
				type="radio"
				name="editor-event-shows"
				value={false}
				bind:group={event.shows}
			/>
			{m.editor_change_no()}
		</label>
		<label>
			<input type="radio" name="editor-event-shows" value={true} bind:group={event.shows} />
			{m.editor_change_yes()}
		</label>
	</Group>

	{#if event.shows}
		<p class="hint">{m.editor_change_cites()}</p>
		<EventFields {editor} />
	{/if}
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

	.hint {
		color: var(--text-muted);
	}
</style>
