<script lang="ts">
	import { page } from '$app/state';
	import { m } from '#lib/paraglide/messages.js';
	import { localizeHref } from '#lib/paraglide/runtime.js';
	import PageTitle from '#lib/shell/PageTitle.svelte';

	// The frame of the error pages; the specs that answer 403 or 410 may add content.
	const known: Record<number, { title: () => string; text: () => string }> = {
		403: { title: m.error_403_title, text: m.error_403_text },
		404: { title: m.error_404_title, text: m.error_404_text },
		410: { title: m.error_410_title, text: m.error_410_text }
	};

	const message = $derived(known[page.status] ?? { title: m.error_title, text: m.error_unknown });
</script>

<PageTitle title={message.title()} />

<h1>{message.title()}</h1>
<p>{message.text()}</p>
<p class="status">{m.error_status({ status: page.status })}</p>
<p><a href={localizeHref('/')}>{m.error_home_link()}</a></p>

<style>
	.status {
		color: var(--text-muted);
	}
</style>
