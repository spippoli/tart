<script lang="ts">
	import Editor from '#lib/contribution/Editor.svelte';
	import { m } from '#lib/paraglide/messages.js';
	import PageTitle from '#lib/shell/PageTitle.svelte';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
</script>

<PageTitle title={m.editor_title_new_artwork()} />

<h1>{m.editor_title_new_artwork()}</h1>

<Editor
	config={{
		submissionId: data.submission.id,
		locale: data.locale,
		timeZone: data.timeZone,
		contentLanguage: data.contentLanguage,
		boundary: data.map.boundary,
		view: data.map.view,
		attribution: data.map.attribution,
		expressionTypes: data.expressionTypes,
		surfaceTypes: data.surfaceTypes,
		licences: data.licences,
		terms: data.terms
	}}
	workingCopy={data.workingCopy}
	lastAutosave={data.submission.lastAutosave}
/>
