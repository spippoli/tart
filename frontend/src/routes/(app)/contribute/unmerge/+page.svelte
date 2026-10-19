<script lang="ts">
	import { enhance } from '$app/forms';
	import RecordAnchor from '#lib/archive/RecordAnchor.svelte';
	import { archiveContext } from '#lib/archive/context.svelte.ts';
	import { linkText } from '#lib/archive/records.ts';
	import { errorText } from '#lib/contribution/errors.ts';
	import { m } from '#lib/paraglide/messages.js';
	import PageTitle from '#lib/shell/PageTitle.svelte';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();

	const context = archiveContext();
	const view = $derived(data.view);
	const failure = $derived(form && 'code' in form ? errorText(String(form.code)) : null);
</script>

<PageTitle title={m.merge_unmerge_title()} />

<h1>{m.merge_unmerge_title()}</h1>

{#if view.merged_into}
	<p>
		{m.merge_unmerge_intro({
			source: linkText(view.record, context.surfaceType, context.locale),
			into: linkText(view.merged_into, context.surfaceType, context.locale)
		})}
	</p>
	<p>
		<RecordAnchor link={view.merged_into} />
	</p>

	{#if failure}
		<p class="error" role="alert">{m.merge_choose_failed({ reason: failure })}</p>
	{/if}

	<form method="post" action="?/start&kind={view.record.kind}&source={view.record.id}" use:enhance>
		<button type="submit">{m.merge_unmerge_submit()}</button>
	</form>
{:else}
	<p>{m.merge_unmerge_not_merged()}</p>
{/if}

<style>
	.error {
		border-inline-start: 4px solid var(--accent, currentColor);
		padding-inline-start: 0.5rem;
	}

	button {
		font: inherit;
		min-block-size: 2.75rem;
		padding: 0.25rem 0.75rem;
		background: var(--background);
		color: var(--text);
		border: 2px solid var(--text);
		cursor: pointer;
	}
</style>
