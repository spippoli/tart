/**
 * The only code, with `archive.ts`, that imports MapLibre GL JS and the `pmtiles` protocol (ADR 0004).
 * Callers of the map module never touch MapLibre objects: `Map.svelte` loads this
 * file in the browser only, and drives the map through `Engine`.
 */
import {
	addProtocol,
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
import { createArchive, type ArchiveOptions } from './archive';
import { MAX_ZOOM, type Bounds } from './bounds';
import type { MapData } from './locations';
import type { Style, Unavailable } from './style';

export interface View {
	/** Longitude, latitude. */
	center: readonly [number, number];
	zoom: number;
}

export interface Camera extends View {
	bearing: number;
	pitch: number;
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
	archive: ArchiveOptions;
}

export interface Engine {
	zoomIn(): void;
	zoomOut(): void;
	/** Pans by a third of the view along each axis: -1, 0, or 1 (east and south positive). */
	pan(x: number, y: number): void;
	/** Back to `view`. */
	reset(): void;
	/** Switches the style without a reload (a theme change). */
	setStyle(style: Style): void;
	/** The Locations, Sites, and Areas to draw. */
	setData(data: MapData): void;
	destroy(): void;
}

let configured = false;

function escapeHtml(text: string): string {
	return text.replace(
		/[&<>"']/g,
		(c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!
	);
}

/** The style's own fonts, for the page's text that goes over the map (Site labels). */
function loadFonts(style: Style) {
	const faces = (style as { 'font-faces'?: Record<string, string> })['font-faces'] ?? {};
	for (const [family, url] of Object.entries(faces)) {
		const face = new FontFace(family, `url(${JSON.stringify(url)})`);
		face.load().then(
			() => document.fonts.add(face),
			() => undefined
		);
	}
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
		let style = options.style;
		const archive = createArchive(map, options.archive);
		map.on('style.load', () => archive.install(style));
		loadFonts(style);
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
		map.on('error', (event) => {
			// A font or glyph that is missing leaves labels out, not the map.
			if (loaded || /glyph|font/i.test(String(event.error?.message))) return;
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
				setStyle(next) {
					style = next;
					// A full reload, so that the archive layers are added to the new style.
					map.setStyle(next as unknown as StyleSpecification, { diff: false });
				},
				setData: (data) => archive.setData(data),
				destroy() {
					archive.destroy();
					map.remove();
				}
			});
		});
	});
}
