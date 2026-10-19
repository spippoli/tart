<script lang="ts">
	import { onMount, tick, untrack } from 'svelte';
	import ChangeValue from '#lib/archive/ChangeValue.svelte';
	import { archiveContext } from '#lib/archive/context.svelte.ts';
	import RecordAnchor from '#lib/archive/RecordAnchor.svelte';
	import { archiveDate, kindWord, linkText, type ApiDate } from '#lib/archive/records.ts';
	import { licence } from '#lib/licences.ts';
	import { signInHref } from '#lib/auth/next.ts';
	import { formatWait } from '#lib/i18n/format.ts';
	import { m } from '#lib/paraglide/messages.js';
	import { localizeHref } from '#lib/paraglide/runtime.js';
	import * as api from '../api';
	import { errorText } from '../errors';
	import {
		chooseAttribution,
		chooseField,
		creationEvents,
		editAdded,
		addedItem,
		isKept,
		isRepointed,
		recordsOf,
		setKept,
		setRepointed,
		usesSourceAttribution,
		usesSourceField,
		type Entry,
		type Op
	} from './ops';
	import type { MergeConfig } from './types';

	/**
	 * The editor of a Merge, a Duplicate retirement, and an Unmerge (Contribution and
	 * moderation spec, Merge, Duplicate retirement, Unmerge; ADR 0018): a stepper that can
	 * be walked in any order, with autosave to the draft and validation on submit only. The
	 * draft is a changeset pre-filled by the API; each choice on the page is the presence of
	 * one of its operations (`ops.ts`), so what is saved is what is shown.
	 */
	let { config }: { config: MergeConfig } = $props();

	// The editor is made once, from what the page loaded; a draft does not change under it.
	/* svelte-ignore state_referenced_locally */
	const { review, submissionId: id, intent } = config;
	/* svelte-ignore state_referenced_locally */
	const initial: Op[] = structuredClone(config.operations);
	/* svelte-ignore state_referenced_locally */
	let operations = $state<Op[]>(structuredClone(config.operations));
	/* svelte-ignore state_referenced_locally */
	const records = recordsOf(config.operations) ?? {
		source: review.source.id,
		into: review.into.id
	};
	const context = archiveContext();
	/* svelte-ignore state_referenced_locally */
	const format = { locale: config.locale, timeZone: config.timeZone };

	type Step = 'which' | 'reconcile' | 'references' | 'separated' | 'pointing' | 'review';
	const STEPS: Record<typeof intent, Step[]> = {
		merge: ['which', 'reconcile', 'references', 'review'],
		retirement: ['which', 'review'],
		unmerge: ['separated', 'pointing', 'review']
	};
	const steps = STEPS[intent];
	let step = $state<Step>(steps[0]);
	const stepNames: Record<Step, () => string> = {
		which: intent === 'retirement' ? m.merge_step_which_items : m.merge_step_which_records,
		reconcile: m.merge_step_reconcile,
		references: m.merge_step_references,
		separated: m.merge_step_separated,
		pointing: m.merge_step_pointing,
		review: m.editor_step_review
	};
	const titles = {
		merge: m.merge_title_merge,
		retirement: m.merge_title_retirement,
		unmerge: m.merge_title_unmerge
	};
	const intros = {
		merge: m.merge_intro_merge,
		retirement: m.merge_intro_retirement,
		unmerge: m.merge_intro_unmerge
	};
	const position = $derived(steps.indexOf(step));

	let heading = $state<HTMLElement>();
	let summary = $state<HTMLElement>();
	async function go(next: Step) {
		step = next;
		await tick();
		heading?.focus();
	}

	const surface = (key: string) => context.surfaceType(key);
	const name = (link: typeof review.source) => linkText(link, surface, config.locale);
	const fieldLabel = (field: string) => {
		const message = (m as unknown as Record<string, () => string>)[`archive_field_${field}`];
		return message ? message() : field;
	};

	// ---- the choices ----

	const entries: Entry[] = review.items as Entry[];
	const collections = (list: Entry[]) => [...new Set(list.map((each) => each.collection))];
	const of = (list: Entry[], collection: string) =>
		list.filter((each) => each.collection === collection);
	const kept = (entry: Entry) => isKept(operations, records.into, entry);
	const keep = (entry: Entry, on: boolean) =>
		(operations = setKept(operations, records.into, entry, on));
	const creations = $derived(creationEvents(operations, records.into, entries));
	const added = $derived(
		operations.filter((op) => op.op === 'add' && op.target === records.into).length
	);
	const dropped = $derived(
		operations.filter((op) => op.op === 'remove' && op.target === records.into).length
	);
	const taken = $derived(
		operations.filter((op) => op.op === 'set' && op.target === records.into).length
	);
	const restored = $derived(
		review.references.filter((each) => isRepointed(operations, each.id)).length
	);
	const sourceEntries = (list: Entry[]) => list.filter((each) => each.origin === 'source');

	// ---- autosave ----

	type Save =
		| { kind: 'idle' }
		| { kind: 'saving' }
		| { kind: 'saved'; at: Date }
		| { kind: 'failed'; failure: api.Failure };
	/* svelte-ignore state_referenced_locally */
	let save = $state<Save>(
		config.lastAutosave ? { kind: 'saved', at: new Date(config.lastAutosave) } : { kind: 'idle' }
	);
	const copy = () => ({ ...config.rest, operations });
	const serialized = $derived(JSON.stringify(copy()));
	let saved = untrack(() => JSON.stringify(copy()));
	let timer: ReturnType<typeof setTimeout> | undefined;
	let queue: Promise<unknown> = Promise.resolve();

	const wait = (failure: api.Failure) =>
		failure.retryAfter !== undefined ? formatWait(failure.retryAfter, format) : '';

	function flush(): Promise<unknown> {
		queue = queue.then(async () => {
			const current = JSON.stringify(untrack(copy));
			if (current === saved) return;
			save = { kind: 'saving' };
			const out = await api.autosave(id, JSON.parse(current));
			if (out.ok) {
				saved = current;
				save = { kind: 'saved', at: new Date(out.value.last_autosave_at) };
			} else {
				save = { kind: 'failed', failure: out.failure };
			}
		});
		return queue;
	}

	$effect(() => {
		if (serialized === saved) return;
		clearTimeout(timer);
		timer = setTimeout(() => void flush(), 1000);
		return () => clearTimeout(timer);
	});

	const saveStatus = $derived.by(() => {
		switch (save.kind) {
			case 'saving':
				return m.editor_autosave_saving();
			case 'saved':
				return m.editor_autosave_saved({
					time: new Intl.DateTimeFormat(config.locale, {
						hour: '2-digit',
						minute: '2-digit',
						timeZone: config.timeZone
					}).format(save.at)
				});
			case 'failed':
				return m.editor_autosave_failed({
					reason: errorText(save.failure.code, { wait: wait(save.failure) })
				});
			default:
				return m.editor_autosave_idle();
		}
	});

	onMount(() => {
		const warn = (event: BeforeUnloadEvent) => {
			if (JSON.stringify(copy()) !== saved) event.preventDefault();
		};
		window.addEventListener('beforeunload', warn);
		return () => window.removeEventListener('beforeunload', warn);
	});

	/** A full page load, so that the next page reads the Submissions afresh. */
	function leave(path: string) {
		window.location.assign(localizeHref(path));
	}

	// ---- swap ----

	let swapError = $state<string | null>(null);
	async function swap() {
		swapError = null;
		const started = await api.startMerge(records.into, records.source);
		if (!started.ok) {
			swapError = errorText(started.failure.code);
			return;
		}
		await api.deleteDraft(id);
		saved = JSON.stringify(copy());
		leave(`/contributions/${started.value.id}/edit`);
	}

	// ---- submit ----

	let note = $state('');
	let termsAccepted = $state(false);
	let submitting = $state(false);
	let refused = $state<{ code: string; wait: string } | null>(null);
	let announcement = $state('');
	/* svelte-ignore state_referenced_locally */
	const terms = config.terms;

	async function submit() {
		refused = null;
		if (terms.acceptanceRequired && !termsAccepted) {
			refused = { code: 'terms.required', wait: '' };
			announcement = m.editor_summary_announcement({ count: 1 });
			await tick();
			summary?.focus();
			return;
		}
		submitting = true;
		const out = await api.submit(id, copy(), note, termsAccepted);
		submitting = false;
		if (out.ok) {
			saved = JSON.stringify(copy());
			leave(`/contributions/${id}`);
			return;
		}
		if (out.failure.status === 401) {
			window.location.href = signInHref(window.location);
			return;
		}
		refused = { code: out.failure.code, wait: wait(out.failure) };
		announcement = m.editor_summary_announcement({ count: 1 });
		await tick();
		summary?.focus();
	}

	let confirmingDelete = $state(false);
	let leaveError = $state<string | null>(null);

	async function exitLater() {
		clearTimeout(timer);
		await flush();
		if (save.kind === 'failed') return;
		saved = JSON.stringify(copy());
		leave('/account/contributions');
	}

	async function deleteDraft() {
		const out = await api.deleteDraft(id);
		if (!out.ok) {
			leaveError = errorText(out.failure.code);
			return;
		}
		saved = JSON.stringify(copy());
		leave('/account/contributions');
	}

	const stepState = (each: Step): 'complete' | 'to_fix' =>
		each === 'reconcile' && intent === 'merge' && creations > 1 ? 'to_fix' : 'complete';
	const stateWords = { complete: m.editor_state_complete, to_fix: m.editor_state_to_fix };

	const when = (date: unknown) => archiveDate(date as ApiDate, context.dates);
</script>

{#snippet recordCard(
	link: typeof review.source,
	title: string,
	detail: typeof config.details.source
)}
	<section class="card" aria-labelledby="card-{link.id}">
		<h3 id="card-{link.id}">{title}</h3>
		<p>
			<RecordAnchor {link} />
			<span class="number">({m.merge_record_number({ number: link.id })})</span>
		</p>
		{#if detail}
			<dl>
				<dt>{fieldLabel('observed_date')}</dt>
				<dd>{when(detail.observed_date)}</dd>
				{#if detail.creator_credit}
					<dt>{fieldLabel('creator_credit')}</dt>
					<dd>{detail.creator_credit}</dd>
				{/if}
				{#if detail.licence}
					<dt>{fieldLabel('licence')}</dt>
					<dd>{licence(detail.licence, config.locale).label}</dd>
				{/if}
				{#if detail.alt_text}
					<dt>{fieldLabel('alt_text')}</dt>
					<dd>{detail.alt_text}</dd>
				{/if}
			</dl>
		{/if}
	</section>
{/snippet}

{#snippet item(entry: Entry, label: string)}
	<ChangeValue field={entry.collection} value={entry.item} records={review.records} />
	<span class="origin">({label})</span>
{/snippet}

<div class="editor">
	<h1>{titles[intent]()}</h1>
	<p>{intros[intent]()}</p>
	<p class="status" role="status">{saveStatus}</p>
	<p class="visually-hidden" role="status">{announcement}</p>

	{#if refused}
		<section
			bind:this={summary}
			class="summary"
			role="alert"
			tabindex="-1"
			aria-labelledby="merge-summary-title"
		>
			<h2 id="merge-summary-title">{m.editor_summary_title({ count: 1 })}</h2>
			<p>{errorText(refused.code, { wait: refused.wait })}</p>
		</section>
	{/if}

	<nav aria-label={m.editor_steps()}>
		<ol class="steps">
			{#each steps as each, index (each)}
				<li>
					<button
						type="button"
						class="step-button"
						aria-current={step === each ? 'step' : undefined}
						onclick={() => go(each)}
					>
						<span class="number">{index + 1}.</span>
						<span class="name">{stepNames[each]()}</span>
						<span class="state">{stateWords[stepState(each)]()}</span>
					</button>
				</li>
			{/each}
		</ol>
	</nav>

	<section class="panel" aria-labelledby="merge-step-heading">
		<h2 id="merge-step-heading" tabindex="-1" bind:this={heading}>
			{m.editor_step_heading({
				number: position + 1,
				count: steps.length,
				name: stepNames[step]()
			})}
		</h2>

		{#if step === 'which'}
			<p>{intent === 'retirement' ? m.merge_which_retirement() : m.merge_which_merge()}</p>
			<div class="pair">
				{@render recordCard(
					review.source,
					intent === 'retirement' ? m.merge_retired_heading() : m.merge_folded_heading(),
					config.details.source
				)}
				{@render recordCard(
					review.into,
					intent === 'retirement' ? m.merge_kept_heading() : m.merge_surviving_heading(),
					config.details.into
				)}
			</div>
			<p>
				<button type="button" onclick={swap}>{m.merge_swap()}</button>
			</p>
			{#if swapError}<p class="error">{m.merge_swap_failed({ reason: swapError })}</p>{/if}
			{#if intent === 'retirement'}
				<section aria-labelledby="merge-moves">
					<h3 id="merge-moves">{m.merge_moves_heading()}</h3>
					<ul>
						<li>
							{m.merge_moves_artworks()}:
							{#if sourceEntries(of(entries, 'artworks')).length > 0}
								{#each sourceEntries(of(entries, 'artworks')) as entry, index (index)}{#if index > 0}{context.separator}{/if}<ChangeValue
										field="artworks"
										value={entry.item}
										records={review.records}
									/>{/each}
							{:else}
								{m.merge_moves_none()}
							{/if}
						</li>
						<li>
							{m.merge_moves_location()}:
							{#if operations.some((op) => op.op === 'set' && op.field === 'location')}
								<ChangeValue
									field="location"
									value={operations.find((op) => op.op === 'set' && op.field === 'location')?.value}
									records={review.records}
								/>
							{:else}
								{m.merge_moves_none()}
							{/if}
						</li>
						<li>
							{m.merge_moves_citations({
								count: review.references.length + review.references_hidden
							})}
						</li>
					</ul>
					<p>{m.merge_retire_not_reconciled()}</p>
				</section>
			{/if}
		{:else if step === 'reconcile'}
			<p>{m.merge_reconcile_intro()}</p>

			{#if review.contradictions.length > 0}
				<section class="contradictions" aria-labelledby="merge-contradictions">
					<h3 id="merge-contradictions">{m.merge_contradictions_heading()}</h3>
					<p>{m.merge_contradictions_hint()}</p>
					<ul>
						{#each review.contradictions as found, index (index)}
							<li>
								{#if found.kind === 'two_creation_events'}
									<strong>
										{creations > 1
											? m.merge_contradiction_two_creation()
											: m.merge_contradiction_two_creation_resolved()}
									</strong>
								{:else if found.kind === 'competing_attributions'}
									{@const artist = review.records[String(found.key)]}
									<fieldset>
										<legend>
											{m.merge_contradiction_attribution({
												artist: artist ? name(artist) : String(found.key)
											})}
										</legend>
										<label>
											<input
												type="radio"
												name="attribution-{found.key}"
												checked={!usesSourceAttribution(operations, records.into, found.key)}
												onchange={() =>
													(operations = chooseAttribution(
														operations,
														records.into,
														found.key,
														found.item,
														false
													))}
											/>
											{m.merge_attribution_keep()}
										</label>
										<label>
											<input
												type="radio"
												name="attribution-{found.key}"
												checked={usesSourceAttribution(operations, records.into, found.key)}
												onchange={() =>
													(operations = chooseAttribution(
														operations,
														records.into,
														found.key,
														found.item,
														true
													))}
											/>
											{m.merge_attribution_use()}
											<ChangeValue
												field="attributions"
												value={found.item}
												records={review.records}
											/>
										</label>
									</fieldset>
								{:else}
									<strong>{m.merge_contradiction_location()}</strong>
								{/if}
							</li>
						{/each}
					</ul>
				</section>
			{/if}

			{#if review.fields.length > 0}
				<section aria-labelledby="merge-fields">
					<h3 id="merge-fields">{m.merge_fields_heading()}</h3>
					{#each review.fields as difference (difference.name)}
						<fieldset>
							<legend>{fieldLabel(difference.name)}</legend>
							<label>
								<input
									type="radio"
									name="field-{difference.name}"
									checked={!usesSourceField(operations, records.into, difference.name)}
									onchange={() =>
										(operations = chooseField(
											operations,
											records.into,
											difference.name,
											difference.source,
											false
										))}
								/>
								{m.merge_field_keep()}:
								<ChangeValue
									field={difference.name}
									value={difference.into}
									records={review.records}
								/>
							</label>
							<label>
								<input
									type="radio"
									name="field-{difference.name}"
									checked={usesSourceField(operations, records.into, difference.name)}
									onchange={() =>
										(operations = chooseField(
											operations,
											records.into,
											difference.name,
											difference.source,
											true
										))}
								/>
								{m.merge_field_use()}:
								<ChangeValue
									field={difference.name}
									value={difference.source}
									records={review.records}
								/>
							</label>
						</fieldset>
					{/each}
				</section>
			{/if}

			<section aria-labelledby="merge-items">
				<h3 id="merge-items">{m.merge_items_heading()}</h3>
				{#if entries.length === 0}
					<p>{m.merge_items_none()}</p>
				{/if}
				{#each collections(entries) as collection (collection)}
					<fieldset>
						<legend>{fieldLabel(collection)}</legend>
						<ul class="choices">
							{#each of(entries, collection) as entry, index (index)}
								{@const inputId = `item-${collection}-${index}`}
								<li>
									<input
										id={inputId}
										type="checkbox"
										checked={kept(entry)}
										onchange={(event) => keep(entry, event.currentTarget.checked)}
									/>
									<label for={inputId}>
										{#if entry.origin === 'source' && typeof entry.item === 'string' && kept(entry)}
											<span class="visually-hidden"
												>{m.merge_alias_label()}: {entry.item as string}</span
											>
										{:else}
											{@render item(
												entry,
												entry.origin === 'source'
													? m.merge_item_from_source()
													: m.merge_item_from_into()
											)}
										{/if}
									</label>
									{#if entry.origin === 'source' && typeof entry.item === 'string' && kept(entry)}
										<input
											type="text"
											aria-label={m.merge_alias_label()}
											value={addedItem(operations, records.into, entry) as string}
											oninput={(event) =>
												(operations = editAdded(
													operations,
													records.into,
													entry,
													event.currentTarget.value
												))}
										/>
										<span class="origin">({m.merge_item_from_source()})</span>
									{/if}
								</li>
							{/each}
						</ul>
					</fieldset>
				{/each}
			</section>
		{:else if step === 'references'}
			<p>{m.merge_references_intro()}</p>
			<p>{m.merge_redirect_note()}</p>
			{@render referenceList()}
		{:else if step === 'separated'}
			<p>{m.merge_separated_intro()}</p>
			<fieldset>
				<legend>{m.merge_separated_from_heading()}</legend>
				{#if review.from_source.length === 0}<p>{m.merge_separated_none()}</p>{/if}
				<ul class="choices">
					{#each review.from_source as entry, index (index)}
						{@const inputId = `from-${index}`}
						<li>
							<input
								id={inputId}
								type="checkbox"
								checked={!kept(entry)}
								onchange={(event) => keep(entry, !event.currentTarget.checked)}
							/>
							<label for={inputId}>
								<span class="origin">{m.merge_remove()}:</span>
								<ChangeValue field={entry.collection} value={entry.item} records={review.records} />
								({fieldLabel(entry.collection)})
							</label>
						</li>
					{/each}
				</ul>
			</fieldset>
			{#if review.added_since.length > 0}
				<fieldset>
					<legend>{m.merge_separated_since_heading()}</legend>
					<p>{m.merge_separated_since_hint()}</p>
					<ul class="choices">
						{#each review.added_since as entry, index (index)}
							{@const inputId = `since-${index}`}
							<li>
								<input
									id={inputId}
									type="checkbox"
									checked={!kept(entry)}
									onchange={(event) => keep(entry, !event.currentTarget.checked)}
								/>
								<label for={inputId}>
									<span class="origin">{m.merge_remove()}:</span>
									<ChangeValue
										field={entry.collection}
										value={entry.item}
										records={review.records}
									/>
									({fieldLabel(entry.collection)})
								</label>
							</li>
						{/each}
					</ul>
				</fieldset>
			{/if}
		{:else if step === 'pointing'}
			<p>{m.merge_pointing_intro()}</p>
			{#if review.references.length === 0}<p>{m.merge_pointing_none()}</p>{/if}
			<ul class="choices">
				{#each review.references as link (link.id)}
					{@const inputId = `point-${link.id}`}
					<li>
						<input
							id={inputId}
							type="checkbox"
							checked={isRepointed(operations, link.id)}
							onchange={(event) =>
								(operations = setRepointed(
									operations,
									initial,
									link.id,
									event.currentTarget.checked
								))}
						/>
						<label for={inputId}>
							<span class="origin">{m.merge_point_back()}:</span>
							{kindWord(link.kind, config.locale)}
							<RecordAnchor {link} />
						</label>
					</li>
				{/each}
			</ul>
			{#if review.skipped.length > 0}
				<p>{m.merge_pointing_skipped()}</p>
				<ul>
					{#each review.skipped as link (link.id)}
						<li>{kindWord(link.kind, config.locale)} <RecordAnchor {link} /></li>
					{/each}
				</ul>
			{/if}
		{:else}
			<p>
				{(intent === 'merge'
					? m.merge_review_merge
					: intent === 'retirement'
						? m.merge_review_retirement
						: m.merge_review_unmerge)({
					source: name(review.source),
					into: name(review.into)
				})}
			</p>
			<p>
				{#if intent === 'unmerge'}
					{m.merge_review_unmerge_counts({ removed: dropped, restored })}
				{:else}
					{m.merge_review_counts({
						added,
						dropped,
						fields: taken,
						references: review.references.length + review.references_hidden
					})}
				{/if}
			</p>
			{#if intent === 'merge' && creations > 1}
				<p class="error">{errorText('artwork.creation_event_duplicated')}</p>
			{/if}

			<div class="field">
				<label for="merge-note">{m.editor_review_note()}</label>
				<p class="hint">{m.editor_review_note_hint()}</p>
				<textarea id="merge-note" rows="3" bind:value={note}></textarea>
			</div>

			{#if terms.acceptanceRequired}
				<div class="terms">
					<label>
						<input type="checkbox" bind:checked={termsAccepted} />
						<span>
							{m.editor_review_accept()}
							<a href={localizeHref('/about/terms')} target="_blank" rel="noopener">
								{m.editor_review_terms({ version: terms.version })}
								<span class="visually-hidden">{m.editor_new_tab()}</span>
							</a>
						</span>
					</label>
					<p class="hint">{m.editor_review_accept_hint()}</p>
				</div>
			{:else}
				<p>
					{m.editor_review_accepted({ version: terms.acceptedVersion ?? terms.version })}
					<a href={localizeHref('/about/terms')} target="_blank" rel="noopener">
						{m.editor_review_read_terms()}
						<span class="visually-hidden">{m.editor_new_tab()}</span>
					</a>
				</p>
			{/if}

			<p>
				<button type="button" class="primary" onclick={submit} disabled={submitting}>
					{submitting ? m.editor_submitting() : m.editor_submit()}
				</button>
			</p>
		{/if}
	</section>

	<div class="movement">
		<button type="button" disabled={position === 0} onclick={() => go(steps[position - 1])}>
			{m.editor_previous()}
		</button>
		<button
			type="button"
			disabled={position === steps.length - 1}
			onclick={() => go(steps[position + 1])}
		>
			{m.editor_next()}
		</button>
	</div>

	<div class="leave">
		<button type="button" onclick={exitLater}>{m.editor_exit()}</button>
		{#if confirmingDelete}
			<span class="confirm" role="group" aria-label={m.editor_delete_confirm_label()}>
				{m.editor_delete_confirm()}
				<button type="button" onclick={deleteDraft}>{m.editor_delete_yes()}</button>
				<button type="button" onclick={() => (confirmingDelete = false)}
					>{m.editor_delete_no()}</button
				>
			</span>
		{:else}
			<button type="button" onclick={() => (confirmingDelete = true)}>{m.editor_delete()}</button>
		{/if}
		{#if leaveError}<p class="error">{leaveError}</p>{/if}
	</div>
</div>

{#snippet referenceList()}
	{#if review.references.length === 0 && review.references_hidden === 0}
		<p>{m.merge_references_none()}</p>
	{:else}
		<p>
			{m.merge_references_count({ count: review.references.length + review.references_hidden })}
		</p>
		<ul>
			{#each review.references as link (link.id)}
				<li>{kindWord(link.kind, config.locale)} <RecordAnchor {link} /></li>
			{/each}
		</ul>
		{#if review.references_hidden > 0}
			<p>{m.merge_references_hidden({ count: review.references_hidden })}</p>
		{/if}
	{/if}
{/snippet}

<style>
	.editor {
		display: grid;
		gap: 1.25rem;
	}

	.editor > p,
	.editor h1 {
		margin: 0;
	}

	.status,
	.hint,
	.origin,
	.number {
		color: var(--text-muted);
	}

	.summary {
		border: 3px solid var(--text);
		padding: 0.75rem 1rem;
	}

	.summary h2,
	.summary p {
		margin: 0 0 0.5rem;
	}

	.steps {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
		list-style: none;
		margin: 0;
		padding: 0;
	}

	.step-button {
		display: grid;
		gap: 0.1rem;
		justify-items: start;
		text-align: start;
		min-inline-size: 7.5rem;
	}

	.step-button[aria-current='step'] {
		border: 3px solid var(--text);
		font-weight: 700;
	}

	.state {
		font-size: 0.85rem;
		color: var(--text-muted);
	}

	.panel {
		display: grid;
		gap: 1rem;
	}

	.panel h2,
	.panel h3 {
		margin: 0;
	}

	.pair {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr));
		gap: 1rem;
	}

	.card {
		border: 1px solid var(--border);
		padding: 0.75rem 1rem;
	}

	.card p {
		margin: 0.25rem 0;
	}

	dl {
		display: grid;
		grid-template-columns: max-content 1fr;
		gap: 0 1rem;
		margin: 0.5rem 0 0;
	}

	dt {
		color: var(--text-muted);
	}

	dd {
		margin: 0;
	}

	fieldset {
		border: 1px solid var(--border);
		margin: 0 0 0.75rem;
		display: grid;
		gap: 0.4rem;
	}

	.choices {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 0.5rem;
	}

	.choices li {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
		align-items: baseline;
	}

	.contradictions {
		border: 3px double var(--text);
		padding: 0.5rem 1rem;
	}

	.contradictions ul {
		margin: 0;
		padding: 0;
		list-style: none;
		display: grid;
		gap: 0.5rem;
	}

	.field,
	.terms {
		display: grid;
		gap: 0.35rem;
	}

	.hint {
		margin: 0;
	}

	.terms label {
		display: flex;
		gap: 0.5rem;
		align-items: baseline;
		font-weight: 600;
	}

	.error {
		margin: 0;
		border-inline-start: 4px solid var(--accent, currentColor);
		padding-inline-start: 0.5rem;
	}

	.movement,
	.leave {
		display: flex;
		flex-wrap: wrap;
		gap: 0.75rem;
		align-items: center;
	}

	.leave {
		border-block-start: 1px solid var(--border);
		padding-block-start: 1rem;
	}

	.confirm {
		display: inline-flex;
		flex-wrap: wrap;
		gap: 0.5rem;
		align-items: center;
	}

	button {
		min-block-size: 2.75rem;
		padding: 0.25rem 0.75rem;
		background: var(--background);
		color: var(--text);
		border: 1px solid var(--border);
		cursor: pointer;
	}

	.primary {
		font-weight: 600;
		border: 2px solid var(--text);
	}

	button:disabled {
		cursor: default;
		opacity: 0.6;
	}

	input[type='text'],
	textarea {
		font: inherit;
		min-block-size: 2.75rem;
		padding: 0.25rem 0.5rem;
		background: var(--background);
		color: var(--text);
		border: 1px solid var(--border);
	}
</style>
