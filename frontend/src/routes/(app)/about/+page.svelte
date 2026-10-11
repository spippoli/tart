<script lang="ts">
	import { m } from '#lib/paraglide/messages.js';
	import { localizeHref } from '#lib/paraglide/runtime.js';
	import ContentText from '#lib/shell/ContentText.svelte';
	import PageTitle from '#lib/shell/PageTitle.svelte';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const subpages = $derived(
		[
			{ route: '/about/guidelines', title: m.about_guidelines_title, shown: data.hasGuidelines },
			{
				route: '/about/contribution-policy',
				title: m.about_contribution_policy_title,
				shown: data.hasContributionPolicy
			},
			{ route: '/about/terms', title: m.about_terms_title, shown: true },
			{ route: '/about/privacy', title: m.about_privacy_title, shown: true },
			{ route: '/about/contact', title: m.about_contact_title, shown: true },
			{ route: '/about/data-licence', title: m.about_data_licence_title, shown: true },
			{ route: '/about/tart', title: m.about_tart_title, shown: true }
		].filter(({ shown }) => shown)
	);
</script>

<PageTitle title={m.about_title()} />

<h1>{m.about_title()}</h1>

{#if data.aboutHtml}
	<ContentText html={data.aboutHtml} />
{/if}

<nav aria-label={m.about_pages_label()}>
	<ul>
		{#each subpages as subpage (subpage.route)}
			<li><a href={localizeHref(subpage.route)}>{subpage.title()}</a></li>
		{/each}
	</ul>
</nav>
