import type { Tokens } from './style';

/**
 * The archive's signs (ADR 0015, Discovery spec, The map): a solid square for a
 * *present* Artwork, a dotted square with a "?" for *unknown*, a dashed square for
 * *disappeared*, the stack outline, the neutral cluster circle, and the hatch of an
 * approximate area. Each is a list of shapes in a `size` × `size` box, coloured
 * from the style's tokens, so the legend (SVG) and the map (canvas, with `Path2D`)
 * draw the same thing. The "?" is a path, never a font glyph.
 */
export type SignKind = 'present' | 'unknown' | 'disappeared' | 'stack' | 'cluster' | 'hatch';

export const SIGN_KINDS: readonly SignKind[] = [
	'present',
	'unknown',
	'disappeared',
	'stack',
	'cluster',
	'hatch'
];

/** The normal sign and the smaller sign of an approximate point (platform constants). */
export const SIGN_SIZE = 16;
export const SMALL_SIGN_SIZE = 12;

export interface Shape {
	/** SVG path data. */
	d: string;
	fill?: string;
	stroke?: string;
	strokeWidth?: number;
	/** Dash and gap lengths. */
	dash?: readonly number[];
}

function square(x: number, y: number, side: number): string {
	return `M${x} ${y}h${side}v${side}h${-side}Z`;
}

/** A "?" drawn with strokes, centred in a box of `size`. */
function questionMark(size: number): string {
	const u = size / 16;
	const r = (n: number) => +(n * u).toFixed(3);
	return (
		`M${r(6)} ${r(6.2)}a${r(2)} ${r(2)} 0 1 1 ${r(2.8)} ${r(1.8)}` +
		`c${r(-0.6)} ${r(0.3)} ${r(-0.8)} ${r(0.7)} ${r(-0.8)} ${r(1.4)}v${r(0.6)}` +
		`M${r(8)} ${r(11.2)}v${r(0.4)}`
	);
}

export function signShapes(kind: SignKind, tokens: Tokens, size = SIGN_SIZE): Shape[] {
	const ink = tokens['marker.ink'];
	const paper = tokens['map.paper'];
	const line = Math.max(1.5, size / 8);
	const inset = line / 2;
	const side = size - line;
	switch (kind) {
		case 'present':
			return [{ d: square(inset, inset, side), fill: ink, stroke: ink, strokeWidth: line }];
		case 'unknown':
			return [
				{
					d: square(inset, inset, side),
					fill: paper,
					stroke: ink,
					strokeWidth: line,
					dash: [line * 0.1, line * 1.4]
				},
				{ d: questionMark(size), stroke: ink, strokeWidth: Math.max(1.25, size / 10) }
			];
		case 'disappeared':
			return [
				{
					d: square(inset, inset, side),
					fill: paper,
					stroke: tokens['marker.accent'],
					strokeWidth: line,
					dash: [size / 4, size / 8]
				}
			];
		case 'stack': {
			// A second outline offset behind the square: a difference of shape, not colour.
			const offset = size / 5;
			const front = side - offset;
			return [
				{ d: square(inset + offset, inset, front), fill: paper, stroke: ink, strokeWidth: line },
				{ d: square(inset, inset + offset, front), fill: ink, stroke: ink, strokeWidth: line }
			];
		}
		case 'cluster': {
			const radius = size / 2 - inset;
			const c = size / 2;
			return [
				{
					d: `M${c - radius} ${c}a${radius} ${radius} 0 1 0 ${2 * radius} 0a${radius} ${radius} 0 1 0 ${-2 * radius} 0Z`,
					fill: paper,
					stroke: tokens['map.ink'],
					strokeWidth: line
				}
			];
		}
		case 'hatch': {
			// 45° ink lines 10 px apart at map scale, with no outline (ADR 0017).
			const spacing = (10 * size) / 24;
			let d = '';
			for (let k = -size; k <= size; k += spacing) {
				d += `M${+k.toFixed(3)} ${size}L${+(k + size).toFixed(3)} 0`;
			}
			return [{ d, stroke: tokens['map.ink'], strokeWidth: 1 }];
		}
	}
}
