<script lang="ts">
	import { vocabularyLabels } from '#lib/archive/records.ts';
	import type { Geometry } from '#lib/map/drawing.ts';
	import { m } from '#lib/paraglide/messages.js';
	import type { DateField } from '../date-field';
	import { errorText } from '../errors';
	import Field from '../Field.svelte';
	import Group from '../Group.svelte';
	import UncertainDateInput from '../UncertainDateInput.svelte';
	import GeometryField from './GeometryField.svelte';
	import LocationPicker from './LocationPicker.svelte';
	import SiteField from './SiteField.svelte';
	import type { FieldValue, PeriodField, PickedLocation, SiteValue, TitleValue } from './form';
	import type { FieldSpec } from './spec';
	import type { RecordEditorState } from './state.svelte';
	import { ids } from './validate';

	/**
	 * The control of one field of a record, by its type (Contribution and moderation spec,
	 * Other editors). Free text is archive content in the Content language; vocabulary
	 * values that are retired are not offered in a new Submission (ADR 0009). The value is
	 * the editor's `form.fields[name]`, set before this control is shown.
	 */
	let {
		editor,
		spec,
		label
	}: {
		editor: RecordEditorState;
		spec: FieldSpec;
		label: string;
	} = $props();

	const config = $derived(editor.config);
	const id = $derived(ids.field(spec.name));
	const found = $derived(editor.errorAt(id));
	const error = $derived(found ? errorText(found.code, found.params) : null);
	const lang = $derived(spec.content ? config.contentLanguage : undefined);
	const surfaceTypes = $derived(config.surfaceTypes.filter((each) => !each.retired));
	const expressionTypes = $derived(config.expressionTypes.filter((each) => !each.retired));
	const surfaceLabel = $derived(vocabularyLabels(config.surfaceTypes, config.locale));
	const typeLabel = $derived(vocabularyLabels(config.expressionTypes, config.locale));

	/** The value of the field, as the type of the control says. */
	function get<T extends FieldValue>(): T {
		return editor.form.fields[spec.name] as T;
	}
	function set(next: FieldValue) {
		editor.form.fields[spec.name] = next;
	}

	const title = $derived(spec.type === 'title' ? get<TitleValue>() : null);
	const period = $derived(spec.type === 'period' ? get<PeriodField>() : null);

	function messageAt(...names: string[]) {
		for (const name of names) {
			const at = editor.errorAt(name);
			if (at) return errorText(at.code, at.params);
		}
		return null;
	}

	function toggle(key: string, on: boolean) {
		const chosen = get<string[]>();
		set(on ? [...chosen, key] : chosen.filter((each) => each !== key));
	}
</script>

{#if spec.type === 'text' || spec.type === 'oneline' || spec.type === 'language'}
	<Field {id} {label} {error} {lang}>
		{#snippet children(props)}
			<input
				{...props}
				type={spec.name === 'url' ? 'url' : 'text'}
				{lang}
				autocomplete="off"
				maxlength={spec.type === 'language' ? 12 : undefined}
				bind:value={() => get<string>(), set}
			/>
		{/snippet}
	</Field>
{:else if spec.type === 'multiline'}
	<Field
		{id}
		{label}
		{error}
		hint={spec.name === 'alt_text' ? m.editor_documentation_alt_hint({ max: 250 }) : undefined}
		{lang}
	>
		{#snippet children(props)}
			<textarea {...props} rows="4" {lang} bind:value={() => get<string>(), set}></textarea>
		{/snippet}
	</Field>
{:else if title}
	<Field {id} {label} {error}>
		{#snippet children(props)}
			<input
				{...props}
				type="text"
				lang={config.contentLanguage}
				autocomplete="off"
				disabled={title.untitled}
				bind:value={title.text}
			/>
		{/snippet}
	</Field>
	<label class="check">
		<input
			type="checkbox"
			bind:checked={title.untitled}
			onchange={() => {
				if (title.untitled) title.text = '';
			}}
		/>
		{m.editor_artwork_untitled()}
	</label>
{:else if spec.type === 'select'}
	<Field {id} {label} {error}>
		{#snippet children(props)}
			<select {...props} bind:value={() => get<string>(), set}>
				<option value="">{m.editor_choose()}</option>
				{#if spec.vocabulary === 'artist_kinds'}
					<option value="individual">{m.archive_artist_individual()}</option>
					<option value="collective">{m.archive_artist_collective()}</option>
				{:else}
					{#each surfaceTypes as each (each.key)}
						<option value={each.key}>{surfaceLabel(each.key)}</option>
					{/each}
				{/if}
			</select>
		{/snippet}
	</Field>
{:else if spec.type === 'choices'}
	<Group {id} legend={label} {error}>
		{#each expressionTypes as each, index (each.key)}
			<label>
				<input
					id={index === 0 ? id : undefined}
					type="checkbox"
					checked={get<string[]>().includes(each.key)}
					onchange={(event) => toggle(each.key, event.currentTarget.checked)}
				/>
				{typeLabel(each.key)}
			</label>
		{/each}
	</Group>
{:else if spec.type === 'approximate'}
	<Group {id} legend={label} {error} radiogroup>
		<label>
			<input
				{id}
				type="radio"
				name="{id}-choice"
				checked={get<boolean>() === false}
				onchange={() => set(false)}
			/>
			{m.editor_location_exact()}
		</label>
		<label>
			<input
				type="radio"
				name="{id}-choice"
				checked={get<boolean>() === true}
				onchange={() => set(true)}
			/>
			{m.editor_location_approximate()}
		</label>
	</Group>
{:else if spec.type === 'radius'}
	<Field {id} {label} {error} hint={m.location_entry_radius_hint()}>
		{#snippet children(props)}
			<input
				{...props}
				type="text"
				inputmode="numeric"
				autocomplete="off"
				bind:value={() => get<string>(), set}
			/>
		{/snippet}
	</Field>
{:else if spec.type === 'date'}
	<UncertainDateInput
		{id}
		legend={label}
		bind:value={() => get<DateField>(), set}
		locale={config.locale}
		timeZone={config.timeZone}
		today={editor.today}
		optional={spec.optional}
		error={messageAt(id, `${id}-second`, `${id}-qualifier`)}
	/>
{:else if period}
	<Group {id} legend={label} {error}>
		<UncertainDateInput
			id="{id}-start"
			legend={m.editor_period_start()}
			bind:value={period.start}
			locale={config.locale}
			timeZone={config.timeZone}
			today={editor.today}
			optional
			error={messageAt(`${id}-start`, `${id}-start-second`, `${id}-start-qualifier`)}
		/>
		<UncertainDateInput
			id="{id}-end"
			legend={m.editor_period_end()}
			bind:value={period.end}
			locale={config.locale}
			timeZone={config.timeZone}
			today={editor.today}
			optional
			error={messageAt(`${id}-end`, `${id}-end-second`, `${id}-end-qualifier`)}
		/>
	</Group>
{:else if spec.type === 'geometry'}
	<GeometryField
		{id}
		bind:value={() => get<Geometry | null>(), set}
		reference={editor.creating
			? null
			: ((config.current.geometry ?? null) as unknown as Geometry | null)}
		polygonOnly={spec.shape === 'polygon'}
		boundary={config.boundary}
		view={config.view}
		attribution={config.attribution}
		locale={config.locale}
		problem={error}
	/>
{:else if spec.type === 'site'}
	<SiteField {id} {editor} bind:value={() => get<SiteValue>(), set} />
{:else if spec.type === 'location'}
	<LocationPicker
		{id}
		bind:value={() => get<PickedLocation | null>(), set}
		locale={config.locale}
		surfaceTypes={config.surfaceTypes}
	/>
	{#if error}
		<p class="error"><strong>{m.editor_error_prefix()}</strong> {error}</p>
	{/if}
{/if}

<style>
	.check {
		display: flex;
		gap: 0.5rem;
		align-items: baseline;
	}

	.error {
		margin: 0;
		border-inline-start: 4px solid var(--accent, currentColor);
		padding-inline-start: 0.5rem;
	}
</style>
