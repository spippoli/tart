<script lang="ts">
	import {
		formatUncertainDate,
		precisionLabel,
		qualifierLabel
	} from '#lib/archive/uncertain-date.ts';
	import { m } from '#lib/paraglide/messages.js';
	import type { Locale } from '#lib/paraglide/runtime.js';
	import { toUncertainDate, type DateField } from './date-field';
	import Group from './Group.svelte';

	/**
	 * The Uncertain date input (Contribution and moderation spec, Common rules): a
	 * qualifier, a precision, and one value, or two with `exact` for a "from-to" range,
	 * plus a separate "Unknown date" choice. A live readout words the date as the archive
	 * will show it ("c. 2019"). The first control carries `id`; a problem with the end of
	 * a range or with the qualifier is on `{id}-second` and `{id}-qualifier`.
	 */
	let {
		id,
		legend,
		value = $bindable(),
		locale,
		timeZone,
		today,
		error,
		optional = false
	}: {
		id: string;
		legend: string;
		value: DateField;
		locale: Locale;
		timeZone: string;
		today: string;
		error?: string | null;
		/** The date may stay empty (the Creation date). */
		optional?: boolean;
	} = $props();

	const QUALIFIERS = ['exact', 'circa', 'before', 'after'] as const;
	const PRECISIONS = ['day', 'month', 'year', 'decade'] as const;
	const LENGTH = { day: 10, month: 7, year: 4, decade: 4 } as const;

	const readout = $derived.by(() => {
		const outcome = toUncertainDate(value, today);
		if ('problem' in outcome || outcome.date === null) return null;
		return formatUncertainDate(outcome.date, { locale, timeZone });
	});

	function changePrecision() {
		// A value cut to the new precision keeps what it can; one that is too short is cleared.
		const length = LENGTH[value.precision];
		for (const field of ['first', 'second'] as const) {
			const text = value[field];
			value[field] = text.length >= length ? text.slice(0, length) : '';
		}
	}
</script>

<Group {id} {legend} {error}>
	{#snippet children({ invalid })}
		{#if optional}
			<p class="hint">{m.editor_date_optional()}</p>
		{/if}
		<label class="check">
			<input type="checkbox" bind:checked={value.unknown} />
			{m.editor_date_unknown()}
		</label>
		{#if !value.unknown}
			<div class="row">
				<label>
					{m.editor_date_qualifier()}
					<select id="{id}-qualifier" bind:value={value.qualifier}>
						{#each QUALIFIERS as qualifier (qualifier)}
							<option value={qualifier}>{qualifierLabel(qualifier, locale)}</option>
						{/each}
					</select>
				</label>
				<label>
					{m.editor_date_precision()}
					<select bind:value={value.precision} onchange={changePrecision}>
						{#each PRECISIONS as precision (precision)}
							<option value={precision}>{precisionLabel(precision, locale)}</option>
						{/each}
					</select>
				</label>
			</div>
			<div class="row">
				<label>
					{value.qualifier === 'exact' ? m.editor_date_value_from() : m.editor_date_value()}
					{#if value.precision === 'day'}
						<input {id} type="date" bind:value={value.first} aria-invalid={invalid} />
					{:else if value.precision === 'month'}
						<input {id} type="month" bind:value={value.first} aria-invalid={invalid} />
					{:else}
						<input
							{id}
							type="text"
							inputmode="numeric"
							maxlength="4"
							autocomplete="off"
							bind:value={value.first}
							aria-invalid={invalid}
						/>
					{/if}
				</label>
				{#if value.qualifier === 'exact'}
					<label>
						{m.editor_date_value_to()}
						{#if value.precision === 'day'}
							<input id="{id}-second" type="date" bind:value={value.second} />
						{:else if value.precision === 'month'}
							<input id="{id}-second" type="month" bind:value={value.second} />
						{:else}
							<input
								id="{id}-second"
								type="text"
								inputmode="numeric"
								maxlength="4"
								autocomplete="off"
								bind:value={value.second}
							/>
						{/if}
					</label>
				{/if}
			</div>
			{#if value.precision === 'decade'}
				<p class="hint">{m.editor_date_decade_hint()}</p>
			{/if}
		{/if}
		<p class="readout" role="status">
			{#if value.unknown}
				{m.editor_date_readout({
					date: formatUncertainDate({ precision: 'unknown' }, { locale, timeZone })
				})}
			{:else if readout}
				{m.editor_date_readout({ date: readout })}
			{/if}
		</p>
	{/snippet}
</Group>

<style>
	.row {
		display: flex;
		flex-wrap: wrap;
		gap: 0.75rem 1.5rem;
	}

	.row label {
		display: grid;
		gap: 0.25rem;
		font-weight: 400;
	}

	.check {
		display: flex;
	}

	.hint,
	.readout {
		margin: 0;
		color: var(--text-muted);
	}

	.readout:empty {
		display: none;
	}
</style>
