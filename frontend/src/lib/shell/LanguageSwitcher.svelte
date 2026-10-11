<script lang="ts">
	import { page } from '$app/state';
	import { m } from '#lib/paraglide/messages.js';
	import { deLocalizeHref, isLocale, localizeHref, type Locale } from '#lib/paraglide/runtime.js';
	import { LANGUAGE_COOKIE, LANGUAGE_COOKIE_MAX_AGE_SECONDS } from '#lib/i18n/language.ts';

	let { enabled, current }: { enabled: string[]; current: Locale } = $props();

	const languages = $derived(enabled.filter(isLocale));
	const route = $derived(deLocalizeHref(page.url.pathname + page.url.search));

	function remember(language: Locale) {
		document.cookie = `${LANGUAGE_COOKIE}=${language}; path=/; max-age=${LANGUAGE_COOKIE_MAX_AGE_SECONDS}; samesite=lax`;
	}
</script>

{#if languages.length > 1}
	<nav class="languages" aria-label={m.language_switcher_label()}>
		<ul>
			{#each languages as language (language)}
				<li>
					<!-- Each language is named in itself; a change of language reloads the page. -->
					<a
						href={localizeHref(route, { locale: language })}
						hreflang={language}
						lang={language}
						aria-current={language === current ? 'true' : undefined}
						data-sveltekit-reload
						onclick={() => remember(language)}>{m.language_name({}, { locale: language })}</a
					>
				</li>
			{/each}
		</ul>
	</nav>
{/if}

<style>
	ul {
		display: flex;
		flex-wrap: wrap;
		gap: 0.75rem;
		margin: 0;
		padding: 0;
		list-style: none;
	}

	a {
		display: inline-block;
		padding-block: 0.25rem;
		text-decoration: none;
	}

	a:hover,
	a[aria-current='true'] {
		text-decoration: underline;
	}

	a[aria-current='true'] {
		font-weight: 700;
	}
</style>
