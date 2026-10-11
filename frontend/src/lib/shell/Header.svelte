<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { page } from '$app/state';
	import { afterNavigate } from '$app/navigation';
	import { m } from '#lib/paraglide/messages.js';
	import { deLocalizeHref, localizeHref, type Locale } from '#lib/paraglide/runtime.js';
	import { textDirection } from '#lib/i18n/language.ts';
	import type { PublicConfiguration } from '#lib/server/instance-config.ts';
	import LanguageSwitcher from './LanguageSwitcher.svelte';
	import { svgDataUrl } from './svg';

	let {
		identity,
		contentLanguage,
		enabledLanguages,
		locale
	}: {
		identity: PublicConfiguration['identity'];
		contentLanguage: string;
		enabledLanguages: string[];
		locale: Locale;
	} = $props();

	const sections = [
		{ route: '/', label: m.nav_explore },
		{ route: '/archive', label: m.nav_archive },
		{ route: '/artists', label: m.nav_artists },
		{ route: '/contribute', label: m.nav_contribute },
		{ route: '/about', label: m.nav_about }
	];

	const route = $derived(deLocalizeHref(page.url.pathname));
	const isCurrent = (section: string) =>
		section === '/' ? route === '/' : route === section || route.startsWith(`${section}/`);

	// Without JavaScript the navigation is always shown; with it, narrow screens
	// put it behind the Menu disclosure button.
	let enhanced = $state(false);
	let open = $state(false);
	let menuButton: HTMLButtonElement | undefined = $state();
	onMount(() => (enhanced = true));
	afterNavigate(() => (open = false));

	async function closeOnEscape(event: KeyboardEvent) {
		if (event.key !== 'Escape' || !open) return;
		open = false;
		await tick();
		menuButton?.focus();
	}
</script>

<header class="site-header" class:enhanced>
	<div class="identity">
		<a class="logo" href={localizeHref('/')}>
			<picture>
				<source srcset={svgDataUrl(identity.logo.dark)} media="(prefers-color-scheme: dark)" />
				<img
					src={svgDataUrl(identity.logo.light)}
					alt={identity.logo.alt}
					lang={contentLanguage}
					dir={textDirection(contentLanguage)}
				/>
			</picture>
		</a>
		<span class="archive-name" lang={contentLanguage} dir={textDirection(contentLanguage)}
			>{identity.name}</span
		>
	</div>

	{#if enhanced}
		<button
			bind:this={menuButton}
			class="menu-button"
			type="button"
			aria-expanded={open}
			aria-controls="site-menu"
			onclick={() => (open = !open)}>{m.nav_menu()}</button
		>
	{/if}

	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div id="site-menu" class="menu" class:open onkeydown={closeOnEscape}>
		<nav aria-label={m.nav_label()}>
			<ul class="sections">
				{#each sections as section (section.route)}
					<li>
						<a
							href={localizeHref(section.route)}
							aria-current={isCurrent(section.route) ? 'page' : undefined}>{section.label()}</a
						>
					</li>
				{/each}
			</ul>
		</nav>

		<form class="search" role="search" method="get" action={localizeHref('/archive')}>
			<label class="visually-hidden" for="site-search">{m.search_label()}</label>
			<input id="site-search" name="q" type="search" />
			<button type="submit">{m.search_submit()}</button>
		</form>

		<LanguageSwitcher enabled={enabledLanguages} current={locale} />

		<div class="user-menu">
			<a href={localizeHref('/sign-in')}>{m.user_menu_sign_in()}</a>
		</div>
	</div>
</header>

<style>
	.site-header {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.75rem 1.5rem;
		padding: 0.75rem var(--gutter);
		border-block-end: 3px solid var(--accent);
	}

	.identity {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		margin-inline-end: auto;
	}

	.logo {
		display: inline-flex;
	}

	.logo img {
		display: block;
		block-size: 2.75rem;
		inline-size: auto;
		max-inline-size: 12rem;
	}

	.archive-name {
		font-weight: 700;
		font-size: 1.125rem;
		line-height: 1.25;
	}

	.menu {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.75rem 1.5rem;
	}

	.sections {
		display: flex;
		flex-wrap: wrap;
		gap: 0.25rem 1rem;
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.sections a {
		display: inline-block;
		padding-block: 0.25rem;
		text-decoration: none;
	}

	.sections a:hover,
	.sections a[aria-current='page'] {
		text-decoration: underline;
	}

	.sections a[aria-current='page'] {
		font-weight: 700;
	}

	.search {
		display: flex;
		gap: 0.25rem;
	}

	input,
	button {
		font: inherit;
		color: inherit;
		background: var(--background);
		border: 1px solid var(--border);
		border-radius: 0.25rem;
		padding: 0.25rem 0.5rem;
	}

	button {
		background: var(--surface);
		cursor: pointer;
	}

	.menu-button {
		display: none;
	}

	@media (max-width: 60rem) {
		.enhanced .menu-button {
			display: inline-block;
		}

		.menu {
			flex-basis: 100%;
			flex-direction: column;
			align-items: flex-start;
		}

		.enhanced .menu:not(.open) {
			display: none;
		}

		.sections {
			flex-direction: column;
		}
	}
</style>
