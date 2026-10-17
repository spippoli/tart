<script lang="ts">
	import { page } from '$app/state';
	import { signInHref } from '#lib/auth/next.ts';
	import { m } from '#lib/paraglide/messages.js';
	import { localizeHref } from '#lib/paraglide/runtime.js';
	import { archiveContext } from './context.svelte';
	import { reportHref, revisionsHref, type Kind } from './records';

	/**
	 * The actions every record page ends with: the contribution actions (Artworks only,
	 * for now), "Report", and the link to `/revisions`. Contribution goes through
	 * sign-in for an anonymous visitor, who comes back here.
	 */
	let { kind, id, path }: { kind: Kind; id: number; path: string } = $props();
	const context = archiveContext();
	const signedIn = $derived(Boolean(page.data.user));
	const signIn = $derived(signInHref(page.url));
	const start = $derived(`${localizeHref('/contribute')}?/edit`);
	// A Merge folds this record into another of its kind; for a Documentation item it is a
	// Duplicate retirement. The first step is choosing the record that survives.
	const mergeHref = $derived(
		page.data.user ? `${localizeHref('/contribute/merge')}?source=${id}` : signInHref(page.url)
	);
</script>

{#snippet action(flavour: string, label: string)}
	<li>
		{#if signedIn}
			<form method="post" action={start}>
				<input type="hidden" name="kind" value={kind} />
				<input type="hidden" name="id" value={id} />
				<input type="hidden" name="flavour" value={flavour} />
				<button type="submit" class="link">{label}</button>
			</form>
		{:else}
			<a href={signIn}>{label}</a>
		{/if}
	</li>
{/snippet}

<section class="actions" aria-labelledby="record-actions">
	<h2 id="record-actions">{m.archive_actions_heading()}</h2>
	<ul>
		{@render action('edit', m.archive_action_propose_edit())}
		{#if kind === 'artwork'}
			{@render action('documentation', m.archive_action_add_documentation())}
			{@render action('event', m.archive_action_report_condition())}
			{@render action('facts', m.archive_action_other_facts())}
		{/if}
		<li>
			<a href={mergeHref}>
				{kind === 'documentation_item' ? m.merge_action_retirement() : m.merge_action_merge()}
			</a>
		</li>
		<li><a href={reportHref(context.locale, kind, id)}>{m.archive_action_report()}</a></li>
		<li><a href={revisionsHref(kind, path)}>{m.archive_revisions_link()}</a></li>
	</ul>
</section>

<style>
	ul {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem 1.5rem;
		padding: 0;
		list-style: none;
	}

	.link {
		font: inherit;
		color: inherit;
		background: none;
		border: 0;
		padding: 0;
		text-decoration: underline;
		cursor: pointer;
	}
</style>
