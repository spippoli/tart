<script lang="ts">
	import { conditionWord } from '#lib/archive/records.ts';
	import { m } from '#lib/paraglide/messages.js';
	import { emptyDate } from './date-field';
	import { errorText } from './errors';
	import Field from './Field.svelte';
	import Group from './Group.svelte';
	import {
		ALT_TEXT_MAX,
		CONDITION_GROUPS,
		MAX_UPLOADED,
		type Condition,
		type DocForm
	} from './form';
	import type { EditorState } from './state.svelte';
	import UncertainDateInput from './UncertainDateInput.svelte';
	import { ids } from './validate';

	/**
	 * The Documentation step (Contribution and moderation spec, Documentation step): files
	 * with their Observed date, Rights basis, Creator credit, licence and alt text, or a
	 * link; and the initial Condition, asked explicitly. The Observed date and the
	 * position of a photo are only ever suggestions.
	 */
	let { editor }: { editor: EditorState } = $props();
	const config = $derived(editor.config);
	const form = $derived(editor.form);
	/** The thumbnail repeats what the file's own fields say: no text alternative of its own. */
	const DECORATIVE = '';
	let link = $state('');
	const uploaded = $derived(form.documentation.filter((each) => each.medium !== 'link').length);

	const groupWords = {
		present: m.discovery_group_present,
		disappeared: m.discovery_group_disappeared,
		unknown: m.discovery_group_unknown
	};

	function chooseFiles(event: Event & { currentTarget: HTMLInputElement }) {
		const files = [...(event.currentTarget.files ?? [])];
		event.currentTarget.value = '';
		editor.addFiles(files);
	}

	function addLink() {
		const url = link.trim();
		if (!url) return;
		form.documentation.push({
			key: editor.newKey('doc'),
			medium: 'link',
			file: null,
			fileName: '',
			observed: emptyDate(),
			suggested: false,
			rightsBasis: '',
			creatorCredit: '',
			licence: '',
			originUrl: '',
			altText: '',
			url
		});
		link = '';
	}

	function message(id: string) {
		const found = editor.errorAt(id);
		return found ? errorText(found.code, found.params) : null;
	}

	/** The state of an upload in words. */
	function statusWords(item: DocForm): string {
		const status = editor.uploads[item.key];
		switch (status?.status) {
			case 'uploading':
				return m.editor_upload_uploading();
			case 'processing':
				return m.editor_upload_processing();
			case 'rejected':
				return m.editor_upload_rejected({ reason: errorText(status.error ?? 'unknown') });
			case 'deleted':
				return m.editor_upload_deleted();
			default:
				return m.editor_upload_ready();
		}
	}

	const conditionError = $derived(message(ids.condition));
</script>

<div class="step">
	<p>{m.editor_documentation_intro()}</p>
	<p class="notice">{m.editor_documentation_people()}</p>

	<Field
		id={ids.documentationAdd}
		label={m.editor_documentation_files()}
		hint={m.editor_documentation_files_hint({ max: MAX_UPLOADED })}
		error={message(ids.documentationAdd)}
	>
		{#snippet children(props)}
			<input
				{...props}
				type="file"
				multiple
				accept="image/*,.heic,.heif,.avif,application/pdf"
				onchange={chooseFiles}
			/>
		{/snippet}
	</Field>

	<div class="link-row">
		<Field id="editor-documentation-link" label={m.editor_documentation_link()}>
			{#snippet children(props)}
				<input
					{...props}
					type="url"
					inputmode="url"
					autocomplete="off"
					bind:value={link}
					onkeydown={(event) => {
						if (event.key === 'Enter') {
							event.preventDefault();
							addLink();
						}
					}}
				/>
			{/snippet}
		</Field>
		<button type="button" onclick={addLink}>{m.editor_documentation_link_add()}</button>
	</div>

	{#if form.documentation.length > 0}
		<ol class="items" aria-label={m.editor_documentation_list()}>
			{#each form.documentation as item, index (item.key)}
				{@const id = (field: string) => ids.doc(item.key, field)}
				<li>
					<fieldset class="item">
						<legend>
							{item.medium === 'link'
								? m.editor_documentation_item_link({ number: index + 1 })
								: m.editor_documentation_item_file({ number: index + 1, name: item.fileName })}
						</legend>

						{#if item.medium !== 'link'}
							<p id={id('file')} class="status" tabindex="-1">{statusWords(item)}</p>
							{#if message(id('file'))}
								<p id="{id('file')}-error" class="error">
									<strong>{m.editor_error_prefix()}</strong>
									{message(id('file'))}
								</p>
							{/if}
							{#if item.medium === 'image' && item.file && editor.uploads[item.key]?.status === 'ready'}
								<img
									class="preview"
									src="/api/media/{item.file}/thumbnail"
									alt={DECORATIVE}
									width="120"
									loading="lazy"
								/>
							{/if}
						{:else}
							<Field id={id('url')} label={m.editor_documentation_url()} error={message(id('url'))}>
								{#snippet children(props)}
									<input {...props} type="url" inputmode="url" bind:value={item.url} />
								{/snippet}
							</Field>
						{/if}

						<UncertainDateInput
							id={id('observed')}
							legend={m.editor_documentation_observed()}
							bind:value={item.observed}
							locale={config.locale}
							timeZone={config.timeZone}
							today={editor.today}
							error={message(id('observed')) ??
								message(`${id('observed')}-second`) ??
								message(`${id('observed')}-qualifier`)}
						/>
						{#if item.suggested}
							<p class="notice">{m.editor_documentation_observed_suggested()}</p>
						{/if}

						{#if item.medium !== 'link'}
							<Group
								id={id('rights')}
								legend={m.editor_documentation_rights()}
								error={message(id('rights'))}
								radiogroup
							>
								<label>
									<input
										id={id('rights')}
										type="radio"
										name={id('rights-basis')}
										value="own_work"
										bind:group={item.rightsBasis}
									/>
									{m.editor_documentation_rights_own()}
								</label>
								<label>
									<input
										type="radio"
										name={id('rights-basis')}
										value="third_party"
										bind:group={item.rightsBasis}
									/>
									{m.editor_documentation_rights_third_party()}
								</label>
							</Group>
							<p class="hint">{m.editor_documentation_rights_other()}</p>

							<Field
								id={id('credit')}
								label={item.rightsBasis === 'third_party'
									? m.editor_documentation_credit_third_party()
									: m.editor_documentation_credit()}
								error={message(id('credit'))}
							>
								{#snippet children(props)}
									<input
										{...props}
										type="text"
										autocomplete="off"
										bind:value={item.creatorCredit}
									/>
								{/snippet}
							</Field>

							<Field
								id={id('licence')}
								label={m.editor_documentation_licence()}
								hint={m.editor_documentation_licence_hint()}
								error={message(id('licence'))}
							>
								{#snippet children(props)}
									<select {...props} bind:value={item.licence}>
										{#each config.licences as licence (licence)}
											<option value={licence}>{licence}</option>
										{/each}
									</select>
								{/snippet}
							</Field>

							{#if item.rightsBasis === 'third_party'}
								<Field
									id={id('origin')}
									label={m.editor_documentation_origin()}
									error={message(id('origin'))}
								>
									{#snippet children(props)}
										<input
											{...props}
											type="url"
											inputmode="url"
											autocomplete="off"
											bind:value={item.originUrl}
										/>
									{/snippet}
								</Field>
							{/if}

							{#if item.medium === 'image'}
								<Field
									id={id('alt')}
									label={m.editor_documentation_alt()}
									hint={m.editor_documentation_alt_hint({ max: ALT_TEXT_MAX })}
									error={message(id('alt'))}
								>
									{#snippet children(props)}
										<textarea
											{...props}
											rows="2"
											lang={config.contentLanguage}
											bind:value={item.altText}></textarea>
									{/snippet}
								</Field>
							{/if}
						{/if}

						<button type="button" onclick={() => editor.removeDocumentation(item.key)}>
							{m.editor_documentation_remove({ number: index + 1 })}
						</button>
					</fieldset>
				</li>
			{/each}
		</ol>
		<p class="hint">{m.editor_documentation_count({ uploaded, max: MAX_UPLOADED })}</p>
	{/if}

	{#if editor.flavour === 'new'}
		<Field
			id={ids.condition}
			label={m.editor_condition_label()}
			hint={m.editor_condition_hint()}
			error={conditionError}
		>
			{#snippet children(props)}
				<select {...props} bind:value={form.initialCondition}>
					<option value="">{m.editor_choose()}</option>
					{#each CONDITION_GROUPS as group (group.group)}
						<optgroup label={groupWords[group.group]()}>
							{#each group.conditions as condition (condition)}
								<option value={condition}
									>{conditionWord(condition as Condition, config.locale)}</option
								>
							{/each}
						</optgroup>
					{/each}
				</select>
			{/snippet}
		</Field>
	{/if}
</div>

<style>
	.step {
		display: grid;
		gap: 1.25rem;
	}

	.step > p,
	.hint {
		margin: 0;
		max-inline-size: var(--measure);
	}

	.notice {
		border-inline-start: 4px solid var(--border);
		padding-inline-start: 0.5rem;
	}

	.hint {
		color: var(--text-muted);
	}

	.link-row {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
		align-items: end;
	}

	.items {
		display: grid;
		gap: 1rem;
		list-style: none;
		margin: 0;
		padding: 0;
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

	.status,
	.error {
		margin: 0;
	}

	.error {
		border-inline-start: 4px solid var(--accent, currentColor);
		padding-inline-start: 0.5rem;
	}

	.preview {
		max-inline-size: 120px;
		block-size: auto;
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
