<script lang="ts">
	import { formatPeriod, type Period } from '#lib/archive/uncertain-date.ts';
	import { m } from '#lib/paraglide/messages.js';
	import { errorText } from '../errors';
	import Group from '../Group.svelte';
	import RecordPicker from '../RecordPicker.svelte';
	import UncertainDateInput from '../UncertainDateInput.svelte';
	import { emptyPeriod } from './form';
	import type { RecordEditorState } from './state.svelte';
	import { ids } from './validate';

	/**
	 * The Crew memberships of an Artist (Contribution and moderation spec, Other editors):
	 * each belongs to the member, so a collective's own edit lists its members read-only and
	 * says that a member joins through its own edit. A membership is added or removed whole;
	 * to change its period, remove it and add it again. A membership that would form a cycle,
	 * or one in an Artist who is not a collective, is refused by the archive with its own code.
	 */
	let { editor }: { editor: RecordEditorState } = $props();
	const crew = $derived(editor.form.crew);
	const present = $derived(
		(Array.isArray(editor.config.current.crew_memberships)
			? editor.config.current.crew_memberships
			: []) as { collective: number; period: Period | null }[]
	);
	const dates = $derived({ locale: editor.config.locale, timeZone: editor.config.timeZone });
	const found = $derived(editor.errorAt(ids.collection('crew_memberships')));

	function periodWords(period: Period | null): string {
		return (period && formatPeriod(period, dates)) || m.editor_value_none();
	}

	function toggle(index: number, on: boolean) {
		crew.removed = on ? [...crew.removed, index] : crew.removed.filter((each) => each !== index);
	}

	function add(collective: { id: number; name: string }) {
		crew.added.push({ key: editor.newKey('crew'), collective, period: emptyPeriod() });
	}

	function message(id: string) {
		const at = editor.errorAt(id);
		return at ? errorText(at.code, at.params) : null;
	}

	const related = $derived(editor.config.related);
</script>

<section class="crew" id={ids.collection('crew_memberships')} tabindex="-1">
	<h3>{m.editor_collection_crew()}</h3>
	<p class="hint">{m.editor_crew_hint()}</p>

	{#if present.length > 0}
		<ul>
			{#each present as membership, index (index)}
				{@const removed = crew.removed.includes(index)}
				{@const name = editor.name(membership.collective)}
				<li>
					<span class:removed>{name} · {periodWords(membership.period)}</span>
					{#if removed}
						<span class="state">{m.editor_item_removed()}</span>
						<button type="button" onclick={() => toggle(index, false)}>
							{m.editor_item_keep({ name })}
						</button>
					{:else}
						<button type="button" onclick={() => toggle(index, true)}>
							{m.editor_item_remove({ name })}
						</button>
					{/if}
				</li>
			{/each}
		</ul>
	{:else if crew.added.length === 0}
		<p>{m.editor_value_none()}</p>
	{/if}

	{#each crew.added as each (each.key)}
		<div class="proposal">
			<p><strong>{m.editor_proposed_label()}</strong> · {each.collective?.name}</p>
			<Group
				id={ids.crew(each.key)}
				legend={m.editor_crew_period()}
				error={message(ids.crew(each.key))}
			>
				<UncertainDateInput
					id="{ids.crew(each.key)}-start"
					legend={m.editor_period_start()}
					bind:value={each.period.start}
					locale={editor.config.locale}
					timeZone={editor.config.timeZone}
					today={editor.today}
					optional
					error={message(`${ids.crew(each.key)}-start`)}
				/>
				<UncertainDateInput
					id="{ids.crew(each.key)}-end"
					legend={m.editor_period_end()}
					bind:value={each.period.end}
					locale={editor.config.locale}
					timeZone={editor.config.timeZone}
					today={editor.today}
					optional
					error={message(`${ids.crew(each.key)}-end`)}
				/>
			</Group>
			<button
				type="button"
				onclick={() => (crew.added = crew.added.filter((other) => other !== each))}
			>
				{m.editor_item_undo_add({ name: each.collective?.name ?? '' })}
			</button>
		</div>
	{/each}

	<RecordPicker
		{editor}
		kind="artist"
		id={ids.add('crew_memberships')}
		label={m.editor_crew_add()}
		onpick={add}
	/>

	{#if related?.kind === 'members'}
		<div class="members">
			<h4>{m.editor_crew_members()}</h4>
			<p class="hint">{m.editor_crew_members_hint()}</p>
			{#if related.items.length === 0}
				<p>{m.editor_value_none()}</p>
			{:else}
				<ul>
					{#each related.items as member (member.href)}
						<li><a href={member.href}>{member.name}</a></li>
					{/each}
				</ul>
			{/if}
		</div>
	{/if}

	{#if found}
		<p class="error">
			<strong>{m.editor_error_prefix()}</strong>
			{errorText(found.code, found.params)}
		</p>
	{/if}
</section>

<style>
	.crew {
		display: grid;
		gap: 0.75rem;
		justify-items: start;
		border-block-start: 1px solid var(--border);
		padding-block: 1rem 0.5rem;
	}

	h3,
	h4,
	p {
		margin: 0;
	}

	.hint {
		color: var(--text-muted);
	}

	ul {
		margin: 0;
		padding-inline-start: 1.25rem;
		display: grid;
		gap: 0.5rem;
	}

	.removed {
		text-decoration: line-through;
	}

	.state {
		font-variant-caps: all-small-caps;
		letter-spacing: 0.04em;
		margin-inline: 0.5rem;
	}

	.proposal {
		display: grid;
		gap: 0.75rem;
		inline-size: 100%;
		border: 3px dashed var(--text);
		padding: 0.75rem;
	}

	.members {
		display: grid;
		gap: 0.35rem;
	}

	.error {
		border-inline-start: 4px solid var(--accent, currentColor);
		padding-inline-start: 0.5rem;
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
