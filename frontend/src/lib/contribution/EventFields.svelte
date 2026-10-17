<script lang="ts">
	import { conditionWord } from '#lib/archive/records.ts';
	import { m } from '#lib/paraglide/messages.js';
	import ArtworkPicker from './ArtworkPicker.svelte';
	import { errorText } from './errors';
	import Field from './Field.svelte';
	import Group from './Group.svelte';
	import {
		CONDITION_GROUPS,
		EVENT_GROUPS,
		REPORT_GROUPS,
		type Condition,
		type EventType
	} from './form';
	import type { EditorState } from './state.svelte';
	import UncertainDateInput from './UncertainDateInput.svelte';
	import { ids } from './validate';

	/**
	 * The fields of a History event (Contribution and moderation spec, Submission form):
	 * its type, grouped as the spec groups them and each with a line saying what it means;
	 * the Observed date; the Condition a Condition record states; the Artwork that covers
	 * this one; and a note. "Report a condition change" and Add documentation offer the
	 * first three groups only; the last ("Other facts") is reached from an edit.
	 */
	let { editor }: { editor: EditorState } = $props();
	const config = $derived(editor.config);
	const event = $derived(editor.form.event);
	const groups = $derived(
		EVENT_GROUPS.filter(
			(each) =>
				(REPORT_GROUPS as readonly string[]).includes(each.group) ||
				(editor.flavour === 'event' && !event.report)
		)
	);

	const groupWords = {
		observed: m.editor_event_group_observed,
		change: m.editor_event_group_change,
		disappearance: m.editor_event_group_disappearance,
		other: m.editor_event_group_other
	};
	const typeWords: Record<EventType, () => string> = {
		condition_recorded: m.editor_event_type_condition_recorded,
		deteriorated: m.editor_event_type_deteriorated,
		damaged: m.editor_event_type_damaged,
		modified: m.editor_event_type_modified,
		covered: m.editor_event_type_covered,
		removed: m.editor_event_type_removed,
		destroyed: m.editor_event_type_destroyed,
		created: m.editor_event_type_created,
		attribution_changed: m.editor_event_type_attribution_changed
	};
	const descriptionWords: Record<EventType, () => string> = {
		condition_recorded: m.editor_event_desc_condition_recorded,
		deteriorated: m.editor_event_desc_deteriorated,
		damaged: m.editor_event_desc_damaged,
		modified: m.editor_event_desc_modified,
		covered: m.editor_event_desc_covered,
		removed: m.editor_event_desc_removed,
		destroyed: m.editor_event_desc_destroyed,
		created: m.editor_event_desc_created,
		attribution_changed: m.editor_event_desc_attribution_changed
	};
	const conditionGroupWords = {
		present: m.discovery_group_present,
		disappeared: m.discovery_group_disappeared,
		unknown: m.discovery_group_unknown
	};

	function message(id: string) {
		const found = editor.errorAt(id);
		return found ? errorText(found.code, found.params) : null;
	}
</script>

<div class="fields">
	<Group id={ids.eventType} legend={m.editor_event_type()} error={message(ids.eventType)}>
		{#each groups as group, index (group.group)}
			<fieldset class="kind">
				<legend>{groupWords[group.group]()}</legend>
				{#each group.types as type, position (type)}
					<label>
						<input
							id={index === 0 && position === 0 ? ids.eventType : undefined}
							type="radio"
							name="editor-event-type"
							value={type}
							bind:group={event.type}
						/>
						<span>
							{typeWords[type]()}
							<span class="description">{descriptionWords[type]()}</span>
						</span>
					</label>
				{/each}
			</fieldset>
		{/each}
	</Group>

	{#if event.type === 'condition_recorded'}
		<Field
			id={ids.eventCondition}
			label={m.editor_event_condition()}
			error={message(ids.eventCondition)}
		>
			{#snippet children(props)}
				<select {...props} bind:value={event.condition}>
					<option value="">{m.editor_choose()}</option>
					{#each CONDITION_GROUPS as group (group.group)}
						<optgroup label={conditionGroupWords[group.group]()}>
							{#each group.conditions as condition (condition)}
								<option value={condition}
									>{conditionWord(condition as Condition, config.locale)}</option
								>
							{/each}
						</optgroup>
					{/each}
				</select>
			{/snippet}
		</Field>
	{/if}

	<UncertainDateInput
		id={ids.eventObserved}
		legend={m.editor_event_observed()}
		bind:value={event.observed}
		locale={config.locale}
		timeZone={config.timeZone}
		today={editor.today}
		error={message(ids.eventObserved) ??
			message(`${ids.eventObserved}-second`) ??
			message(`${ids.eventObserved}-qualifier`)}
	/>

	{#if event.type === 'covered'}
		<div class="covering">
			{#if event.covering}
				<p id={ids.eventCovering}>
					{m.editor_event_covering_chosen({ title: event.covering.title })}
					<button type="button" onclick={() => (event.covering = null)}>
						{m.editor_event_covering_clear()}
					</button>
				</p>
			{:else}
				<ArtworkPicker
					id={ids.eventCovering}
					label={m.editor_event_covering()}
					onpick={(artwork) => (event.covering = artwork)}
				/>
			{/if}
			<p class="hint">{m.editor_event_covering_hint()}</p>
		</div>
	{/if}

	<Field id="editor-event-note" label={m.editor_event_note()} hint={m.editor_event_note_hint()}>
		{#snippet children(props)}
			<textarea {...props} rows="3" lang={config.contentLanguage} bind:value={event.note}
			></textarea>
		{/snippet}
	</Field>
</div>

<style>
	.fields {
		display: grid;
		gap: 1.25rem;
	}

	.kind {
		display: grid;
		gap: 0.5rem;
		border: 0;
		border-block-start: 1px solid var(--border);
		margin: 0;
		padding: 0.5rem 0 0;
	}

	.kind legend {
		font-weight: 600;
		padding-inline: 0.25rem;
	}

	.description {
		display: block;
		color: var(--text-muted);
	}

	.hint,
	.covering p {
		margin: 0;
	}

	.hint {
		color: var(--text-muted);
	}

	.covering {
		display: grid;
		gap: 0.5rem;
		justify-items: start;
	}

	button {
		min-block-size: 2.75rem;
		padding-inline: 0.75rem;
		background: var(--background);
		color: var(--text);
		border: 1px solid var(--border);
		cursor: pointer;
	}
</style>
