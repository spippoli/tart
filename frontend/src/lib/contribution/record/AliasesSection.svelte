<script lang="ts">
	import { m } from '#lib/paraglide/messages.js';
	import { errorText } from '../errors';
	import type { RecordEditorState } from './state.svelte';
	import { ids } from './validate';

	/**
	 * The Aliases of an Artist (Contribution and moderation spec, Other editors): each is
	 * an item, added or removed on its own. An Alias that an Attribution names cannot be
	 * removed until that Attribution is changed by an edit of the Artwork; the archive
	 * refuses it with its own code, which the summary words. Aliases are public names only
	 * (ADR 0014).
	 */
	let { editor }: { editor: RecordEditorState } = $props();
	const aliases = $derived(editor.form.aliases);
	const present = $derived(
		(Array.isArray(editor.config.current.aliases) ? editor.config.current.aliases : []).filter(
			(each): each is string => typeof each === 'string'
		)
	);
	const found = $derived(editor.errorAt(ids.collection('aliases')));
	let draft = $state('');

	function add() {
		const alias = draft.trim();
		if (!alias || present.includes(alias) || aliases.added.includes(alias)) return;
		aliases.added.push(alias);
		draft = '';
	}

	function remove(alias: string, on: boolean) {
		aliases.removed = on
			? [...aliases.removed, alias]
			: aliases.removed.filter((each) => each !== alias);
	}
</script>

<section class="aliases" id={ids.collection('aliases')} tabindex="-1">
	<h3>{m.editor_collection_aliases()}</h3>
	<p class="hint">{m.editor_artist_public_name()}</p>

	{#if present.length > 0}
		<ul>
			{#each present as alias (alias)}
				{@const removed = aliases.removed.includes(alias)}
				<li>
					<span class:removed lang={editor.config.contentLanguage}>{alias}</span>
					{#if removed}
						<span class="state">{m.editor_item_removed()}</span>
						<button type="button" onclick={() => remove(alias, false)}>
							{m.editor_item_keep({ name: alias })}
						</button>
					{:else}
						<button type="button" onclick={() => remove(alias, true)}>
							{m.editor_item_remove({ name: alias })}
						</button>
					{/if}
				</li>
			{/each}
		</ul>
	{:else if aliases.added.length === 0}
		<p>{m.editor_value_none()}</p>
	{/if}

	{#if aliases.added.length > 0}
		<div class="proposal">
			<p><strong>{m.editor_proposed_label()}</strong></p>
			<ul>
				{#each aliases.added as alias (alias)}
					<li>
						<span lang={editor.config.contentLanguage}>{alias}</span>
						<button
							type="button"
							onclick={() => (aliases.added = aliases.added.filter((each) => each !== alias))}
						>
							{m.editor_item_undo_add({ name: alias })}
						</button>
					</li>
				{/each}
			</ul>
		</div>
	{/if}

	<div class="add">
		<label for="record-alias-add">{m.editor_alias_add()}</label>
		<div class="row">
			<input
				id="record-alias-add"
				type="text"
				autocomplete="off"
				lang={editor.config.contentLanguage}
				bind:value={draft}
				onkeydown={(event) => {
					if (event.key === 'Enter') {
						event.preventDefault();
						add();
					}
				}}
			/>
			<button type="button" onclick={add}>{m.editor_alias_add_button()}</button>
		</div>
	</div>
	{#if found}
		<p class="error">
			<strong>{m.editor_error_prefix()}</strong>
			{errorText(found.code, found.params)}
		</p>
	{/if}
</section>

<style>
	.aliases {
		display: grid;
		gap: 0.75rem;
		justify-items: start;
		border-block-start: 1px solid var(--border);
		padding-block: 1rem 0.5rem;
	}

	h3,
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
		gap: 0.5rem;
		inline-size: 100%;
		border: 3px dashed var(--text);
		padding: 0.75rem;
	}

	.add {
		display: grid;
		gap: 0.35rem;
	}

	.add label {
		font-weight: 600;
	}

	.row {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
	}

	.error {
		border-inline-start: 4px solid var(--accent, currentColor);
		padding-inline-start: 0.5rem;
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
</style>
