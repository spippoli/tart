<script lang="ts">
	import '../app.css';
	import { page } from '$app/state';
	import { m } from '#lib/paraglide/messages.js';
	import { deLocalizeHref, isLocale, localizeHref } from '#lib/paraglide/runtime.js';
	import Footer from '#lib/shell/Footer.svelte';
	import Header from '#lib/shell/Header.svelte';
	import { svgDataUrl } from '#lib/shell/svg.ts';
	import type { LayoutProps } from './$types';

	let { data, children }: LayoutProps = $props();

	// Alternates for the same page in every enabled UI language; `x-default` is the
	// root, which chooses the language (ADR 0008).
	const alternates = $derived.by(() => {
		const route = deLocalizeHref(page.url.pathname + page.url.search);
		return data.enabledLanguages.filter(isLocale).map((language) => ({
			language,
			href: new URL(localizeHref(route, { locale: language }), page.url.origin).href
		}));
	});
</script>

<svelte:head>
	<link rel="icon" href={svgDataUrl(data.identity.favicon)} type="image/svg+xml" />
	{#each alternates as { language, href } (language)}
		<link rel="alternate" hreflang={language} {href} />
	{/each}
	<link rel="alternate" hreflang="x-default" href={new URL('/', page.url.origin).href} />
</svelte:head>

<div
	class="shell"
	style:--accent-light={data.identity.accent.light}
	style:--accent-dark={data.identity.accent.dark}
>
	<a class="skip-link" href="#main">{m.shell_skip_to_content()}</a>
	<Header
		identity={data.identity}
		contentLanguage={data.contentLanguage}
		enabledLanguages={data.enabledLanguages}
		locale={data.locale}
	/>
	<main id="main" tabindex="-1">
		{@render children()}
	</main>
	<Footer dataLicence={data.dataLicence} locale={data.locale} />
</div>

<style>
	/* The Instance accent, each value against its own theme's background. */
	.shell {
		--accent: var(--accent-light);
		display: flex;
		flex-direction: column;
		min-block-size: 100vh;
	}

	@media (prefers-color-scheme: dark) {
		.shell {
			--accent: var(--accent-dark);
		}
	}

	main {
		flex: 1;
		padding-inline: var(--gutter);
	}

	main:focus {
		outline: none;
	}

	.skip-link {
		position: absolute;
		inset-inline-start: var(--gutter);
		inset-block-start: -10rem;
		padding: 0.5rem 1rem;
		background: var(--background);
		z-index: 1;
	}

	.skip-link:focus {
		inset-block-start: 0.5rem;
	}
</style>
