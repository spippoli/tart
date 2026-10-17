<script lang="ts">
	import { evidenceWords } from '#lib/archive/records.ts';
	import { m } from '#lib/paraglide/messages.js';
	import type { Locale } from '#lib/paraglide/runtime.js';
	import type { Citable } from './form';
	import Group from './Group.svelte';

	/**
	 * What a Claim cites (ADR 0006): the Sources and Documentation items of this
	 * Submission, with the Evidence level it will have as a live readout in words: *reported*
	 * when it cites nothing, *documented* otherwise.
	 */
	let {
		id,
		legend,
		citables,
		selected = $bindable(),
		locale,
		error
	}: {
		id: string;
		legend: string;
		citables: Citable[];
		selected: string[];
		locale: Locale;
		error?: string | null;
	} = $props();

	const cited = $derived(selected.filter((key) => citables.some((each) => each.key === key)));

	function toggle(key: string, on: boolean) {
		selected = on ? [...selected, key] : selected.filter((each) => each !== key);
	}
</script>

<Group {id} {legend} {error}>
	{#snippet children({ invalid })}
		{#if citables.length === 0}
			<p {id} class="none" tabindex="-1">{m.editor_citations_none()}</p>
		{:else}
			{#each citables as citable, index (citable.key)}
				<label>
					<input
						id={index === 0 ? id : undefined}
						type="checkbox"
						checked={selected.includes(citable.key)}
						aria-invalid={index === 0 ? invalid : undefined}
						onchange={(event) => toggle(citable.key, event.currentTarget.checked)}
					/>
					{citable.label}
				</label>
			{/each}
		{/if}
		<p class="evidence" role="status">
			{m.editor_evidence_readout({
				level: evidenceWords(cited.length > 0 ? 'documented' : 'reported', cited.length, locale)
			})}
		</p>
	{/snippet}
</Group>

<style>
	.none,
	.evidence {
		margin: 0;
	}

	.evidence {
		color: var(--text-muted);
	}
</style>
