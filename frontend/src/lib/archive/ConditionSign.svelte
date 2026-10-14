<script lang="ts">
	import Sign from '#lib/map/Sign.svelte';
	import type { Tokens } from '../map/style';
	import type { ConditionGroup } from './records';

	/**
	 * The sign of a Condition group (ADR 0015): solid, dashed, or dotted with a "?".
	 * Decorative: the Condition is always in words beside it; the accent that marks
	 * *disappeared* is redundant with the dashes.
	 */
	let { group }: { group: ConditionGroup } = $props();
	const tokens: Tokens = {
		'map.paper': 'transparent',
		'map.ink': 'currentColor',
		'marker.ink': 'currentColor',
		'map.label.district': 'currentColor',
		'marker.accent': 'currentColor'
	};
</script>

<span class="sign" class:disappeared={group === 'disappeared'}
	><Sign kind={group === 'present' ? 'present' : group} {tokens} size={14} /></span
>

<style>
	.sign {
		display: inline-flex;
		vertical-align: -0.1em;
		margin-inline-end: 0.35em;
	}
	.disappeared {
		color: var(--accent);
	}
</style>
