<script lang="ts">
	import { m } from '#lib/paraglide/messages.js';
	import { initialLegendOpen, rememberLegend } from './legend-memory';
	import Sign from './Sign.svelte';
	import { SIGN_KINDS, type SignKind } from './signs';
	import type { Tokens } from './style';

	// The legend disclosure of the map control (Discovery spec, Map controls, legend,
	// attribution): every sign drawn from the Instance style, each with one line of text.
	let { tokens }: { tokens: Tokens } = $props();

	let open = $state(initialLegendOpen());
	const id = $props.id();

	const text: Record<SignKind, () => string> = {
		present: m.map_legend_present,
		unknown: m.map_legend_unknown,
		disappeared: m.map_legend_disappeared,
		stack: m.map_legend_stack,
		cluster: m.map_legend_cluster,
		hatch: m.map_legend_hatch
	};

	function toggle() {
		open = !open;
		rememberLegend(open);
	}
</script>

<div class="legend">
	<button type="button" aria-expanded={open} aria-controls="{id}-legend" onclick={toggle}>
		{m.map_legend()}
	</button>
	<ul id="{id}-legend" hidden={!open}>
		{#each SIGN_KINDS as kind (kind)}
			<li>
				<span class="swatch"><Sign {kind} {tokens} size={kind === 'hatch' ? 24 : 16} /></span>
				{text[kind]()}
			</li>
		{/each}
	</ul>
</div>

<style>
	button {
		min-block-size: 2.75rem;
		padding-inline: 0.75rem;
		font: inherit;
		background: var(--background);
		color: var(--text);
		border: 1px solid var(--border);
		cursor: pointer;
	}

	button:hover {
		background: var(--surface);
	}

	.legend ul {
		margin: 0;
		padding: 0.5rem;
		list-style: none;
		max-inline-size: 18rem;
		background: var(--background);
		color: var(--text);
		border: 1px solid var(--border);
	}

	li {
		display: flex;
		gap: 0.5rem;
		align-items: center;
		font-size: 0.875rem;
		line-height: 1.3;
	}

	li + li {
		margin-block-start: 0.375rem;
	}

	.swatch {
		display: inline-flex;
		flex: none;
		justify-content: center;
		align-items: center;
		inline-size: 1.5rem;
		block-size: 1.5rem;
	}
</style>
