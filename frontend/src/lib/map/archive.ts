/**
 * The archive's layers on the map (Discovery spec, The map: signs, stack, clusters,
 * geometries): the signs and clusters, the geometries from z17, the hatched
 * approximate areas, the district labels, and the focusable elements over them (a
 * canvas is invisible to the keyboard and to assistive technology, so each Location,
 * cluster, and Site label also has one element in the page). Part of the map module:
 * only `engine.ts` imports it.
 */
import { Marker, type GeoJSONSource, type Map as MapLibreMap } from 'maplibre-gl';
import { renderImage } from './canvas';
import {
	EMPTY_MAP_DATA,
	geometryFeatures,
	hatchFeatures,
	signFeatures,
	signImageName,
	type LocationProperties,
	type MapData
} from './locations';
import { HATCH_TILE, hatchTile, signImage, signShapes, type Group } from './signs';
import type { Style } from './style';

/** Clusters up to this zoom, none above (radius in screen pixels). */
export const CLUSTER_MAX_ZOOM = 16;
const CLUSTER_RADIUS = 50;
/** Lines and polygons are drawn from this zoom. */
const GEOMETRY_MIN_ZOOM = 17;
const HATCH_MIN_ZOOM = 15;
const SITE_MIN_ZOOM = 16;
/** A guard against a viewport crowded with elements: the nearest to the centre. */
const MAX_FOCUSABLE = 500;
const CLUSTER_SIZE = 28;

const SIGNS = 'tart-signs';
const GEOMETRIES = 'tart-geometries';
const HATCH = 'tart-hatch';
const AREAS = 'tart-areas';
const MUTED = 'tart-muted';
const OUTLINE = 'tart-outline';
const MUTED_SIZE = 8;
const GROUPS: readonly Group[] = ['present', 'unknown', 'disappeared'];

export interface ArchiveOptions {
	/** The accessible names, in the UI language. */
	describe: {
		sign: (properties: LocationProperties) => string;
		cluster: (artworks: number, locations: number) => string;
	};
	onSelect: (id: number) => void;
	/** Clusters nearby Locations up to z16; the mini-map does not. Defaults to true. */
	cluster?: boolean;
	/** Whether each Location and cluster in view is also a button; the mini-map has none. */
	focusable?: boolean;
}

export interface Archive {
	/** Adds the archive's sources, images, and layers to the current style. */
	install(style: Style): void;
	setData(data: MapData): void;
	setMuted(points: readonly (readonly [number, number])[]): void;
	setOutline(geometry: Outline | null): void;
	destroy(): void;
}

type Outline = { type: 'Polygon'; coordinates: number[][][] };

type Coordinates = [number, number];

interface Entry {
	key: string;
	at: Coordinates;
	label: string;
	/** The image of the sign it stands for, for tests and for styling. */
	sign: string;
	activate: () => void;
}

export function createArchive(map: MapLibreMap, options: ArchiveOptions): Archive {
	let data = EMPTY_MAP_DATA;
	let muted: readonly (readonly [number, number])[] = [];
	let outline: Outline | null = null;
	let installed = false;
	const markers = new Map<string, { marker: Marker; element: HTMLElement }>();
	const sites = new Map<number, Marker>();
	let frame = 0;

	function addImages(style: Style) {
		const tokens = style.metadata['tart:tokens'];
		const ratio = window.devicePixelRatio || 1;
		for (const group of GROUPS) {
			for (const stacked of [false, true]) {
				for (const small of [false, true]) {
					const image = signImage(group, tokens, { stacked, small });
					const name = `sign-${group}-${stacked ? 'stack' : 'single'}-${small ? 'small' : 'normal'}`;
					map.addImage(name, renderImage(image.size, image.size, image.parts, ratio), {
						pixelRatio: ratio
					});
				}
			}
		}
		map.addImage(
			'cluster',
			renderImage(
				CLUSTER_SIZE,
				CLUSTER_SIZE,
				[{ x: 0, y: 0, shapes: signShapes('cluster', tokens, CLUSTER_SIZE) }],
				ratio
			),
			{ pixelRatio: ratio }
		);
		// The neighbours of the mini-map: a smaller sign in a muted `map.ink`, one shape.
		const side = MUTED_SIZE;
		map.addImage(
			'muted',
			renderImage(
				side,
				side,
				[
					{ x: 0, y: 0, shapes: [{ d: `M0 0h${side}v${side}h${-side}Z`, fill: tokens['map.ink'] }] }
				],
				ratio
			),
			{ pixelRatio: ratio }
		);
		map.addImage(
			'hatch',
			renderImage(HATCH_TILE, HATCH_TILE, [{ x: 0, y: 0, shapes: hatchTile(tokens) }], ratio),
			{ pixelRatio: ratio }
		);
	}

	function install(style: Style) {
		const tokens = style.metadata['tart:tokens'];
		const before = style.metadata['tart:insert-archive-below'];
		addImages(style);
		const empty = { type: 'FeatureCollection' as const, features: [] };
		map.addSource(SIGNS, {
			type: 'geojson',
			data: empty,
			cluster: options.cluster ?? true,
			clusterRadius: CLUSTER_RADIUS,
			clusterMaxZoom: CLUSTER_MAX_ZOOM,
			clusterProperties: { artworks: ['+', ['get', 'count']] }
		});
		map.addSource(GEOMETRIES, { type: 'geojson', data: empty });
		map.addSource(HATCH, { type: 'geojson', data: empty });
		map.addSource(AREAS, { type: 'geojson', data: empty });
		map.addSource(MUTED, { type: 'geojson', data: empty });
		map.addSource(OUTLINE, { type: 'geojson', data: empty });

		map.addLayer(
			{
				id: OUTLINE,
				type: 'line',
				source: OUTLINE,
				paint: { 'line-color': tokens['map.ink'], 'line-width': 2, 'line-opacity': 0.7 }
			},
			before
		);
		map.addLayer(
			{
				id: MUTED,
				type: 'symbol',
				source: MUTED,
				layout: {
					'icon-image': 'muted',
					'icon-allow-overlap': true,
					'icon-ignore-placement': true
				},
				paint: { 'icon-opacity': 0.5 }
			},
			before
		);
		map.addLayer(
			{
				id: HATCH,
				type: 'fill',
				source: HATCH,
				minzoom: HATCH_MIN_ZOOM,
				paint: { 'fill-pattern': 'hatch', 'fill-antialias': false }
			},
			before
		);
		map.addLayer(
			{
				id: AREAS,
				type: 'symbol',
				source: AREAS,
				minzoom: 12,
				maxzoom: GEOMETRY_MIN_ZOOM,
				layout: {
					'text-field': ['get', 'name'],
					'text-font': ['Sorts Mill Goudy Regular'],
					'text-size': 14,
					'text-transform': 'uppercase',
					'text-letter-spacing': 0.2
				},
				paint: {
					'text-color': tokens['map.label.district'],
					'text-halo-color': tokens['map.paper'],
					'text-halo-width': 1.5
				}
			},
			before
		);
		// A wider, invisible line makes a drawn geometry easier to hit.
		map.addLayer(
			{
				id: `${GEOMETRIES}-hit`,
				type: 'line',
				source: GEOMETRIES,
				minzoom: GEOMETRY_MIN_ZOOM,
				paint: { 'line-color': tokens['marker.ink'], 'line-width': 16, 'line-opacity': 0 }
			},
			before
		);
		const dashes: Record<Group, number[] | undefined> = {
			present: undefined,
			disappeared: [3, 2],
			unknown: [1, 2]
		};
		for (const group of GROUPS) {
			map.addLayer(
				{
					id: `${GEOMETRIES}-${group}`,
					type: 'line',
					source: GEOMETRIES,
					minzoom: GEOMETRY_MIN_ZOOM,
					filter: ['==', ['get', 'group'], group],
					layout: { 'line-cap': dashes[group] ? 'round' : 'butt', 'line-join': 'round' },
					paint: {
						'line-color': tokens['marker.ink'],
						'line-width': 3,
						...(dashes[group] ? { 'line-dasharray': dashes[group] } : {})
					}
				},
				before
			);
		}
		map.addLayer(
			{
				id: `${SIGNS}-clusters`,
				type: 'symbol',
				source: SIGNS,
				filter: ['has', 'point_count'],
				layout: {
					'icon-image': 'cluster',
					'icon-allow-overlap': true,
					'icon-ignore-placement': true,
					'text-field': ['to-string', ['get', 'artworks']],
					'text-font': ['Noto Sans Regular'],
					'text-size': 12,
					'text-allow-overlap': true,
					'text-ignore-placement': true
				},
				paint: { 'text-color': tokens['map.ink'] }
			},
			before
		);
		map.addLayer(
			{
				id: `${SIGNS}-locations`,
				type: 'symbol',
				source: SIGNS,
				filter: ['!', ['has', 'point_count']],
				layout: {
					'icon-image': ['get', 'image'],
					'icon-allow-overlap': true,
					'icon-ignore-placement': true
				}
			},
			before
		);
		installed = true;
		setData(data);
		setMuted(muted);
		setOutline(outline);
	}

	function setData(next: MapData) {
		data = next;
		if (!installed) return;
		feed(SIGNS, signFeatures(data.locations));
		feed(GEOMETRIES, geometryFeatures(data.locations));
		feed(HATCH, hatchFeatures(data.locations));
		feed(
			AREAS,
			data.areas.map((area) => ({
				type: 'Feature',
				geometry: { type: 'Point', coordinates: area.point },
				properties: { name: area.name }
			}))
		);
		schedule();
	}

	function feed(id: string, features: unknown[]) {
		(map.getSource(id) as GeoJSONSource).setData({ type: 'FeatureCollection', features } as never);
	}

	function setMuted(points: readonly (readonly [number, number])[]) {
		muted = points;
		// What the canvas draws, for tests, which do not read pixels.
		map.getContainer().dataset.muted = String(points.length);
		if (!installed) return;
		feed(
			MUTED,
			points.map((coordinates) => ({
				type: 'Feature',
				geometry: { type: 'Point', coordinates },
				properties: {}
			}))
		);
	}

	function setOutline(next: Outline | null) {
		outline = next;
		map.getContainer().dataset.outline = String(next !== null);
		if (!installed) return;
		feed(OUTLINE, next ? [{ type: 'Feature', geometry: next, properties: {} }] : []);
	}

	// The elements over the canvas: one per Location and cluster in view.
	function entries(): Entry[] {
		const bounds = map.getBounds();
		const centre = map.getCenter();
		const byId = new Map(data.locations.map((feature) => [feature.properties.id, feature]));
		const seen = new Map<string, Entry>();
		for (const feature of map.querySourceFeatures(SIGNS)) {
			const properties = feature.properties as Record<string, number>;
			const at = (feature.geometry as unknown as { coordinates: Coordinates }).coordinates;
			if (properties.cluster_id !== undefined) {
				const key = `c${properties.cluster_id}`;
				if (seen.has(key) || !bounds.contains(at)) continue;
				seen.set(key, {
					key,
					at,
					label: options.describe.cluster(properties.artworks, properties.point_count),
					sign: 'cluster',
					activate: () => expand(properties.cluster_id, at)
				});
			} else {
				const location = byId.get(properties.id);
				const key = `l${properties.id}`;
				if (!location || seen.has(key)) continue;
				const point = location.properties.point;
				if (!bounds.contains(point)) continue;
				seen.set(key, {
					key,
					at: point,
					label: options.describe.sign(location.properties),
					sign: signImageName(location.properties).replace('sign-', ''),
					activate: () => options.onSelect(location.properties.id)
				});
			}
		}
		const distance = ([lon, lat]: Coordinates) => (lon - centre.lng) ** 2 + (lat - centre.lat) ** 2;
		return [...seen.values()]
			.sort((a, b) => distance(a.at) - distance(b.at))
			.slice(0, MAX_FOCUSABLE)
			.sort((a, b) => b.at[1] - a.at[1] || a.at[0] - b.at[0]);
	}

	async function expand(clusterId: number, at: Coordinates) {
		const source = map.getSource(SIGNS) as GeoJSONSource;
		const zoom = await source.getClusterExpansionZoom(clusterId);
		map.easeTo({ center: at, zoom: Math.min(zoom, map.getMaxZoom()) });
	}

	function refresh() {
		frame = 0;
		if (!installed) return;
		const wanted = options.focusable === false ? [] : entries();
		const keys = new Set(wanted.map((entry) => entry.key));
		for (const [key, { marker }] of markers) {
			if (keys.has(key)) continue;
			marker.remove();
			markers.delete(key);
		}
		for (const entry of wanted) {
			const known = markers.get(entry.key);
			if (known) {
				known.element.setAttribute('aria-label', entry.label);
				known.element.dataset.sign = entry.sign;
				continue;
			}
			const element = document.createElement('button');
			element.type = 'button';
			element.className = 'tart-sign';
			element.dataset.sign = entry.sign;
			element.setAttribute('aria-label', entry.label);
			element.addEventListener('click', entry.activate);
			const marker = new Marker({ element, anchor: 'center' }).setLngLat(entry.at).addTo(map);
			markers.set(entry.key, { marker, element });
		}
		// The hatched area shows only for a Location that is not in a cluster.
		const unclustered = wanted
			.filter((entry) => entry.key.startsWith('l'))
			.map((e) => +e.key.slice(1));
		if (map.getLayer(HATCH)) {
			map.setFilter(HATCH, ['in', ['get', 'id'], ['literal', unclustered]]);
		}
		refreshSites();
		report();
	}

	// What the canvas draws, on its container: the geometries and the hatched areas
	// in view, for tests, which do not read pixels.
	function report() {
		const container = map.getContainer();
		const rendered = (layers: string[]) =>
			map.getLayer(layers[0]) ? map.queryRenderedFeatures({ layers }) : [];
		const geometries = rendered(GROUPS.map((group) => `${GEOMETRIES}-${group}`));
		container.dataset.geometries = [
			...new Set(
				geometries.map((feature) => `${feature.properties.id}:${feature.properties.group}`)
			)
		]
			.sort()
			.join(' ');
		container.dataset.hatched = [
			...new Set(rendered([HATCH]).map((feature) => feature.properties.id as number))
		]
			.sort((a, b) => a - b)
			.join(' ');
	}

	function refreshSites() {
		const shown = map.getZoom() >= SITE_MIN_ZOOM;
		const wanted = new Map(shown ? data.sites.map((site) => [site.id, site]) : []);
		for (const [id, marker] of sites) {
			if (wanted.has(id)) continue;
			marker.remove();
			sites.delete(id);
		}
		const bounds = map.getBounds();
		for (const [id, site] of wanted) {
			if (sites.has(id) || !bounds.contains(site.point)) continue;
			const link = document.createElement('a');
			link.className = 'tart-site';
			link.href = site.path;
			link.textContent = site.name;
			sites.set(
				id,
				new Marker({ element: link, anchor: 'top', offset: [0, 14] })
					.setLngLat(site.point)
					.addTo(map)
			);
		}
	}

	function schedule() {
		if (!frame) frame = requestAnimationFrame(refresh);
	}

	map.on('idle', schedule);
	map.on('click', `${GEOMETRIES}-hit`, (event) => {
		const id = event.features?.[0]?.properties?.id;
		if (typeof id === 'number') options.onSelect(id);
	});

	return {
		install,
		setData,
		setMuted,
		setOutline,
		destroy() {
			cancelAnimationFrame(frame);
			for (const { marker } of markers.values()) marker.remove();
			for (const marker of sites.values()) marker.remove();
		}
	};
}
