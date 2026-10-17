<script lang="ts">
	import type { Geometry } from '#lib/map/drawing.ts';
	import { m } from '#lib/paraglide/messages.js';
	import { errorText } from '../errors';
	import AliasesSection from './AliasesSection.svelte';
	import AreaReadout from './AreaReadout.svelte';
	import AttributionsSection from './AttributionsSection.svelte';
	import CrewSection from './CrewSection.svelte';
	import FieldInput from './FieldInput.svelte';
	import FieldRow from './FieldRow.svelte';
	import LinksSection from './LinksSection.svelte';
	import LocationNotices from './LocationNotices.svelte';
	import NameWarning from './NameWarning.svelte';
	import { SPECS, type FieldSpec } from './spec';
	import type { RecordEditorState } from './state.svelte';
	import { ids, stepOfCollection, stepOfField } from './validate';
	import { fieldLabel } from './words';

	/**
	 * A step that asks fields and collections of a record: the one step of an edit ("What
	 * changes", Contribution and moderation spec, Other editors), or a step of a new Area
	 * or Artist. An edit shows each field as current against proposed; a new record shows the
	 * controls at once. The notices that belong to a kind come first.
	 */
	let { editor, step }: { editor: RecordEditorState; step: string } = $props();
	const kind = $derived(editor.kind);
	const spec = $derived(SPECS[kind]);
	const medium = $derived(String(editor.config.current.medium ?? ''));
	const applicable = (field: FieldSpec) => !field.media || field.media.includes(medium);
	const fields = $derived(
		spec.fields.filter((each) => applicable(each) && stepOfField(each, editor.creating) === step)
	);
	const collections = $derived(
		spec.collections.filter(
			(each) => each.picker !== 'sources' && stepOfCollection(each, editor.creating) === step
		)
	);
	const found = $derived(editor.errorAt(ids.changes));
	const related = $derived(editor.config.related);
	const name = $derived(
		editor.creating && typeof editor.form.fields.name === 'string' ? editor.form.fields.name : ''
	);
</script>

<div class="step">
	{#if !editor.creating}
		<p class="intro" id={ids.changes} tabindex="-1">{m.editor_changes_intro()}</p>
		{#if found}
			<p class="error">
				<strong>{m.editor_error_prefix()}</strong>
				{errorText(found.code, found.params)}
			</p>
		{/if}
	{/if}

	{#if kind === 'location' && !editor.creating}
		<LocationNotices {editor} />
	{/if}
	{#if kind === 'artist'}
		<p class="notice">{m.editor_artist_public_name()}</p>
	{/if}
	{#if kind === 'documentation_item' && !editor.creating}
		<p class="notice">{m.editor_item_fixed()}</p>
	{/if}

	{#each fields as field (field.name)}
		{#if editor.creating}
			<div class="field">
				<FieldInput {editor} spec={field} label={fieldLabel(field.name)} />
				{#if field.name === 'name' && (kind === 'artist' || kind === 'area')}
					<NameWarning {editor} {kind} {name} />
				{/if}
				{#if field.type === 'geometry'}
					<AreaReadout {editor} geometry={editor.form.fields.geometry as Geometry | null} />
				{/if}
			</div>
		{:else}
			<FieldRow {editor} spec={field} />
		{/if}
	{/each}

	{#each collections as collection (collection.name)}
		{#if collection.type === 'links'}
			<LinksSection {editor} {collection} />
		{:else if collection.type === 'aliases'}
			<AliasesSection {editor} />
		{:else if collection.type === 'attributions'}
			<AttributionsSection {editor} />
		{:else}
			<CrewSection {editor} />
		{/if}
	{/each}

	{#if !editor.creating && related && related.kind !== 'members'}
		<section class="related">
			<h3>
				{related.kind === 'locations' ? m.editor_related_locations() : m.editor_related_artworks()}
			</h3>
			<p class="hint">
				{related.kind === 'locations'
					? m.editor_related_locations_hint()
					: m.editor_related_artworks_hint()}
			</p>
			{#if related.items.length === 0}
				<p>{m.editor_value_none()}</p>
			{:else}
				<ul>
					{#each related.items as item (item.href)}
						<li><a href={item.href}>{item.name}</a></li>
					{/each}
				</ul>
			{/if}
		</section>
	{/if}
</div>

<style>
	.step {
		display: grid;
		gap: 1.25rem;
	}

	.step p,
	h3 {
		margin: 0;
	}

	.intro {
		max-inline-size: var(--measure);
	}

	.notice {
		border-inline-start: 4px solid var(--border);
		padding-inline-start: 0.75rem;
	}

	.field {
		display: grid;
		gap: 0.75rem;
		justify-items: start;
	}

	.related {
		display: grid;
		gap: 0.5rem;
		border-block-start: 1px solid var(--border);
		padding-block-start: 1rem;
	}

	.hint {
		color: var(--text-muted);
	}

	ul {
		margin: 0;
		padding-inline-start: 1.25rem;
	}

	.error {
		border-inline-start: 4px solid var(--accent, currentColor);
		padding-inline-start: 0.5rem;
	}
</style>
