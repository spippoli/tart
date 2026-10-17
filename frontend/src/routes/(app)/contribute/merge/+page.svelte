<script lang="ts">
	import { enhance } from '$app/forms';
	import RecordAnchor from '#lib/archive/RecordAnchor.svelte';
	import { archiveContext } from '#lib/archive/context.svelte.ts';
	import { kindWord, linkText } from '#lib/archive/records.ts';
	import { errorText } from '#lib/contribution/errors.ts';
	import { m } from '#lib/paraglide/messages.js';
	import PageTitle from '#lib/shell/PageTitle.svelte';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();

	const context = archiveContext();
	const retirement = $derived(data.source.kind === 'documentation_item');
	const sourceName = $derived(linkText(data.source, context.surfaceType, context.locale));
	const failure = $derived(form && 'code' in form ? errorText(String(form.code)) : null);
</script>

<PageTitle title={retirement ? m.merge_title_retirement() : m.merge_choose_title()} />

<h1>{retirement ? m.merge_title_retirement() : m.merge_choose_title()}</h1>

<p>
	{(retirement ? m.merge_choose_retirement_intro : m.merge_choose_intro)({ source: sourceName })}
</p>
<p>
	{kindWord(data.source.kind, context.locale)}
	<RecordAnchor link={data.source} />
</p>

{#if failure}
	<p class="error" role="alert">{m.merge_choose_failed({ reason: failure })}</p>
{/if}

<section aria-labelledby="candidates">
	<form method="post" action="?/start&source={data.source.id}" use:enhance>
		<input type="hidden" name="source" value={data.source.id} />
		<h2 id="candidates">{m.merge_choose_candidates()}</h2>
		{#if data.candidates.length === 0}
			<p>{m.merge_choose_none()}</p>
		{:else}
			<ul class="candidates">
				{#each data.candidates as candidate (candidate.id)}
					<li>
						{kindWord(candidate.kind, context.locale)}
						<RecordAnchor link={candidate} />
						<button type="submit" name="into" value={candidate.id}>
							{retirement ? m.merge_choose_use_retirement() : m.merge_choose_use()}
							<span class="visually-hidden"
								>: {linkText(candidate, context.surfaceType, context.locale)}</span
							>
						</button>
					</li>
				{/each}
			</ul>
		{/if}
	</form>
</section>

<section aria-labelledby="by-number">
	<h2 id="by-number">{m.merge_choose_by_number()}</h2>
	<form method="post" action="?/start&source={data.source.id}" use:enhance>
		<input type="hidden" name="source" value={data.source.id} />
		<div class="field">
			<label for="number">{m.merge_choose_number_label()}</label>
			<p id="number-hint" class="hint">{m.merge_choose_number_hint()}</p>
			<input
				id="number"
				name="number"
				value={data.into ?? ''}
				type="number"
				min="1"
				inputmode="numeric"
				aria-describedby="number-hint"
			/>
		</div>
		<p><button type="submit">{m.merge_choose_number_submit()}</button></p>
	</form>
</section>

<style>
	.candidates {
		list-style: none;
		padding: 0;
		display: grid;
		gap: 0.75rem;
	}

	.candidates li {
		display: flex;
		flex-wrap: wrap;
		gap: 0.75rem;
		align-items: center;
	}

	.field {
		display: grid;
		gap: 0.35rem;
		max-inline-size: 20rem;
	}

	.hint {
		margin: 0;
		color: var(--text-muted);
	}

	.error {
		border-inline-start: 4px solid var(--accent, currentColor);
		padding-inline-start: 0.5rem;
	}

	button,
	input {
		font: inherit;
		min-block-size: 2.75rem;
		padding: 0.25rem 0.75rem;
		background: var(--background);
		color: var(--text);
		border: 1px solid var(--border);
	}

	button {
		cursor: pointer;
	}
</style>
