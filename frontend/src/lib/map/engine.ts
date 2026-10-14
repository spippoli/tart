/**
 * The only code that imports MapLibre GL JS and the `pmtiles` protocol (ADR 0004).
 * Callers of the map module never touch MapLibre objects: `Map.svelte` loads this
 * file in the browser only, and drives the map through `Engine`.
 */
import {
	addProtocol,
	type GeoJSONSource,
	Map as MapLibreMap,
	setWorkerUrl,
	type AddProtocolAction,
	type StyleSpecification
} from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
// MapLibre finds its worker next to its own module, which bundling moves: Vite
// builds the worker, with the code it shares with the main thread, as its own file.
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';
import { Protocol } from 'pmtiles';
import { MAX_ZOOM, type Bounds } from './bounds';
import type { Point } from './coordinates';
import type { Style, Tokens, Unavailable } from './style';

export interface View {
	/** Longitude, latitude. */
	center: readonly [number, number];
	zoom: number;
}

export interface Camera extends View {
	bearing: number;
	pitch: number;
}

/** What a click landed on among the drawing's own handles, if anything. */
export type Handle = { kind: 'vertex' | 'midpoint'; index: number };

export interface ClickEvent {
	point: Point;
	handle: Handle | null;
}

/**
 * The drawing shown over the map: the shape being drawn and its handles. A midpoint
 * with index `i` sits on the segment after vertex `i`.
 */
export interface Drawn {
	/** The shape's vertices and whether they form a ring (a polygon) or a path. */
	vertices: readonly Point[];
	ring: boolean;
	selected: number | null;
	/** Midpoint handles, where a click inserts a vertex; none for a point. */
	midpoints: boolean;
}

export interface EngineOptions {
	style: Style;
	view: View;
	bounds: Bounds;
	/** The configured map attribution, shown as links and never translated. */
	attribution: readonly { text: string; url: string }[];
	/** The few strings MapLibre itself shows, in the UI language. */
	labels: { canvas: string; attributionToggle: string };
	onMoveEnd: (camera: Camera) => void;
	/** Clicks on the map; set for the drawing tool only. */
	onClick?: (click: ClickEvent) => void;
}

export interface Engine {
	zoomIn(): void;
	zoomOut(): void;
	/** Pans by a third of the view along each axis: -1, 0, or 1 (east and south positive). */
	pan(x: number, y: number): void;
	/** Back to `view`. */
	reset(): void;
	/** Shows the shape being drawn over the map; `null` clears it. */
	setDrawn(drawn: Drawn | null, tokens: Tokens): void;
	/** Moves the map so that `point` is at its centre. */
	centerOn(point: Point): void;
	/** Switches the style without a reload (a theme change). */
	setStyle(style: Style): void;
	destroy(): void;
}

let configured = false;

const DRAW = 'tart-draw';
const HANDLE_LAYERS = [`${DRAW}-vertices`, `${DRAW}-midpoints`];

function drawnCollection(drawn: Drawn) {
	const { vertices, ring, selected, midpoints } = drawn;
	const features: object[] = [];
	const path = ring && vertices.length > 2 ? [...vertices, vertices[0]] : vertices;
	if (ring && vertices.length > 2) {
		features.push({
			type: 'Feature',
			properties: { role: 'area' },
			geometry: { type: 'Polygon', coordinates: [path] }
		});
	}
	if (path.length > 1) {
		features.push({
			type: 'Feature',
			properties: { role: 'line' },
			geometry: { type: 'LineString', coordinates: path }
		});
	}
	vertices.forEach((vertex, index) => {
		features.push({
			type: 'Feature',
			properties: { role: 'vertex', index, selected: index === selected },
			geometry: { type: 'Point', coordinates: vertex }
		});
		const next = path[index + 1];
		if (midpoints && next) {
			features.push({
				type: 'Feature',
				properties: { role: 'midpoint', index },
				geometry: {
					type: 'Point',
					coordinates: [(vertex[0] + next[0]) / 2, (vertex[1] + next[1]) / 2]
				}
			});
		}
	});
	return { type: 'FeatureCollection', features };
}

function addDrawingLayers(map: MapLibreMap, tokens: Tokens) {
	const ink = tokens['marker.ink'];
	const accent = tokens['marker.accent'];
	const paper = tokens['map.paper'];
	map.addSource(DRAW, { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
	map.addLayer({
		id: `${DRAW}-area`,
		type: 'fill',
		source: DRAW,
		filter: ['==', ['get', 'role'], 'area'],
		paint: { 'fill-color': accent, 'fill-opacity': 0.2 }
	});
	// A proposal is drawn with a dashed outline (ADR 0015).
	map.addLayer({
		id: `${DRAW}-line`,
		type: 'line',
		source: DRAW,
		filter: ['==', ['get', 'role'], 'line'],
		paint: { 'line-color': ink, 'line-width': 3, 'line-dasharray': [2, 1.5] }
	});
	map.addLayer({
		id: `${DRAW}-midpoints`,
		type: 'circle',
		source: DRAW,
		filter: ['==', ['get', 'role'], 'midpoint'],
		paint: {
			'circle-radius': 5,
			'circle-color': paper,
			'circle-stroke-color': ink,
			'circle-stroke-width': 1.5
		}
	});
	// The selected vertex is larger and ringed, so that selection is never colour alone.
	map.addLayer({
		id: `${DRAW}-vertices`,
		type: 'circle',
		source: DRAW,
		filter: ['==', ['get', 'role'], 'vertex'],
		paint: {
			'circle-radius': ['case', ['get', 'selected'], 10, 7],
			'circle-color': ['case', ['get', 'selected'], accent, paper],
			'circle-stroke-color': ink,
			'circle-stroke-width': ['case', ['get', 'selected'], 4, 2]
		}
	});
}

function escapeHtml(text: string): string {
	return text.replace(
		/[&<>"']/g,
		(c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!
	);
}

function attributionHtml(entry: { text: string; url: string }): string {
	return `<a href="${escapeHtml(entry.url)}" rel="noopener">${escapeHtml(entry.text)}</a>`;
}

/**
 * Renders a map into `container`. Resolves once the style has loaded; rejects with
 * the reason when the map cannot be shown: `webgl2` when MapLibre could not get a
 * WebGL2 context, `style` when the style failed to load (an `error` event before the
 * first `load`). Errors after that, such as a tile that fails, leave the map in place.
 */
export function createEngine(container: HTMLElement, options: EngineOptions): Promise<Engine> {
	if (!configured) {
		setWorkerUrl(workerUrl);
		addProtocol('pmtiles', new Protocol().tilev4 as AddProtocolAction);
		configured = true;
	}

	return new Promise((resolve, rejectWith) => {
		const reject = (reason: Unavailable) => rejectWith(reason);
		let map: MapLibreMap;
		try {
			map = new MapLibreMap({
				container,
				style: options.style as unknown as StyleSpecification,
				center: [options.view.center[0], options.view.center[1]],
				zoom: options.view.zoom,
				maxBounds: [...options.bounds] as [number, number, number, number],
				maxZoom: MAX_ZOOM,
				// Rotation and pitch are disabled (ADR 0017).
				maxPitch: 0,
				dragRotate: false,
				pitchWithRotate: false,
				touchPitch: false,
				attributionControl: {
					compact: true,
					customAttribution: options.attribution.map(attributionHtml)
				},
				locale: {
					'Map.Title': options.labels.canvas,
					'AttributionControl.ToggleAttribution': options.labels.attributionToggle
				}
			});
		} catch {
			reject('webgl2');
			return;
		}
		map.keyboard.disableRotation();
		map.touchZoomRotate.disableRotation();

		let loaded = false;
		const camera = (): Camera => {
			const { lng, lat } = map.getCenter();
			return {
				center: [lng, lat],
				zoom: map.getZoom(),
				bearing: map.getBearing(),
				pitch: map.getPitch()
			};
		};
		map.on('moveend', () => options.onMoveEnd(camera()));
		// What is drawn is kept here, so that a style switch can put it back.
		let drawn: { value: Drawn; tokens: Tokens } | null = null;
		const showDrawn = () => {
			if (!drawn) return;
			if (!map.getSource(DRAW)) addDrawingLayers(map, drawn.tokens);
			(map.getSource(DRAW) as GeoJSONSource).setData(
				drawnCollection(drawn.value) as unknown as Parameters<GeoJSONSource['setData']>[0]
			);
		};
		map.on('style.load', showDrawn);
		const { onClick } = options;
		if (onClick) {
			map.on('click', (event) => {
				const layers = HANDLE_LAYERS.filter((id) => map.getLayer(id));
				const found = layers.length
					? map.queryRenderedFeatures(event.point, { layers })[0]
					: undefined;
				const handle = found
					? {
							kind: found.properties.role as 'vertex' | 'midpoint',
							index: Number(found.properties.index)
						}
					: null;
				onClick({ point: [event.lngLat.lng, event.lngLat.lat], handle });
			});
		}
		map.on('error', () => {
			if (loaded) return;
			map.remove();
			reject('style');
		});
		map.once('load', () => {
			loaded = true;
			options.onMoveEnd(camera());
			resolve({
				zoomIn: () => map.zoomIn(),
				zoomOut: () => map.zoomOut(),
				pan(x, y) {
					const { clientWidth, clientHeight } = map.getContainer();
					map.panBy([(x * clientWidth) / 3, (y * clientHeight) / 3]);
				},
				reset: () =>
					map.easeTo({
						center: [options.view.center[0], options.view.center[1]],
						zoom: options.view.zoom,
						bearing: 0,
						pitch: 0
					}),
				setDrawn(value, tokens) {
					drawn = value && { value, tokens };
					if (value) showDrawn();
					else if (map.getSource(DRAW)) {
						(map.getSource(DRAW) as GeoJSONSource).setData({
							type: 'FeatureCollection',
							features: []
						});
					}
				},
				centerOn: (point) => map.easeTo({ center: [point[0], point[1]] }),
				setStyle: (style) => map.setStyle(style as unknown as StyleSpecification),
				destroy: () => map.remove()
			});
		});
	});
}
