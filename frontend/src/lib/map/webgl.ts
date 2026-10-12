/**
 * Whether this browser can give a WebGL2 context, which MapLibre v6 needs (ADR 0004).
 * Probed before MapLibre is even downloaded; MapLibre's own failure to get a
 * context is caught as well (`createEngine`).
 */
export function supportsWebGL2(): boolean {
	try {
		return document.createElement('canvas').getContext('webgl2') !== null;
	} catch {
		return false;
	}
}
