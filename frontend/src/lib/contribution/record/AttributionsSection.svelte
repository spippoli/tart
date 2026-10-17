<script lang="ts">
	import { certaintyWord } from '#lib/archive/records.ts';
	import { m } from '#lib/paraglide/messages.js';
	import { errorText } from '../errors';
	import Group from '../Group.svelte';
	import RecordPicker from '../RecordPicker.svelte';
	import AttributionFields from './AttributionFields.svelte';
	import type { AttributionEdit, LinkRef } from './form';
	import type { RecordEditorState } from './state.svelte';
	import { ids } from './validate';

	/**
	 * The Attributions of an Artwork (Contribution and moderation spec, Other editors):
	 * item-level, so each can be changed, removed, or added, and nothing else is touched.
	 * Several Attributions that are not disputed mean a collaboration; alternatives are all
	 * `disputed`. A new Artist can be created inline, with the public-name-only rule in view
	 * (ADR 0014).
	 */
	let { editor }: { editor: RecordEditorState } = $props();
	const state = $derived(editor.form.attributions);
	const present = $derived(
		(Array.isArray(editor.config.current.attributions)
			? editor.config.current.attributions
			: []) as {
			artist: number;
			certainty: AttributionEdit['certainty'];
			alias: string | null;
			note: string | null;
			citations: number[];
		}[]
	);
	const found = $derived(editor.errorAt(ids.collection('attributions')));

	function earlierOf(artist: number): LinkRef[] {
		const item = present.find((each) => each.artist === artist);
		return (item?.citations ?? []).map((cited) => ({
			id: cited,
			key: null,
			name: editor.name(cited)
		}));
	}

	function change(artist: number) {
		const item = present.find((each) => each.artist === artist);
		if (!item) return;
		state.changed[String(artist)] = {
			key: `current-${artist}`,
			artist: { kind: 'existing', id: artist, key: null, name: editor.name(artist) },
			certainty: item.certainty,
			alias: item.alias ?? '',
			note: item.note ?? '',
			citations: earlierOf(artist)
		};
	}

	function remove(artist: number, on: boolean) {
		state.removed = on
			? [...state.removed, artist]
			: state.removed.filter((each) => each !== artist);
		delete state.changed[String(artist)];
	}

	function addExisting(artist: { id: number; name: string }) {
		if (present.some((each) => each.artist === artist.id && !state.removed.includes(artist.id)))
			return;
		state.added.push({
			key: editor.newKey('attribution'),
			artist: { kind: 'existing', id: artist.id, key: null, name: artist.name },
			certainty: '',
			alias: '',
			note: '',
			citations: []
		});
	}

	function addNew(name: string) {
		const key = editor.newKey('artist');
		editor.form.artists.push({ key, name, artistKind: 'individual' });
		state.added.push({
			key: editor.newKey('attribution'),
			artist: { kind: 'new', id: null, key, name },
			certainty: '',
			alias: '',
			note: '',
			citations: []
		});
	}

	function dropAdded(each: AttributionEdit) {
		state.added = state.added.filter((other) => other !== each);
		if (each.artist?.kind === 'new') {
			const key = each.artist.key;
			editor.form.artists = editor.form.artists.filter((artist) => artist.key !== key);
		}
	}

	function setKind(key: string | null, kind: 'individual' | 'collective') {
		const artist = editor.form.artists.find((each) => each.key === key);
		if (artist) artist.artistKind = kind;
	}

	function nameOf(artist: number) {
		return editor.name(artist);
	}
</script>

<section class="attributions" id={ids.collection('attributions')} tabindex="-1">
	<h3>{m.editor_collection_attributions()}</h3>
	<p class="hint">{m.editor_attribution_hint()}</p>

	{#if present.length === 0 && state.added.length === 0}
		<p>{m.archive_unknown_artist()}</p>
	{/if}

	{#each present as item (item.artist)}
		{@const removed = state.removed.includes(item.artist)}
		{@const changed = state.changed[String(item.artist)]}
		<div class="item">
			<p class:removed>
				<strong>{nameOf(item.artist)}</strong>
				· {certaintyWord(item.certainty as 'confirmed', editor.config.locale)}
				{#if item.alias}· <span lang={editor.config.contentLanguage}>{item.alias}</span>{/if}
			</p>
			{#if removed}
				<p class="state">{m.editor_item_removed()}</p>
				<button type="button" onclick={() => remove(item.artist, false)}>
					{m.editor_item_keep({ name: nameOf(item.artist) })}
				</button>
			{:else if changed}
				<div class="proposal">
					<p><strong>{m.editor_proposed_label()}</strong></p>
					<AttributionFields {editor} attribution={changed} earlier={earlierOf(item.artist)} />
					<button type="button" onclick={() => delete state.changed[String(item.artist)]}>
						{m.editor_edit_cancel({ field: nameOf(item.artist) })}
					</button>
				</div>
			{:else}
				<div class="buttons">
					<button type="button" onclick={() => change(item.artist)}>
						{m.editor_edit_field({ field: nameOf(item.artist) })}
					</button>
					<button type="button" onclick={() => remove(item.artist, true)}>
						{m.editor_item_remove({ name: nameOf(item.artist) })}
					</button>
				</div>
			{/if}
		</div>
	{/each}

	{#each state.added as each (each.key)}
		<div class="item proposal">
			<p>
				<strong>{m.editor_proposed_label()}</strong> · {each.artist?.name}
				{#if each.artist?.kind === 'new'}<span>({m.editor_new()})</span>{/if}
			</p>
			{#if each.artist?.kind === 'new'}
				<p class="hint">{m.editor_artist_public_name()}</p>
				{@const artist = editor.form.artists.find((other) => other.key === each.artist?.key)}
				<Group id={ids.created(each.key, 'kind')} legend={m.editor_artist_kind()} radiogroup>
					<label>
						<input
							type="radio"
							name={ids.created(each.key, 'kind')}
							checked={artist?.artistKind === 'individual'}
							onchange={() => setKind(each.artist?.key ?? null, 'individual')}
						/>
						{m.editor_artist_individual()}
					</label>
					<label>
						<input
							type="radio"
							name={ids.created(each.key, 'kind')}
							checked={artist?.artistKind === 'collective'}
							onchange={() => setKind(each.artist?.key ?? null, 'collective')}
						/>
						{m.editor_artist_collective()}
					</label>
				</Group>
			{/if}
			{#if editor.errorAt(ids.attribution(each.key, 'artist'))}
				{@const problem = editor.errorAt(ids.attribution(each.key, 'artist'))!}
				<p id={ids.attribution(each.key, 'artist')} class="error" tabindex="-1">
					<strong>{m.editor_error_prefix()}</strong>
					{errorText(problem.code, problem.params)}
				</p>
			{/if}
			<AttributionFields {editor} attribution={each} />
			<button type="button" onclick={() => dropAdded(each)}>
				{m.editor_item_undo_add({ name: each.artist?.name ?? '' })}
			</button>
		</div>
	{/each}

	<RecordPicker
		{editor}
		kind="artist"
		id={ids.add('attributions')}
		label={m.editor_attribution_add()}
		onpick={addExisting}
		oncreate={addNew}
	/>
	{#if found}
		<p class="error">
			<strong>{m.editor_error_prefix()}</strong>
			{errorText(found.code, found.params)}
		</p>
	{/if}
</section>

<style>
	.attributions {
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

	.item {
		display: grid;
		gap: 0.5rem;
		justify-items: start;
		inline-size: 100%;
	}

	.removed {
		text-decoration: line-through;
	}

	.state {
		font-variant-caps: all-small-caps;
		letter-spacing: 0.04em;
	}

	.buttons {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
	}

	.proposal {
		border: 3px dashed var(--text);
		padding: 0.75rem;
		background-image: repeating-linear-gradient(
			135deg,
			transparent 0 10px,
			color-mix(in srgb, var(--text) 9%, transparent) 10px 11px
		);
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
