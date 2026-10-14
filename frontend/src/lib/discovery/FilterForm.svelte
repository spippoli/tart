<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { SvelteSet, SvelteURLSearchParams } from 'svelte/reactivity';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { m } from '#lib/paraglide/messages.js';
	import { getLocale } from '#lib/paraglide/runtime.js';
	import { conditionWord, vocabularyLabels, type RecordLink } from '#lib/archive/records.ts';
	import {
		ATTRIBUTIONS,
		CONDITIONS,
		CONDITION_GROUPS,
		filterCount,
		parseState,
		queryKey,
		queryString,
		type Concept,
		type FilterState,
		type Order
	} from './state';

	/**
	 * The filters as a GET form (Discovery spec, Applying filters): with a "Show results"
	 * button it works without JavaScript. With JavaScript, on a wide screen each change
	 * applies at once (the text fields after 300 ms) through `replaceState`, without
	 * moving focus; on a narrow screen the form opens in a full-screen dialog from a
	 * "Filters" button and applies on "Show results", returning focus to the button.
	 */
	let {
		filters,
		expressionTypes,
		areas,
		keep = []
	}: {
		filters: FilterState;
		expressionTypes: { key: string; label: Record<string, string> }[];
		areas: RecordLink[];
		/** Concepts of the filters that the form holds as hidden fields (Artist, Series). */
		keep?: ('artist' | 'series')[];
	} = $props();
	const locale = getLocale();
	const typeLabel = $derived(vocabularyLabels(expressionTypes, locale));

	// What is checked, kept apart from the URL's state so that a group checkbox follows
	// its Conditions before anything is applied.
	const conditions = new SvelteSet<string>();
	const types = new SvelteSet<string>();
	const chosenAreas = new SvelteSet<string>();
	const attributions = new SvelteSet<string>();
	$effect.pre(() => {
		const sync = (set: SvelteSet<string>, values: Iterable<string>) => {
			set.clear();
			for (const value of values) set.add(value);
		};
		sync(conditions, filters.condition.length === 0 ? CONDITIONS : filters.condition);
		sync(types, filters.type);
		sync(chosenAreas, filters.area.map(String));
		sync(attributions, filters.attribution);
	});

	let enhanced = $state(false);
	let narrow = $state(false);
	let dialog: HTMLDialogElement | undefined = $state();
	let opener: HTMLButtonElement | undefined = $state();
	let form: HTMLFormElement | undefined = $state();
	onMount(() => {
		enhanced = true;
		const query = matchMedia('(max-width: 60rem)');
		narrow = query.matches;
		const follow = () => (narrow = query.matches);
		query.addEventListener('change', follow);
		return () => query.removeEventListener('change', follow);
	});

	const orders: { order: Order; label: () => string }[] = [
		{ order: 'recent', label: m.discovery_order_recent },
		{ order: 'oldest', label: m.discovery_order_oldest },
		{ order: 'added', label: m.discovery_order_added },
		{ order: 'title', label: m.discovery_order_title },
		{ order: 'relevance', label: m.discovery_order_relevance }
	];
	const groupName: Record<string, () => string> = {
		present: m.discovery_group_present,
		disappeared: m.discovery_group_disappeared,
		unknown: m.discovery_group_unknown
	};
	const attributionName: Record<string, () => string> = {
		unknown: m.discovery_attribution_unknown,
		attributed: m.discovery_attribution_attributed,
		disputed: m.discovery_attribution_disputed
	};
	const yearRanges = [
		{ legend: m.discovery_documented_legend, from: 'documentedFrom', to: 'documentedTo' },
		{ legend: m.discovery_created_legend, from: 'createdFrom', to: 'createdTo' }
	] as const;
	const key = (concept: Concept) => queryKey(concept, locale);

	function toggle(set: SvelteSet<string>, value: string, on: boolean) {
		if (on) set.add(value);
		else set.delete(value);
	}
	function toggleGroup(conditionsOfGroup: string[], on: boolean) {
		for (const condition of conditionsOfGroup) toggle(conditions, condition, on);
	}

	/** Goes to the results of what the form holds, at the canonical URL. */
	async function apply() {
		await tick();
		if (!form) return;
		const data = new FormData(form);
		const params = new SvelteURLSearchParams();
		for (const [name, value] of data) if (typeof value === 'string') params.append(name, value);
		const next = parseState(params, locale);
		// The URL is the current path with the canonical query string of the form.
		// eslint-disable-next-line svelte/no-navigation-without-resolve
		await goto(page.url.pathname + queryString(next, locale), {
			replace: true,
			reset: false
		});
	}

	let timer: ReturnType<typeof setTimeout> | undefined;
	/** Choices apply at once; the text fields after a 300 ms pause. */
	function changed(event: Event) {
		if (!enhanced || narrow) return;
		const field = event.target as HTMLInputElement | HTMLSelectElement;
		const typed = field.tagName === 'INPUT' && ['search', 'number'].includes(field.type);
		if (event.type === 'input' && typed) {
			clearTimeout(timer);
			timer = setTimeout(apply, 300);
		} else if (event.type === 'change' && !typed) {
			apply();
		}
	}

	async function submit(event: SubmitEvent) {
		if (!enhanced) return;
		event.preventDefault();
		clearTimeout(timer);
		await apply();
		if (narrow && dialog?.open) {
			dialog.close();
			opener?.focus();
		}
	}

	/** Text fields follow the URL's state unless the person is typing in them. */
	function follow(node: HTMLInputElement, value: string) {
		node.value = value;
		return {
			update(next: string) {
				if (document.activeElement !== node) node.value = next;
			}
		};
	}

	const count = $derived(filterCount(filters));
</script>

{#snippet fields()}
	<form
		bind:this={form}
		method="get"
		action={page.url.pathname}
		role={narrow && enhanced ? undefined : 'search'}
		aria-label={m.discovery_filters()}
		onsubmit={submit}
		oninput={changed}
		onchange={changed}
	>
		<div class="row">
			<label>
				<span>{m.search_label()}</span>
				<input type="search" name={key('q')} use:follow={filters.q ?? ''} maxlength="100" />
			</label>
			<label>
				<span>{m.discovery_order_label()}</span>
				<select name={key('order')}>
					<!-- Left empty, the order is the default one, which depends on whether there is a search. -->
					<option value="" selected={!filters.order}>{m.discovery_order_default()}</option>
					{#each orders as option (option.order)}
						{#if option.order !== 'relevance' || filters.q}
							<option value={option.order} selected={filters.order === option.order}
								>{option.label()}</option
							>
						{/if}
					{/each}
				</select>
			</label>
		</div>

		<fieldset>
			<legend>{m.discovery_condition_legend()}</legend>
			{#each CONDITION_GROUPS as { group, conditions: members } (group)}
				<div class="group">
					{#if enhanced}
						{@const selected = members.filter((c) => conditions.has(c)).length}
						<label class="group-label">
							<input
								type="checkbox"
								checked={selected === members.length}
								indeterminate={selected > 0 && selected < members.length}
								onchange={(event) => toggleGroup(members, event.currentTarget.checked)}
							/>
							<span>{groupName[group]()}</span>
						</label>
					{:else}
						<span class="group-label">{groupName[group]()}</span>
					{/if}
					<ul>
						{#each members as condition (condition)}
							<li>
								<label>
									<input
										type="checkbox"
										name={key('condition')}
										value={condition}
										checked={conditions.has(condition)}
										onchange={(event) => toggle(conditions, condition, event.currentTarget.checked)}
									/>
									<span>{conditionWord(condition, locale)}</span>
								</label>
							</li>
						{/each}
					</ul>
				</div>
			{/each}
		</fieldset>

		<fieldset>
			<legend>{m.discovery_type_legend()}</legend>
			<ul>
				{#each expressionTypes as option (option.key)}
					<li>
						<label>
							<input
								type="checkbox"
								name={key('type')}
								value={option.key}
								checked={types.has(option.key)}
								onchange={(event) => toggle(types, option.key, event.currentTarget.checked)}
							/>
							<span>{typeLabel(option.key)}</span>
						</label>
					</li>
				{/each}
			</ul>
		</fieldset>

		{#if areas.length > 0}
			<fieldset>
				<legend>{m.discovery_area_legend()}</legend>
				<ul>
					{#each areas as area (area.id)}
						<li>
							<label>
								<input
									type="checkbox"
									name={key('area')}
									value={area.id}
									checked={chosenAreas.has(String(area.id))}
									onchange={(event) =>
										toggle(chosenAreas, String(area.id), event.currentTarget.checked)}
								/>
								<span>{area.name}</span>
							</label>
						</li>
					{/each}
				</ul>
			</fieldset>
		{/if}

		<fieldset>
			<legend>{m.discovery_attribution_legend()}</legend>
			<ul>
				{#each ATTRIBUTIONS as value (value)}
					<li>
						<label>
							<input
								type="checkbox"
								name={key('attribution')}
								{value}
								checked={attributions.has(value)}
								onchange={(event) => toggle(attributions, value, event.currentTarget.checked)}
							/>
							<span>{attributionName[value]()}</span>
						</label>
					</li>
				{/each}
			</ul>
		</fieldset>

		{#each yearRanges as years (years.from)}
			<fieldset class="years">
				<legend>{years.legend()}</legend>
				<label>
					<span>{m.discovery_year_from()}</span>
					<input
						type="number"
						name={key(years.from)}
						min="1"
						max="9999"
						inputmode="numeric"
						use:follow={String(filters[years.from] ?? '')}
					/>
				</label>
				<label>
					<span>{m.discovery_year_to()}</span>
					<input
						type="number"
						name={key(years.to)}
						min="1"
						max="9999"
						inputmode="numeric"
						use:follow={String(filters[years.to] ?? '')}
					/>
				</label>
			</fieldset>
		{/each}

		{#each keep as concept (concept)}
			{#if filters[concept] !== null}
				<input type="hidden" name={key(concept)} value={filters[concept]} />
			{/if}
		{/each}

		<button type="submit" class="apply">{m.discovery_apply()}</button>
	</form>
{/snippet}

{#if enhanced && narrow}
	<button bind:this={opener} type="button" class="opener" onclick={() => dialog?.showModal()}>
		{count > 0 ? m.discovery_filters_active({ count }) : m.discovery_filters()}
	</button>
	<dialog bind:this={dialog} aria-label={m.discovery_filters()} onclose={() => opener?.focus()}>
		<button type="button" class="close" onclick={() => dialog?.close()}
			>{m.discovery_filters_close()}</button
		>
		{@render fields()}
	</dialog>
{:else}
	{@render fields()}
{/if}

<style>
	form {
		display: grid;
		gap: 0.75rem;
	}
	.row {
		display: flex;
		flex-wrap: wrap;
		gap: 0.75rem;
	}
	label {
		display: grid;
		gap: 0.15rem;
	}
	label:has(input[type='checkbox']) {
		display: flex;
		align-items: center;
		gap: 0.4rem;
	}
	fieldset {
		margin: 0;
		padding: 0.5rem 0.75rem;
		border: 1px solid var(--border);
		border-radius: 4px;
	}
	ul {
		display: flex;
		flex-wrap: wrap;
		gap: 0.25rem 1rem;
		margin: 0;
		padding: 0;
		list-style: none;
	}
	.group {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.25rem 1rem;
	}
	.group-label {
		font-weight: 700;
		min-inline-size: 7rem;
	}
	.years {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem 1rem;
	}
	input,
	select,
	button {
		font: inherit;
		color: inherit;
		background: var(--background);
		border: 1px solid var(--border);
		border-radius: 0.25rem;
		padding: 0.25rem 0.5rem;
	}
	input[type='checkbox'] {
		inline-size: 1.1rem;
		block-size: 1.1rem;
		padding: 0;
	}
	button {
		background: var(--surface);
		cursor: pointer;
		justify-self: start;
	}
	dialog {
		inline-size: 100%;
		block-size: 100%;
		max-inline-size: none;
		max-block-size: none;
		box-sizing: border-box;
		margin: 0;
		overflow: auto;
		color: var(--text);
		background: var(--background);
		border: 0;
	}
	.close {
		margin-block-end: 0.75rem;
	}
</style>
