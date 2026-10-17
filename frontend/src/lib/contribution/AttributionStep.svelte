<script lang="ts">
	import { certaintyWord } from '#lib/archive/records.ts';
	import { m } from '#lib/paraglide/messages.js';
	import CitationChoice from './CitationChoice.svelte';
	import { errorText } from './errors';
	import Field from './Field.svelte';
	import Group from './Group.svelte';
	import RecordPicker from './RecordPicker.svelte';
	import type { AttributionForm, Certainty } from './form';
	import type { EditorState } from './state.svelte';
	import { ids } from './validate';

	/**
	 * The Attribution step (Contribution and moderation spec, Common rules): unknown
	 * authorship is an explicit choice. Each Attribution is a Claim with a certainty, its
	 * citations (`confirmed` needs one, ADR 0006), and an Evidence level shown live.
	 * Several that are not disputed mean a collaboration; alternatives are all `disputed`.
	 * A new Artist can be created here, with the public-name-only rule in view (ADR 0014).
	 */
	let { editor }: { editor: EditorState } = $props();
	const config = $derived(editor.config);
	const form = $derived(editor.form);
	const CERTAINTIES: Certainty[] = ['confirmed', 'probable', 'disputed'];

	const citables = $derived(
		editor.citables(
			(item, index) =>
				item.medium === 'link'
					? m.editor_cite_link({ number: index + 1, url: item.url })
					: m.editor_cite_file({ number: index + 1, name: item.fileName }),
			(title) => m.editor_cite_source({ title: title || m.editor_untitled_source() })
		)
	);

	function message(id: string) {
		const found = editor.errorAt(id);
		return found ? errorText(found.code, found.params) : null;
	}

	function setKind(attribution: AttributionForm, kind: 'individual' | 'collective') {
		if (attribution.artist?.kind === 'new') attribution.artist.artistKind = kind;
	}

	function add(artist: AttributionForm['artist']) {
		form.attributions.push({
			key: editor.newKey('attribution'),
			artist,
			certainty: '',
			alias: '',
			note: '',
			citations: []
		});
	}
</script>

<div class="step">
	<Group
		id={ids.attributedChoice}
		legend={m.editor_attribution_legend()}
		error={message(ids.attributedChoice)}
		radiogroup
	>
		<label>
			<input
				id={ids.attributedChoice}
				type="radio"
				name="editor-attributed"
				value={false}
				bind:group={form.attributed}
			/>
			{m.editor_attribution_unknown()}
		</label>
		<label>
			<input type="radio" name="editor-attributed" value={true} bind:group={form.attributed} />
			{m.editor_attribution_known()}
		</label>
	</Group>

	{#if form.attributed}
		<p class="hint">{m.editor_attribution_hint()}</p>

		{#if form.attributions.length > 0}
			<ol class="claims">
				{#each form.attributions as attribution, index (attribution.key)}
					{@const id = (field: string) => ids.attribution(attribution.key, field)}
					{@const artist = attribution.artist}
					<li>
						<fieldset class="claim">
							<legend>
								{m.editor_attribution_claim({
									number: index + 1,
									name: attribution.artist?.name ?? ''
								})}
							</legend>
							<p id={id('artist')} tabindex="-1" class="who" lang={config.contentLanguage}>
								{attribution.artist?.name}
								{#if artist?.kind === 'new'}
									<span lang={config.locale}>({m.editor_new()})</span>
								{/if}
							</p>
							{#if message(id('artist'))}
								<p class="error">
									<strong>{m.editor_error_prefix()}</strong>
									{message(id('artist'))}
								</p>
							{/if}
							{#if artist?.kind === 'new'}
								<p class="hint">{m.editor_artist_public_name()}</p>
								<Group id={id('artist-kind')} legend={m.editor_artist_kind()} radiogroup>
									<label>
										<input
											type="radio"
											name={id('artist-kind')}
											value="individual"
											checked={artist.artistKind === 'individual'}
											onchange={() => setKind(attribution, 'individual')}
										/>
										{m.editor_artist_individual()}
									</label>
									<label>
										<input
											type="radio"
											name={id('artist-kind')}
											value="collective"
											checked={artist.artistKind === 'collective'}
											onchange={() => setKind(attribution, 'collective')}
										/>
										{m.editor_artist_collective()}
									</label>
								</Group>
							{/if}

							<Field
								id={id('certainty')}
								label={m.editor_attribution_certainty()}
								hint={attribution.certainty === 'disputed'
									? m.editor_attribution_disputed_hint()
									: undefined}
								error={message(id('certainty'))}
							>
								{#snippet children(props)}
									<select {...props} bind:value={attribution.certainty}>
										<option value="">{m.editor_choose()}</option>
										{#each CERTAINTIES as certainty (certainty)}
											<option value={certainty}>{certaintyWord(certainty, config.locale)}</option>
										{/each}
									</select>
								{/snippet}
							</Field>

							<Field id={id('note')} label={m.editor_attribution_note()}>
								{#snippet children(props)}
									<textarea
										{...props}
										rows="2"
										lang={config.contentLanguage}
										bind:value={attribution.note}></textarea>
								{/snippet}
							</Field>

							<CitationChoice
								id={id('citations')}
								legend={m.editor_attribution_citations()}
								{citables}
								bind:selected={attribution.citations}
								locale={config.locale}
								error={message(id('citations'))}
							/>

							<button type="button" onclick={() => form.attributions.splice(index, 1)}>
								{m.editor_attribution_remove({ number: index + 1 })}
							</button>
						</fieldset>
					</li>
				{/each}
			</ol>
		{/if}

		{#if message(ids.attributionAdd)}
			<p class="error"><strong>{m.editor_error_prefix()}</strong> {message(ids.attributionAdd)}</p>
		{/if}
		<RecordPicker
			{editor}
			kind="artist"
			id={ids.attributionAdd}
			label={m.editor_attribution_picker()}
			onpick={(record) => add({ kind: 'existing', id: record.id, name: record.name })}
			oncreate={(name) =>
				add({ kind: 'new', key: editor.newKey('artist'), name, artistKind: 'individual' })}
		/>
	{/if}
</div>

<style>
	.step {
		display: grid;
		gap: 1.25rem;
		justify-items: start;
	}

	.step > p,
	.hint {
		margin: 0;
		max-inline-size: var(--measure);
	}

	.hint {
		color: var(--text-muted);
	}

	.claims {
		display: grid;
		gap: 1rem;
		list-style: none;
		margin: 0;
		padding: 0;
		inline-size: 100%;
	}

	.claim {
		display: grid;
		gap: 1rem;
		justify-items: start;
		border: 1px solid var(--border);
		margin: 0;
		padding: 1rem;
	}

	.claim legend {
		font-weight: 600;
	}

	.who {
		margin: 0;
		font-weight: 600;
	}

	.error {
		margin: 0;
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
