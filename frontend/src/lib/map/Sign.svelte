<script lang="ts">
	import { signShapes, SIGN_SIZE, type SignKind } from './signs';
	import type { Tokens } from './style';

	// One archive sign as SVG, decorative: its meaning is always given in words beside it.
	let {
		kind,
		tokens,
		size = SIGN_SIZE
	}: { kind: SignKind; tokens: Tokens; size?: number } = $props();
	const shapes = $derived(signShapes(kind, tokens, size));
</script>

<svg
	width={size}
	height={size}
	viewBox="0 0 {size} {size}"
	aria-hidden="true"
	focusable="false"
	data-sign={kind}
>
	{#each shapes as shape, index (index)}
		<path
			d={shape.d}
			fill={shape.fill ?? 'none'}
			stroke={shape.stroke ?? 'none'}
			stroke-width={shape.strokeWidth}
			stroke-dasharray={shape.dash?.join(' ')}
			stroke-linecap={shape.dash || !shape.fill ? 'round' : 'butt'}
		/>
	{/each}
</svg>
