<script lang="ts">
	import { page } from '$app/state';
	import { m } from '#lib/paraglide/messages.js';
	import { localizeHref } from '#lib/paraglide/runtime.js';
	import type { LayoutProps } from './$types';

	let { data, children }: LayoutProps = $props();

	// The other entries (Notices, Legal actions) come with their pages.
	const entries = $derived([
		{ href: localizeHref('/moderation'), label: m.moderation_nav_queue() },
		...(data.invitationsEnabled
			? [{ href: localizeHref('/moderation/invitations'), label: m.moderation_nav_invitations() }]
			: [])
	]);
</script>

<nav aria-label={m.moderation_nav_label()}>
	<ul>
		{#each entries as entry (entry.href)}
			<li>
				<a href={entry.href} aria-current={page.url.pathname === entry.href ? 'page' : undefined}
					>{entry.label}</a
				>
			</li>
		{/each}
	</ul>
</nav>

{@render children()}

<style>
	ul {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem 1.5rem;
		list-style: none;
		margin: 0 0 1.5rem;
		padding: 0;
	}

	/* The current page is marked by weight and an underline, never by colour alone. */
	a[aria-current='page'] {
		font-weight: 700;
		text-decoration: underline;
		text-underline-offset: 0.25em;
	}
</style>
