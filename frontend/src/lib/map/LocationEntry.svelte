<script lang="ts">
	import { onMount } from 'svelte';
	import { m } from '#lib/paraglide/messages.js';
	import type { Bounds } from './bounds';
	import { insideBounds, parseInInstance, type Point } from './coordinates';
	import {
		addVertex,
		finish,
		fromGeometry,
		geometry,
		startDrawing,
		type Drawing,
		type Geometry,
		type Shape
	} from './drawing';
	import DrawingTool from './DrawingTool.svelte';
	import type { View } from './engine';
	import { describePoint, parseRadius } from './location-entry';
	import { supportsWebGL2 } from './webgl';

	/**
	 * The Location step's way in (Discovery spec, Location entry without the map):
	 * a coordinates field that is always there, the device position with its
	 * reminder, a text list of existing Locations, and, when the map works, drawing
	 * a point, a line, or an area. Without the map only a point can be entered.
	 * The parent owns the rest of the step (the duplicate warning is computed on the
	 * server from `onchange`'s value and handed back as `duplicates`).
	 */
	export interface LocationOption {
		id: string;
		title: string;
		description?: string;
	}

	export type Chosen =
		| { kind: 'existing'; location: LocationOption }
		| { kind: 'new'; geometry: Geometry; radiusMetres: number | null };

	let {
		locale,
		boundary,
		view,
		attribution,
		useMap = true,
		area = null,
		findLocations,
		duplicates = [],
		fieldId,
		initial = null,
		suggested = null,
		radiusProblem = null,
		problem = null,
		onchange
	}: {
		locale: string;
		/** The bounding box of the Instance boundary; the server applies the polygon. */
		boundary: Bounds;
		view: View;
		attribution: readonly { text: string; url: string }[];
		/** False to skip the map, as when the Operator disabled it. */
		useMap?: boolean;
		/** The Area the entered point falls in, once the server has said. */
		area?: string | null;
		/** Searches existing Locations by Site, Area, or text, or near a point. */
		findLocations: (query: { text?: string; near?: Point }) => Promise<LocationOption[]>;
		/** Similar Locations the server found, each with where to add documentation. */
		duplicates?: readonly { title: string; href: string; documentationHref: string }[];
		/** A prefix for the ids of the fields, so that an error summary can link to them. */
		fieldId?: string;
		/** What was chosen before, when the entry opens again on a draft. */
		initial?: Chosen | null;
		/**
		 * A position the file's metadata suggests (longitude, latitude). It only prefills
		 * the coordinates field with a notice: nothing is placed until the person does.
		 */
		suggested?: Point | null;
		/** Why the radius cannot be used with the rest of the Location, in words. */
		radiusProblem?: string | null;
		/** Why nothing has been placed yet, in words, once the person tried to go on. */
		problem?: string | null;
		onchange: (chosen: Chosen | null) => void;
	} = $props();

	const generatedId = $props.id();
	const id = $derived(fieldId ?? generatedId);
	// The map exists only with JavaScript and WebGL2; a style that fails to load
	// or a missing tile extract takes it away again (`onunavailable`).
	let mapAvailable = $state(false);
	let mounted = $state(false);
	onMount(() => {
		mapAvailable = useMap && supportsWebGL2();
		mounted = true;
	});

	// The entry opens on what was chosen before; later changes of `initial` are echoes of its own.
	// svelte-ignore state_referenced_locally
	const first = initial?.kind === 'new' ? initial.geometry : null;
	let shape = $state<Shape>(
		first
			? first.type === 'Point'
				? 'point'
				: first.type === 'LineString'
					? 'line'
					: 'polygon'
			: 'point'
	);
	// Until the page has mounted the shape is the one the draft had; after, without the map, a point.
	const effectiveShape = $derived<Shape>(!mounted || mapAvailable ? shape : 'point');
	let drawing = $state<Drawing>(first ? fromGeometry(first) : startDrawing('point'));
	// A change of shape starts a new drawing.
	$effect(() => {
		if (drawing.shape !== effectiveShape) drawing = startDrawing(effectiveShape);
	});

	let text = $state('');
	let coordinatesError = $state<string | null>(null);
	let confirmed = $state<Point | null>(null);
	// svelte-ignore state_referenced_locally
	let radiusText = $state(
		initial?.kind === 'new' && initial.radiusMetres !== null ? String(initial.radiusMetres) : ''
	);
	let positionError = $state<string | null>(null);
	let searchText = $state('');
	let results = $state<LocationOption[] | null>(null);
	// svelte-ignore state_referenced_locally
	let existing = $state<LocationOption | null>(
		initial?.kind === 'existing' ? initial.location : null
	);
	let suggestionShown = $state(false);

	// A suggested position only fills the field in; the person places it, or does not.
	$effect(() => {
		if (suggested && text === '' && !confirmed && !existing) {
			text = `${suggested[1].toFixed(6)}, ${suggested[0].toFixed(6)}`;
			suggestionShown = true;
		}
	});

	const radius = $derived(parseRadius(radiusText));
	const confirmation = $derived.by(() => {
		if (!confirmed) return null;
		const { latitude, longitude } = describePoint(confirmed, locale);
		return area
			? m.location_entry_confirm_area({ latitude, longitude, area })
			: m.location_entry_confirm({ latitude, longitude });
	});

	const coordinatesErrors: Record<string, () => string> = {
		empty: m.location_entry_error_empty,
		unrecognised: m.location_entry_error_unrecognised,
		short_link: m.location_entry_error_short_link,
		out_of_range: m.location_entry_error_out_of_range,
		outside_boundary: m.location_entry_error_outside_boundary
	};

	/** A point from the field or the device: the point itself, or one more vertex. */
	function place(point: Point) {
		existing = null;
		confirmed = point;
		if (!insideBounds(point, boundary)) return;
		const next = addVertex(drawing, point, boundary);
		drawing = effectiveShape === 'point' ? finish(next) : next;
	}

	function useCoordinates() {
		const parsed = parseInInstance(text, boundary);
		if ('error' in parsed) {
			confirmed = null;
			coordinatesError = coordinatesErrors[parsed.error]();
			return;
		}
		coordinatesError = null;
		place(parsed.point);
	}

	function usePosition() {
		positionError = null;
		if (!('geolocation' in navigator)) {
			positionError = m.location_entry_position_unavailable();
			return;
		}
		// The position is used once, here, and kept nowhere.
		navigator.geolocation.getCurrentPosition(
			({ coords }) => {
				const point: Point = [coords.longitude, coords.latitude];
				if (!insideBounds(point, boundary)) {
					positionError = m.location_entry_error_outside_boundary();
					return;
				}
				text = `${coords.latitude.toFixed(6)}, ${coords.longitude.toFixed(6)}`;
				coordinatesError = null;
				place(point);
			},
			(failure) => {
				positionError =
					failure.code === failure.PERMISSION_DENIED
						? m.location_entry_position_denied()
						: m.location_entry_position_unavailable();
			},
			{ enableHighAccuracy: true, timeout: 20_000, maximumAge: 0 }
		);
	}

	async function search(near?: Point) {
		results = await findLocations(near ? { near } : { text: searchText });
	}

	function choose(location: LocationOption) {
		existing = location;
		results = null;
	}

	// What the parent receives: an existing Location, or a finished new geometry.
	const chosen = $derived.by((): Chosen | null => {
		if (existing) return { kind: 'existing', location: existing };
		const shapeOut = geometry(drawing);
		if (!shapeOut || 'error' in radius) return null;
		return { kind: 'new', geometry: shapeOut, radiusMetres: radius.metres };
	});
	$effect(() => onchange(chosen));

	function onkeydown(event: KeyboardEvent) {
		// Enter confirms the field; it does not submit the Submission form around it.
		if (event.key === 'Enter') {
			event.preventDefault();
			useCoordinates();
		}
	}
</script>

<section class="entry" aria-labelledby="{id}-title">
	<h2 id="{id}-title">{m.location_entry_title()}</h2>

	{#if existing}
		<p>{m.location_entry_chosen({ title: existing.title })}</p>
		<button type="button" onclick={() => (existing = null)}>{m.location_entry_clear()}</button>
	{:else}
		{#if mapAvailable}
			<fieldset class="shape">
				<legend>{m.draw_shape_legend()}</legend>
				{#each ['point', 'line', 'polygon'] as const as option (option)}
					<label>
						<input type="radio" name="{id}-shape" value={option} bind:group={shape} />
						{option === 'point'
							? m.draw_shape_point()
							: option === 'line'
								? m.draw_shape_line()
								: m.draw_shape_polygon()}
					</label>
				{/each}
			</fieldset>
		{:else}
			<p class="notice">{m.location_entry_no_map()}</p>
		{/if}

		<div class="field">
			<label for="{id}-coordinates">{m.location_entry_coordinates_label()}</label>
			<p id="{id}-coordinates-hint" class="hint">{m.location_entry_coordinates_hint()}</p>
			<div class="row">
				<input
					id="{id}-coordinates"
					type="text"
					inputmode="text"
					autocomplete="off"
					spellcheck="false"
					bind:value={text}
					{onkeydown}
					aria-describedby="{id}-coordinates-hint {id}-coordinates-message"
					aria-invalid={coordinatesError || problem ? 'true' : undefined}
				/>
				<button type="button" onclick={useCoordinates}>{m.location_entry_coordinates_use()}</button>
			</div>
			{#if suggestionShown && !confirmed}
				<p class="notice">{m.location_entry_suggestion()}</p>
			{/if}
			<p id="{id}-coordinates-message" class="message" role="status">
				{coordinatesError ?? problem ?? confirmation ?? ''}
			</p>
		</div>

		<div class="field">
			<button type="button" onclick={usePosition}>{m.location_entry_position_use()}</button>
			<p class="hint">{m.location_entry_position_reminder()}</p>
			{#if positionError}<p class="message" role="alert">{positionError}</p>{/if}
		</div>

		{#if mapAvailable}
			<DrawingTool
				{drawing}
				ondrawing={(next) => (drawing = next)}
				{view}
				{boundary}
				inside={boundary}
				{attribution}
				onunavailable={() => (mapAvailable = false)}
			/>
		{/if}

		<div class="field">
			<label for="{id}-radius">{m.location_entry_radius_label()}</label>
			<p id="{id}-radius-hint" class="hint">{m.location_entry_radius_hint()}</p>
			<input
				id="{id}-radius"
				type="text"
				inputmode="numeric"
				autocomplete="off"
				bind:value={radiusText}
				aria-describedby="{id}-radius-hint {id}-radius-error"
				aria-invalid={'error' in radius || radiusProblem ? 'true' : undefined}
			/>
			<p id="{id}-radius-error" class="message">
				{'error' in radius ? m.location_entry_radius_error() : (radiusProblem ?? '')}
			</p>
		</div>

		{#if duplicates.length > 0}
			<section aria-labelledby="{id}-duplicates">
				<h3 id="{id}-duplicates">{m.location_entry_duplicates()}</h3>
				<ul>
					{#each duplicates as duplicate (duplicate.href)}
						<li>
							<a href={duplicate.href}>{duplicate.title}</a>
							<a href={duplicate.documentationHref}>
								{m.location_entry_duplicate_documentation({ title: duplicate.title })}
							</a>
						</li>
					{/each}
				</ul>
			</section>
		{/if}

		<fieldset class="existing">
			<legend>{m.location_entry_existing_legend()}</legend>
			<label for="{id}-search">{m.location_entry_search_label()}</label>
			<div class="row">
				<input
					id="{id}-search"
					type="search"
					autocomplete="off"
					bind:value={searchText}
					onkeydown={(event) => {
						if (event.key === 'Enter') {
							event.preventDefault();
							search();
						}
					}}
				/>
				<button type="button" onclick={() => search()}>{m.location_entry_search()}</button>
				<button type="button" onclick={() => search(confirmed ?? undefined)} disabled={!confirmed}>
					{m.location_entry_search_near()}
				</button>
			</div>
			{#if results}
				<div role="status">
					{#if results.length === 0}
						<p>{m.location_entry_no_results()}</p>
					{:else}
						<ul aria-label={m.location_entry_results()}>
							{#each results as location (location.id)}
								<li>
									<button
										type="button"
										aria-label={m.location_entry_choose({ title: location.title })}
										onclick={() => choose(location)}
									>
										{location.title}
									</button>
									{#if location.description}<span>{location.description}</span>{/if}
								</li>
							{/each}
						</ul>
					{/if}
				</div>
			{/if}
		</fieldset>
	{/if}
</section>

<style>
	.entry,
	.field {
		display: grid;
		gap: 0.5rem;
	}

	.entry {
		gap: 1.25rem;
	}

	.hint,
	.message,
	.notice {
		margin: 0;
	}

	.message:empty {
		display: none;
	}

	.row {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
	}

	.row input {
		flex: 1 1 14rem;
	}

	.shape {
		display: flex;
		flex-wrap: wrap;
		gap: 0.25rem 1.5rem;
		border: 0;
		margin: 0;
		padding: 0;
	}

	input[type='text'],
	input[type='search'] {
		min-block-size: 2.75rem;
		padding-inline: 0.5rem;
		background: var(--background);
		color: var(--text);
		border: 1px solid var(--border);
	}

	button {
		min-block-size: 2.75rem;
		padding-inline: 0.75rem;
		background: var(--background);
		color: var(--text);
		border: 1px solid var(--border);
		cursor: pointer;
	}

	button:disabled {
		cursor: default;
		opacity: 0.6;
	}
</style>
