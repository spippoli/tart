<script lang="ts">
	import { m } from '#lib/paraglide/messages.js';
	import * as api from './api';
	import type { Session } from './session';

	/**
	 * A link picker for an Artist or a Series: search the public records by name, use one,
	 * or create a new one named by the person. Creating checks the name against the
	 * archive's (Contribution and moderation spec, Duplicate detection, the name rule):
	 * if records are alike it says so and offers each, and never blocks.
	 */
	let {
		editor,
		kind,
		id,
		label,
		onpick,
		oncreate
	}: {
		editor: Pick<Session, 'announce'>;
		kind: 'artist' | 'series' | 'site' | 'area';
		id: string;
		label: string;
		onpick: (record: { id: number; name: string }) => void;
		/** Absent: only records that exist can be picked (an Area of activity). */
		oncreate?: (name: string) => void;
	} = $props();

	const SEARCH = { artist: 'artists', series: 'series', site: 'sites', area: 'areas' } as const;
	const CREATE = {
		artist: m.editor_picker_create_artist,
		series: m.editor_picker_create_series,
		site: m.editor_picker_create_site,
		area: m.editor_picker_create_series
	} as const;

	let query = $state('');
	let results = $state<api.RecordLink[] | null>(null);
	let alike = $state<api.NameCandidate[] | null>(null);
	let failed = $state(false);

	async function search() {
		const name = query.trim();
		if (!name) return;
		alike = null;
		const found = await api.searchRecords(SEARCH[kind], name);
		failed = !found.ok;
		results = found.ok ? found.value.items : null;
	}

	async function create() {
		const name = query.trim();
		if (!name) return;
		results = null;
		const found = await api.nameCandidates(kind, name);
		if (found.ok && found.value.candidates.length > 0) {
			alike = found.value.candidates;
			editor.announce(m.editor_alike_announcement({ count: alike.length, name }));
			return;
		}
		finish(name);
	}

	function finish(name: string) {
		alike = null;
		query = '';
		oncreate?.(name);
	}

	function use(record: { id: number; name: string }) {
		alike = null;
		results = null;
		query = '';
		onpick(record);
	}
</script>

<div class="picker">
	<label for={id}>{label}</label>
	<div class="row">
		<input
			{id}
			type="search"
			autocomplete="off"
			bind:value={query}
			onkeydown={(event) => {
				if (event.key === 'Enter') {
					event.preventDefault();
					search();
				}
			}}
		/>
		<button type="button" onclick={search}>{m.editor_picker_search()}</button>
		{#if oncreate}
			<button type="button" onclick={create} disabled={!query.trim()}>
				{CREATE[kind]()}
			</button>
		{/if}
	</div>

	{#if failed}
		<p>{m.editor_picker_failed()}</p>
	{:else if results}
		{#if results.length === 0}
			<p>{m.editor_picker_none()}</p>
		{:else}
			<ul aria-label={m.editor_picker_results()}>
				{#each results as record (record.id)}
					<li>
						{record.name}
						<button type="button" onclick={() => use({ id: record.id, name: record.name ?? '' })}>
							{m.editor_picker_use({ name: record.name ?? '' })}
						</button>
					</li>
				{/each}
			</ul>
		{/if}
	{/if}

	{#if alike}
		<section class="alike" aria-label={m.editor_alike_title()}>
			<h4>{m.editor_alike_title()}</h4>
			<p>{m.editor_alike_intro()}</p>
			<ul>
				{#each alike as candidate (candidate.record.id)}
					<li>
						{m.editor_alike_candidate({
							name: candidate.record.name ?? '',
							matched: candidate.matched
						})}
						<button
							type="button"
							onclick={() => use({ id: candidate.record.id, name: candidate.record.name ?? '' })}
						>
							{m.editor_picker_use({ name: candidate.record.name ?? '' })}
						</button>
					</li>
				{/each}
			</ul>
			<button type="button" onclick={() => finish(query.trim())}>{m.editor_alike_continue()}</button
			>
		</section>
	{/if}
</div>

<style>
	.picker {
		display: grid;
		gap: 0.5rem;
		justify-items: start;
	}

	label {
		font-weight: 600;
	}

	.row {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
	}

	ul {
		margin: 0;
		padding-inline-start: 1.25rem;
		display: grid;
		gap: 0.5rem;
	}

	p,
	h4 {
		margin: 0;
	}

	.alike {
		display: grid;
		gap: 0.5rem;
		border: 1px solid var(--border);
		padding: 0.75rem;
	}

	input,
	button {
		min-block-size: 2.75rem;
		padding-inline: 0.75rem;
		background: var(--background);
		color: var(--text);
		border: 1px solid var(--border);
	}

	button {
		cursor: pointer;
	}

	button:disabled {
		cursor: default;
		opacity: 0.6;
	}
</style>
