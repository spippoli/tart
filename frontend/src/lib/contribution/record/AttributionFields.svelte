<script lang="ts">
	import { certaintyWord } from '#lib/archive/records.ts';
	import { m } from '#lib/paraglide/messages.js';
	import { errorText } from '../errors';
	import Field from '../Field.svelte';
	import Group from '../Group.svelte';
	import type { AttributionEdit, LinkRef } from './form';
	import type { RecordEditorState } from './state.svelte';
	import { ids } from './validate';

	/**
	 * The fields of one Attribution (Contribution and moderation spec, Common rules): its
	 * certainty, the Alias the Artwork was signed with, a note, and what it cites (ADR 0006).
	 * `confirmed` needs at least one citation. What can be cited is what the Attribution
	 * cites already and the Sources this Submission creates.
	 */
	let {
		editor,
		attribution,
		earlier = []
	}: {
		editor: RecordEditorState;
		attribution: AttributionEdit;
		/** What the Attribution cited before this edit: records that exist. */
		earlier?: LinkRef[];
	} = $props();
	const config = $derived(editor.config);
	const id = (field: string) => ids.attribution(attribution.key, field);
	const CERTAINTIES = ['confirmed', 'probable', 'disputed'] as const;

	const options = $derived<LinkRef[]>([
		...earlier,
		...editor.form.sources.map((each) => ({ id: null, key: each.key, name: each.title }))
	]);

	function same(a: LinkRef, b: LinkRef) {
		return a.id !== null ? a.id === b.id : a.key === b.key;
	}

	function toggle(option: LinkRef, on: boolean) {
		attribution.citations = on
			? [...attribution.citations, option]
			: attribution.citations.filter((each) => !same(each, option));
	}

	function message(field: string) {
		const found = editor.errorAt(id(field));
		return found ? errorText(found.code, found.params) : null;
	}
</script>

<div class="fields">
	<Field id={id('certainty')} label={m.editor_attribution_certainty()} error={message('certainty')}>
		{#snippet children(props)}
			<select {...props} bind:value={attribution.certainty}>
				<option value="">{m.editor_choose()}</option>
				{#each CERTAINTIES as certainty (certainty)}
					<option value={certainty}>{certaintyWord(certainty, config.locale)}</option>
				{/each}
			</select>
		{/snippet}
	</Field>
	<Field id={id('alias')} label={m.editor_attribution_alias()}>
		{#snippet children(props)}
			<input
				{...props}
				type="text"
				lang={config.contentLanguage}
				autocomplete="off"
				bind:value={attribution.alias}
			/>
		{/snippet}
	</Field>
	<Field id={id('note')} label={m.editor_attribution_note()}>
		{#snippet children(props)}
			<textarea {...props} rows="2" lang={config.contentLanguage} bind:value={attribution.note}
			></textarea>
		{/snippet}
	</Field>
	<Group
		id={id('citations')}
		legend={m.editor_attribution_citations()}
		error={message('citations')}
	>
		{#if options.length === 0}
			<p id={id('citations')} tabindex="-1">{m.editor_citations_none()}</p>
		{:else}
			{#each options as option, index (option.id ?? option.key)}
				<label>
					<input
						id={index === 0 ? id('citations') : undefined}
						type="checkbox"
						checked={attribution.citations.some((each) => same(each, option))}
						onchange={(event) => toggle(option, event.currentTarget.checked)}
					/>
					{m.editor_cite_source({ title: option.name || m.editor_untitled_source() })}
				</label>
			{/each}
		{/if}
	</Group>
</div>

<style>
	.fields {
		display: grid;
		gap: 1rem;
		justify-items: start;
	}

	p {
		margin: 0;
	}
</style>
