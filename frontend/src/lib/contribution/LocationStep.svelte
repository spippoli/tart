<script lang="ts">
	import { vocabularyLabels } from '#lib/archive/records.ts';
	import type { Point } from '#lib/map/coordinates.ts';
	import LocationEntry, { type Chosen, type LocationOption } from '#lib/map/LocationEntry.svelte';
	import { m } from '#lib/paraglide/messages.js';
	import { errorText } from './errors';
	import Field from './Field.svelte';
	import { findLocations as find } from './find-locations';
	import Group from './Group.svelte';
	import DuplicateWarning from './DuplicateWarning.svelte';
	import { PLACE_DESCRIPTION_MAX } from './form';
	import { ids } from './validate';
	import type { EditorState } from './state.svelte';

	/**
	 * The Location step (Contribution and moderation spec, Location step): choose an
	 * existing Location or place a geometry (the map module's entry: clicks, crosshair,
	 * coordinates, current position), say whether it is exact or approximate, and read the
	 * duplicate warning. A position the files suggest only fills the coordinates field in.
	 */
	let { editor }: { editor: EditorState } = $props();
	const config = $derived(editor.config);
	const location = $derived(editor.form.location);
	const surfaceLabel = $derived(vocabularyLabels(config.surfaceTypes, config.locale));
	const surfaceTypes = $derived(config.surfaceTypes.filter((each) => !each.retired));

	const initial = $derived.by((): Chosen | null => {
		const { existing, geometry, radius } = location;
		if (existing) {
			return { kind: 'existing', location: { id: String(existing.id), title: existing.title } };
		}
		return geometry ? { kind: 'new', geometry, radiusMetres: radius } : null;
	});
	// The entry keeps its own state after it opens: on what the draft has, once per remount.

	function chosen(next: Chosen | null) {
		const place = editor.form.location;
		if (next === null) {
			if (place.existing || place.geometry) {
				place.existing = null;
				place.geometry = null;
				place.radius = null;
			}
		} else if (next.kind === 'existing') {
			const id = Number(next.location.id);
			if (place.existing?.id !== id || place.existing.title !== next.location.title) {
				place.existing = { id, title: next.location.title };
			}
			place.geometry = null;
			place.radius = null;
		} else {
			place.existing = null;
			if (JSON.stringify(place.geometry) !== JSON.stringify(next.geometry)) {
				place.geometry = next.geometry;
			}
			if (place.radius !== next.radiusMetres) place.radius = next.radiusMetres;
		}
	}

	const findLocations = (query: { text?: string; near?: Point }): Promise<LocationOption[]> =>
		find(query, surfaceLabel, config.locale);

	const radiusProblem = $derived(
		editor.errorAt(ids.radius) ? errorText(editor.errorAt(ids.radius)!.code) : null
	);
	const surfaceError = $derived(editor.errorAt(ids.surfaceType));
	const placeError = $derived(editor.errorAt(ids.placeDescription));
	const locationError = $derived(editor.errorAt(ids.coordinates));
</script>

<div class="step">
	{#key editor.entryVersion}
		<LocationEntry
			locale={config.locale}
			boundary={config.boundary}
			view={config.view}
			attribution={config.attribution}
			fieldId={ids.location}
			{initial}
			problem={locationError ? errorText(locationError.code, locationError.params) : null}
			suggested={editor.suggestedPoint}
			{radiusProblem}
			{findLocations}
			onchange={chosen}
		/>
	{/key}

	{#if location.existing}
		<p class="chosen">{m.editor_location_existing({ title: location.existing.title })}</p>
	{:else}
		<Group id="editor-approximate" legend={m.editor_location_precision_legend()} radiogroup>
			<label>
				<input
					type="radio"
					name="editor-approximate"
					value={false}
					bind:group={location.approximate}
				/>
				{m.editor_location_exact()}
			</label>
			<label>
				<input
					type="radio"
					name="editor-approximate"
					value={true}
					bind:group={location.approximate}
				/>
				{m.editor_location_approximate()}
			</label>
		</Group>

		<Field
			id={ids.surfaceType}
			label={m.editor_location_surface_type()}
			error={surfaceError ? errorText(surfaceError.code, surfaceError.params) : null}
		>
			{#snippet children(props)}
				<select {...props} bind:value={location.surfaceType}>
					<option value="">{m.editor_choose()}</option>
					{#each surfaceTypes as each (each.key)}
						<option value={each.key}>{surfaceLabel(each.key)}</option>
					{/each}
				</select>
			{/snippet}
		</Field>

		<Field
			id={ids.placeDescription}
			label={m.editor_location_place_description()}
			hint={m.editor_location_place_description_hint({ max: PLACE_DESCRIPTION_MAX })}
			error={placeError ? errorText(placeError.code, placeError.params) : null}
		>
			{#snippet children(props)}
				<input
					{...props}
					type="text"
					lang={config.contentLanguage}
					autocomplete="off"
					bind:value={location.placeDescription}
				/>
			{/snippet}
		</Field>
	{/if}

	<DuplicateWarning {editor} />
</div>

<style>
	.step {
		display: grid;
		gap: 1.5rem;
	}

	.chosen {
		margin: 0;
	}
</style>
