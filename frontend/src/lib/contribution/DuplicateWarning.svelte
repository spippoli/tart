<script lang="ts">
	import { locationTitleText, vocabularyLabels } from '#lib/archive/records.ts';
	import type { ComponentProps } from 'svelte';
	import ListEntry from '#lib/discovery/ListEntry.svelte';
	import { m } from '#lib/paraglide/messages.js';
	import { localizeHref } from '#lib/paraglide/runtime.js';
	import type { LocationCandidate } from './api';
	import { errorText } from './errors';
	import { placementKey } from './form';
	import { ids } from './validate';
	import type { EditorState } from './state.svelte';

	/**
	 * The duplicate warning of the Location step (Contribution and moderation spec,
	 * Duplicate detection): the Locations near the place chosen, each with all its
	 * Artworks, disappeared ones included, with the three ways on: add documentation to an
	 * Artwork already there, put a new Artwork on that Location, or confirm that this is
	 * another surface. Continuing as a different Artwork or surface is confirmed here, once;
	 * nothing is checked again at submission.
	 */
	type ListEntryProps = ComponentProps<typeof ListEntry>;
	let { editor }: { editor: EditorState } = $props();
	const config = $derived(editor.config);
	const surfaceLabel = $derived(vocabularyLabels(config.surfaceTypes, config.locale));
	const existing = $derived(editor.form.location.existing);
	const confirmed = $derived(
		editor.form.location.confirmedKey === placementKey(editor.form.location)
	);
	const error = $derived(editor.errorAt(ids.duplicateConfirm));

	function titleOf(candidate: LocationCandidate): string {
		return locationTitleText(
			candidate.location.id,
			candidate.location.title,
			surfaceLabel,
			config.locale
		);
	}

	function useLocation(candidate: LocationCandidate) {
		const place = editor.form.location;
		place.existing = { id: candidate.location.id, title: titleOf(candidate) };
		place.geometry = null;
		place.radius = null;
		place.confirmedKey = null;
		editor.entryVersion += 1;
	}

	function confirm(checked: boolean) {
		editor.form.location.confirmedKey = checked ? placementKey(editor.form.location) : null;
	}

	// The warning is announced when it appears, by the page's live region.
	$effect(() => {
		if (editor.duplicatesShown) {
			editor.announce(m.editor_duplicates_announcement({ count: editor.candidates.length }));
		}
	});
</script>

{#if editor.duplicatesShown}
	<section class="warning" aria-labelledby="editor-duplicates-title">
		<h3 id="editor-duplicates-title">{m.editor_duplicates_title()}</h3>
		<p>{m.editor_duplicates_intro({ count: editor.candidates.length })}</p>
		{#each editor.candidates as candidate (candidate.location.id)}
			<article class="candidate" aria-labelledby="editor-candidate-{candidate.location.id}">
				<h4 id="editor-candidate-{candidate.location.id}">{titleOf(candidate)}</h4>
				<p class="facts">
					{m.editor_duplicates_distance({
						metres: new Intl.NumberFormat(config.locale, { maximumFractionDigits: 0 }).format(
							candidate.distance
						)
					})}
					· {surfaceLabel(candidate.location.surface_type)}
					{#if candidate.site}
						· {candidate.site.name}
					{/if}
				</p>
				<ul class="artworks">
					{#each candidate.artworks as entry (entry.id)}
						<li>
							<ListEntry entry={entry as unknown as ListEntryProps['entry']} where={false} />
							<form method="post" action="{localizeHref('/contribute')}?/edit">
								<input type="hidden" name="kind" value="artwork" />
								<input type="hidden" name="id" value={entry.id} />
								<input type="hidden" name="flavour" value="documentation" />
								<button type="submit">
									{m.editor_duplicates_add_documentation({
										title: entry.title ?? m.archive_untitled()
									})}
								</button>
							</form>
						</li>
					{/each}
				</ul>
				{#if existing?.id !== candidate.location.id}
					<button type="button" onclick={() => useLocation(candidate)}>
						{m.editor_duplicates_use_location({ title: titleOf(candidate) })}
					</button>
				{/if}
			</article>
		{/each}

		<div class="confirm">
			<label>
				<input
					id={ids.duplicateConfirm}
					type="checkbox"
					checked={confirmed}
					aria-invalid={error ? 'true' : undefined}
					aria-describedby={error ? `${ids.duplicateConfirm}-error` : undefined}
					onchange={(event) => confirm(event.currentTarget.checked)}
				/>
				{existing ? m.editor_duplicates_confirm_artwork() : m.editor_duplicates_confirm_surface()}
			</label>
			{#if error}
				<p id="{ids.duplicateConfirm}-error" class="error">
					<strong>{m.editor_error_prefix()}</strong>
					{errorText(error.code, error.params)}
				</p>
			{/if}
		</div>
	</section>
{/if}

<style>
	.warning {
		display: grid;
		gap: 1rem;
		border: 2px solid var(--border);
		padding: 1rem;
	}

	.warning > * {
		margin: 0;
	}

	.candidate {
		display: grid;
		gap: 0.5rem;
		border-block-start: 1px solid var(--border);
		padding-block-start: 0.75rem;
	}

	.candidate > * {
		margin: 0;
	}

	.facts {
		color: var(--text-muted);
	}

	.artworks {
		display: grid;
		gap: 0.75rem;
		list-style: none;
		margin: 0;
		padding: 0;
	}

	.artworks li {
		display: grid;
		gap: 0.25rem;
	}

	.confirm label {
		display: flex;
		gap: 0.5rem;
		align-items: baseline;
		font-weight: 600;
	}

	.error {
		margin: 0.35rem 0 0;
		border-inline-start: 4px solid var(--accent, currentColor);
		padding-inline-start: 0.5rem;
	}

	button {
		justify-self: start;
		min-block-size: 2.75rem;
		padding-inline: 0.75rem;
		background: var(--background);
		color: var(--text);
		border: 1px solid var(--border);
		cursor: pointer;
	}
</style>
