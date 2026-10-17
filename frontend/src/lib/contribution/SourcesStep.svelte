<script lang="ts">
	import { recordHref } from '#lib/archive/records.ts';
	import { m } from '#lib/paraglide/messages.js';
	import * as api from './api';
	import { errorText } from './errors';
	import Field from './Field.svelte';
	import type { EditorState } from './state.svelte';
	import { ids } from './validate';

	/**
	 * The Sources step, optional (Contribution and moderation spec, Form structure): the
	 * Sources behind the Artwork, which a Claim in the Attribution or Creation step may
	 * cite. A Source is created here with the Artwork, never alone. A Source whose title
	 * is alike, or whose address is the same as an existing one, is shown without blocking.
	 */
	let { editor }: { editor: EditorState } = $props();
	const config = $derived(editor.config);
	const form = $derived(editor.form);
	let alike = $state<Record<string, api.NameCandidate[]>>({});

	function message(id: string) {
		const found = editor.errorAt(id);
		return found ? errorText(found.code, found.params) : null;
	}

	function add() {
		form.sources.push({
			key: editor.newKey('source'),
			title: '',
			author: '',
			publication: '',
			url: '',
			note: ''
		});
	}

	async function check(key: string) {
		const source = form.sources.find((each) => each.key === key);
		if (!source?.title.trim()) return;
		const found = await api.nameCandidates('source', source.title, source.url);
		if (!found.ok) return;
		alike[key] = found.value.candidates;
		if (found.value.candidates.length > 0) {
			editor.announce(
				m.editor_alike_announcement({ count: found.value.candidates.length, name: source.title })
			);
		}
	}
</script>

<div class="step">
	<p>{m.editor_sources_intro()}</p>

	{#if form.sources.length > 0}
		<ol class="items" aria-label={m.editor_sources_list()}>
			{#each form.sources as source, index (source.key)}
				{@const id = (field: string) => ids.source(source.key, field)}
				<li>
					<fieldset class="item">
						<legend>{m.editor_sources_item({ number: index + 1 })}</legend>
						<Field id={id('title')} label={m.editor_sources_title()} error={message(id('title'))}>
							{#snippet children(props)}
								<input
									{...props}
									type="text"
									lang={config.contentLanguage}
									autocomplete="off"
									bind:value={source.title}
									onblur={() => check(source.key)}
								/>
							{/snippet}
						</Field>
						<Field id={id('author')} label={m.editor_sources_author()}>
							{#snippet children(props)}
								<input
									{...props}
									type="text"
									lang={config.contentLanguage}
									autocomplete="off"
									bind:value={source.author}
								/>
							{/snippet}
						</Field>
						<Field id={id('publication')} label={m.editor_sources_publication()}>
							{#snippet children(props)}
								<input
									{...props}
									type="text"
									lang={config.contentLanguage}
									autocomplete="off"
									bind:value={source.publication}
								/>
							{/snippet}
						</Field>
						<Field id={id('url')} label={m.editor_sources_url()} error={message(id('url'))}>
							{#snippet children(props)}
								<input
									{...props}
									type="url"
									inputmode="url"
									autocomplete="off"
									bind:value={source.url}
									onblur={() => check(source.key)}
								/>
							{/snippet}
						</Field>
						<Field id={id('note')} label={m.editor_sources_note()}>
							{#snippet children(props)}
								<textarea {...props} rows="2" lang={config.contentLanguage} bind:value={source.note}
								></textarea>
							{/snippet}
						</Field>

						{#if alike[source.key]?.length}
							<section class="alike" aria-label={m.editor_alike_title()}>
								<h3>{m.editor_alike_title()}</h3>
								<p>{m.editor_alike_source_intro()}</p>
								<ul>
									{#each alike[source.key] as candidate (candidate.record.id)}
										<li>
											<a
												href={recordHref('source', candidate.record.path, config.locale)}
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

						<button type="button" onclick={() => editor.removeSource(source.key)}>
							{m.editor_sources_remove({ number: index + 1 })}
						</button>
					</fieldset>
				</li>
			{/each}
		</ol>
	{/if}

	<button id="editor-sources-add" type="button" onclick={add}>{m.editor_sources_add()}</button>
</div>

<style>
	.step {
		display: grid;
		gap: 1.25rem;
		justify-items: start;
	}

	.step > p {
		margin: 0;
		max-inline-size: var(--measure);
	}

	.items {
		display: grid;
		gap: 1rem;
		list-style: none;
		margin: 0;
		padding: 0;
		inline-size: 100%;
	}

	.item {
		display: grid;
		gap: 1rem;
		justify-items: start;
		border: 1px solid var(--border);
		margin: 0;
		padding: 1rem;
	}

	.item legend {
		font-weight: 600;
	}

	.alike {
		display: grid;
		gap: 0.5rem;
		border: 1px solid var(--border);
		padding: 0.75rem;
	}

	.alike > * {
		margin: 0;
	}

	button {
		min-block-size: 2.75rem;
		padding-inline: 0.75rem;
		background: var(--background);
		color: var(--text);
		border: 1px solid var(--border);
		cursor: pointer;
	}
</style>
