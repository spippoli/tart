<script lang="ts">
	import { kindWord } from '#lib/archive/records.ts';
	import MergeEditor from '#lib/contribution/merge/MergeEditor.svelte';
	import ArtworkEditor from '#lib/contribution/ArtworkEditor.svelte';
	import RecordEditor from '#lib/contribution/record/RecordEditor.svelte';
	import { m } from '#lib/paraglide/messages.js';
	import PageTitle from '#lib/shell/PageTitle.svelte';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const mergeTitles = {
		merge: m.merge_title_merge,
		retirement: m.merge_title_retirement,
		unmerge: m.merge_title_unmerge
	};
	const title = $derived.by(() => {
		if (data.editor === 'merge') return mergeTitles[data.mergeEditor.intent]();
		if (data.editor === 'artwork') {
			return data.flavour === 'documentation'
				? m.editor_title_documentation()
				: data.flavour === 'event'
					? m.editor_title_event()
					: m.editor_title_new_artwork();
		}
		if (data.creating) {
			return data.kind === 'area' ? m.editor_title_new_area() : m.editor_title_new_artist();
		}
		return m.editor_title_edit({ kind: kindWord(data.kind, data.locale) });
	});
</script>

<PageTitle {title} />

{#if data.editor === 'merge'}
	<MergeEditor config={data.mergeEditor} />
{:else}
	<h1>{title}</h1>
{/if}

{#if data.editor === 'merge'}
	<!-- the Merge editor has its own heading -->
{:else if data.editor === 'artwork'}
	<ArtworkEditor
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
			terms: data.terms,
			flavour: data.flavour,
			target: 'target' in data ? data.target : undefined
		}}
		workingCopy={data.workingCopy}
		lastAutosave={data.submission.lastAutosave}
	/>
{:else}
	<RecordEditor
		config={{
			submissionId: data.submission.id,
			locale: data.locale,
			timeZone: data.timeZone,
			contentLanguage: data.contentLanguage,
			terms: data.terms,
			kind: data.kind,
			creating: data.creating,
			targetId: data.targetId,
			current: data.current as Record<string, never>,
			links: data.links,
			redactedFields: data.redactedFields,
			artworkCount: data.artworkCount,
			related: data.related,
			surfaceTypes: data.surfaceTypes,
			expressionTypes: data.expressionTypes,
			licences: data.licences,
			boundary: data.map.boundary,
			view: data.map.view,
			attribution: data.map.attribution
		}}
		workingCopy={data.workingCopy}
		lastAutosave={data.submission.lastAutosave}
	/>
{/if}
