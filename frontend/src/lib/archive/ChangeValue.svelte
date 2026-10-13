<script lang="ts">
	import { licence } from '#lib/licences.ts';
	import { m } from '#lib/paraglide/messages.js';
	import ChangeValue from './ChangeValue.svelte';
	import Content from './Content.svelte';
	import { archiveContext } from './context.svelte';
	import RecordAnchor from './RecordAnchor.svelte';
	import {
		archiveDate,
		archivePeriod,
		certaintyWord,
		eventWord,
		mediumWord,
		type ApiDate,
		type RecordLink
	} from './records';

	/**
	 * One value of a Revision's change list, in words (criterion 26): a linked record by
	 * its name, a vocabulary key by its label, a date or period formatted, an item by its
	 * main values. Values are as the API stored them.
	 */
	let {
		field,
		value,
		records
	}: { field: string; value: unknown; records: Record<string, RecordLink> } = $props();
	const context = archiveContext();

	const LINKS = new Set([
		'location',
		'site',
		'series',
		'sources',
		'artworks',
		'areas',
		'artist',
		'collective',
		'covering'
	]);

	type Json = Record<string, unknown>;
	const isObject = (v: unknown): v is Json =>
		typeof v === 'object' && v !== null && !Array.isArray(v);
	const link = (id: unknown) => records[String(id)];
	const words = (key: string): string => {
		switch (field) {
			case 'expression_types':
				return context.expressionType(key);
			case 'surface_type':
				return context.surfaceType(key);
			case 'medium':
				return mediumWord(key as never, context.locale);
			case 'kind':
				return key === 'collective' ? m.archive_artist_collective() : m.archive_artist_individual();
			case 'rights_basis':
				return key === 'own_work' ? m.archive_rights_own_work() : m.archive_rights_third_party();
			case 'licence':
				return licence(key, context.locale).label;
		}
		return key;
	};
	const date = (v: unknown) => archiveDate(v as ApiDate, context.dates);
	const isDate = (v: unknown): v is Json => isObject(v) && 'precision' in v;
</script>

{#snippet record(id: unknown)}
	{#if link(id)}<RecordAnchor link={link(id)} />{:else}{m.archive_value_record({
			id: String(id)
		})}{/if}
{/snippet}

{#if value === null || value === undefined || (Array.isArray(value) && value.length === 0)}
	<span class="none">{m.archive_value_none()}</span>
{:else if typeof value === 'boolean'}
	{value ? m.archive_value_yes() : m.archive_value_no()}
{:else if typeof value === 'number'}
	{#if LINKS.has(field)}{@render record(value)}{:else}{value}{/if}
{:else if typeof value === 'string'}
	{#if ['title', 'description', 'name', 'biography', 'note', 'place_description', 'author', 'publication', 'alt_text', 'text', 'creator_credit', 'aliases'].includes(field)}
		<Content text={value} />
	{:else}
		{words(value)}
	{/if}
{:else if Array.isArray(value)}
	{#each value as item, index (index)}{#if index > 0}{context.separator}{/if}<ChangeValue
			{field}
			value={item}
			{records}
		/>{/each}
{:else if isDate(value)}
	{date(value)}
{:else if isObject(value) && ('start' in value || 'end' in value)}
	{archivePeriod(value as never, context.dates)}
{:else if isObject(value) && 'coordinates' in value}
	{m.archive_value_geometry()}
{:else if isObject(value) && 'certainty' in value}
	{@render record(value.artist)} ({certaintyWord(value.certainty as never, context.locale)})
{:else if isObject(value) && 'observed_date' in value && 'type' in value}
	{eventWord(value.type as never, value.condition as never, context.locale)}, {date(
		value.observed_date
	)}
{:else if isObject(value) && 'collective' in value}
	{@render record(value.collective)}{#if value.period}
		({archivePeriod(value.period as never, context.dates)}){/if}
{:else}
	{JSON.stringify(value)}
{/if}

<style>
	.none {
		font-style: italic;
		color: var(--text-muted);
	}
</style>
