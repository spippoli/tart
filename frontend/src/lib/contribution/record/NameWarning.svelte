<script lang="ts">
	import { recordHref } from '#lib/archive/records.ts';
	import { m } from '#lib/paraglide/messages.js';
	import * as api from '../api';
	import type { RecordEditorState } from './state.svelte';

	/**
	 * The name rule's warning for a new Area or Artist (Contribution and moderation spec,
	 * Duplicate detection): when the name is alike to the name or an Alias of a record that
	 * exists, it says so and links to it. It never blocks; the person goes on.
	 */
	let { editor, kind, name }: { editor: RecordEditorState; kind: 'artist' | 'area'; name: string } =
		$props();
	let alike = $state<api.NameCandidate[]>([]);
	let checked = $state('');

	$effect(() => {
		const entered = name.trim();
		if (entered.length < 2 || entered === checked) return;
		const timer = setTimeout(async () => {
			const found = await api.nameCandidates(kind, entered);
			checked = entered;
			alike = found.ok ? found.value.candidates : [];
			if (alike.length > 0) {
				editor.announce(m.editor_alike_announcement({ count: alike.length, name: entered }));
			}
		}, 600);
		return () => clearTimeout(timer);
	});
</script>

{#if alike.length > 0 && checked === name.trim()}
	<section class="alike" aria-label={m.editor_alike_title()}>
		<h4>{m.editor_alike_title()}</h4>
		<p>{m.editor_alike_intro()}</p>
		<ul>
			{#each alike as candidate (candidate.record.id)}
				<li>
					<a
						href={recordHref(kind, candidate.record.path, editor.config.locale)}
						target="_blank"
						rel="noopener"
					>
						{candidate.record.name ?? candidate.matched}
						<span class="visually-hidden">{m.editor_new_tab()}</span>
					</a>
				</li>
			{/each}
		</ul>
	</section>
{/if}

<style>
	.alike {
		display: grid;
		gap: 0.5rem;
		border: 1px solid var(--border);
		padding: 0.75rem;
	}

	.alike > * {
		margin: 0;
	}
</style>
