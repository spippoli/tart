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
	let {
		kind,
		id,
		path,
		contribute = false
	}: { kind: Kind; id: number; path: string; contribute?: boolean } = $props();
	const context = archiveContext();
	const contributeHref = $derived(
		page.data.user ? localizeHref('/contribute') : signInHref(page.url)
	);
	// A Merge folds this record into another of its kind; for a Documentation item it is a
	// Duplicate retirement. The first step is choosing the record that survives.
	const mergeHref = $derived(
		page.data.user ? `${localizeHref('/contribute/merge')}?source=${id}` : signInHref(page.url)
	);
</script>

<section class="actions" aria-labelledby="record-actions">
	<h2 id="record-actions">{m.archive_actions_heading()}</h2>
	<ul>
		{#if contribute}
			<li><a href={contributeHref}>{m.archive_action_propose_edit()}</a></li>
			<li><a href={contributeHref}>{m.archive_action_add_documentation()}</a></li>
			<li><a href={contributeHref}>{m.archive_action_report_condition()}</a></li>
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
</style>
