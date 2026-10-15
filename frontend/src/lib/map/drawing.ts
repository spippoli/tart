/**
 * The state of drawing a Location's geometry (Discovery spec, Modules: drawing;
 * Contribution and moderation, Location step): a point, a line, or a simple
 * polygon, built vertex by vertex. Pure functions over an immutable `Drawing`, so
 * that clicks on the map and the crosshair buttons are two inputs to the same
 * operations (add, move, delete, insert, close, undo), and the keyboard can do
 * everything the pointer can. Nothing here knows MapLibre.
 */
import type { Bounds } from './bounds';
import { insideBounds, type Point } from './coordinates';

export type Shape = 'point' | 'line' | 'polygon';

/** Why an operation changed nothing, or why a drawing cannot be finished. */
export type Problem =
	'outside_boundary' | 'too_few_vertices' | 'self_intersecting' | 'nothing_to_do';

/** What the last operation did, for the text announced to assistive technology. */
export type Event =
	| { type: 'started' }
	| { type: 'added' | 'moved' | 'inserted' | 'deleted' | 'selected'; index: number }
	| { type: 'deselected' }
	| { type: 'undone' }
	| { type: 'finished' }
	| { type: 'rejected'; problem: Problem };

export interface Drawing {
	shape: Shape;
	vertices: readonly Point[];
	/** The vertex a move, an insertion, or a deletion acts on. */
	selected: number | null;
	/** *Done* was pressed on a drawing that could be finished. */
	finished: boolean;
	/** The states before each change, newest last, for undo. */
	history: readonly Snapshot[];
	last: Event;
}

type Snapshot = Pick<Drawing, 'vertices' | 'selected' | 'finished'>;

/** The fewest vertices a line and a polygon need. */
export const MINIMUM: Record<Shape, number> = { point: 1, line: 2, polygon: 3 };

export function startDrawing(shape: Shape): Drawing {
	return {
		shape,
		vertices: [],
		selected: null,
		finished: false,
		history: [],
		last: { type: 'started' }
	};
}

function change(
	drawing: Drawing,
	next: Partial<Pick<Drawing, 'vertices' | 'selected' | 'finished'>>,
	last: Event
): Drawing {
	const { vertices, selected, finished, history } = drawing;
	return {
		...drawing,
		...next,
		history: [...history, { vertices, selected, finished }],
		last
	};
}

function reject(drawing: Drawing, problem: Problem): Drawing {
	return { ...drawing, last: { type: 'rejected', problem } };
}

type Inside = Bounds;

/** A new vertex at the end; for a point, the point itself, replacing any earlier one. */
export function addVertex(drawing: Drawing, at: Point, inside: Inside): Drawing {
	if (!insideBounds(at, inside)) return reject(drawing, 'outside_boundary');
	if (drawing.shape === 'point') {
		const moved = drawing.vertices.length > 0;
		return change(
			drawing,
			{ vertices: [at], selected: null, finished: false },
			{ type: moved ? 'moved' : 'added', index: 0 }
		);
	}
	const vertices = [...drawing.vertices, at];
	return change(
		drawing,
		{ vertices, selected: null, finished: false },
		{ type: 'added', index: vertices.length - 1 }
	);
}

/** Selects a vertex so that the next click, or *Move selected vertex here*, moves it. */
export function selectVertex(drawing: Drawing, index: number | null): Drawing {
	if (index === null) return { ...drawing, selected: null, last: { type: 'deselected' } };
	if (index < 0 || index >= drawing.vertices.length) return reject(drawing, 'nothing_to_do');
	return { ...drawing, selected: index, last: { type: 'selected', index } };
}

/** Selects the next (1) or previous (-1) vertex, wrapping around. */
export function stepSelection(drawing: Drawing, step: 1 | -1): Drawing {
	const count = drawing.vertices.length;
	if (count === 0) return reject(drawing, 'nothing_to_do');
	const from = drawing.selected ?? (step === 1 ? -1 : 0);
	return selectVertex(drawing, (from + step + count) % count);
}

/** Moves the selected vertex. */
export function moveSelected(drawing: Drawing, to: Point, inside: Inside): Drawing {
	const { selected } = drawing;
	if (selected === null) return reject(drawing, 'nothing_to_do');
	if (!insideBounds(to, inside)) return reject(drawing, 'outside_boundary');
	const vertices = drawing.vertices.map((vertex, i) => (i === selected ? to : vertex));
	return change(
		drawing,
		{ vertices, selected: null, finished: false },
		{ type: 'moved', index: selected }
	);
}

/** Inserts a vertex after `after` (a segment midpoint is a click between two vertices). */
export function insertVertex(drawing: Drawing, after: number, at: Point, inside: Inside): Drawing {
	if (drawing.shape === 'point' || after < 0 || after >= drawing.vertices.length) {
		return reject(drawing, 'nothing_to_do');
	}
	if (!insideBounds(at, inside)) return reject(drawing, 'outside_boundary');
	const vertices = [
		...drawing.vertices.slice(0, after + 1),
		at,
		...drawing.vertices.slice(after + 1)
	];
	return change(
		drawing,
		{ vertices, selected: null, finished: false },
		{ type: 'inserted', index: after + 1 }
	);
}

/** Deletes the selected vertex. */
export function deleteSelected(drawing: Drawing): Drawing {
	const { selected } = drawing;
	if (selected === null) return reject(drawing, 'nothing_to_do');
	const vertices = drawing.vertices.filter((_, i) => i !== selected);
	return change(
		drawing,
		{ vertices, selected: null, finished: false },
		{ type: 'deleted', index: selected }
	);
}

/** Undoes the last change. */
export function undo(drawing: Drawing): Drawing {
	const previous = drawing.history.at(-1);
	if (!previous) return reject(drawing, 'nothing_to_do');
	return {
		...drawing,
		...previous,
		history: drawing.history.slice(0, -1),
		last: { type: 'undone' }
	};
}

function cross(a: Point, b: Point, c: Point): number {
	return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
}

function onSegment(a: Point, b: Point, p: Point): boolean {
	return (
		Math.min(a[0], b[0]) <= p[0] &&
		p[0] <= Math.max(a[0], b[0]) &&
		Math.min(a[1], b[1]) <= p[1] &&
		p[1] <= Math.max(a[1], b[1])
	);
}

/** Whether two segments share a point (a planar test, which holds at city scale). */
function touch(a: Point, b: Point, c: Point, d: Point): boolean {
	const d1 = cross(a, b, c);
	const d2 = cross(a, b, d);
	const d3 = cross(c, d, a);
	const d4 = cross(c, d, b);
	if (((d1 > 0 && d2 < 0) || (d1 < 0 && d2 > 0)) && ((d3 > 0 && d4 < 0) || (d3 < 0 && d4 > 0))) {
		return true;
	}
	return (
		(d1 === 0 && onSegment(a, b, c)) ||
		(d2 === 0 && onSegment(a, b, d)) ||
		(d3 === 0 && onSegment(c, d, a)) ||
		(d4 === 0 && onSegment(c, d, b))
	);
}

/** Whether a ring of vertices crosses or touches itself anywhere but at consecutive vertices. */
export function selfIntersects(ring: readonly Point[]): boolean {
	const n = ring.length;
	if (n < 4) return false;
	for (let i = 0; i < n; i++) {
		for (let j = i + 1; j < n; j++) {
			// Edges that share a vertex are neighbours, including the closing edge.
			if (j === i + 1 || (i === 0 && j === n - 1)) continue;
			if (touch(ring[i], ring[(i + 1) % n], ring[j], ring[(j + 1) % n])) return true;
		}
	}
	return false;
}

/** What stops the drawing from being finished, if anything. */
export function problem(drawing: Drawing): Problem | null {
	if (drawing.vertices.length < MINIMUM[drawing.shape]) return 'too_few_vertices';
	if (drawing.shape === 'polygon' && selfIntersects(drawing.vertices)) return 'self_intersecting';
	return null;
}

/** *Done*: closes the line, or the polygon once it has three vertices. */
export function finish(drawing: Drawing): Drawing {
	const found = problem(drawing);
	if (found) return reject(drawing, found);
	return change(drawing, { selected: null, finished: true }, { type: 'finished' });
}

export type Geometry =
	| { type: 'Point'; coordinates: Point }
	| { type: 'LineString'; coordinates: readonly Point[] }
	| { type: 'Polygon'; coordinates: readonly (readonly Point[])[] };

/** The GeoJSON of a finished drawing, in the order the server takes it. */
export function geometry(drawing: Drawing): Geometry | null {
	if (!drawing.finished || problem(drawing)) return null;
	const vertices = [...drawing.vertices];
	switch (drawing.shape) {
		case 'point':
			return { type: 'Point', coordinates: vertices[0] };
		case 'line':
			return { type: 'LineString', coordinates: vertices };
		case 'polygon':
			return { type: 'Polygon', coordinates: [[...vertices, vertices[0]]] };
	}
}

/** A finished geometry back as a drawing, for editing a Location's existing geometry. */
export function fromGeometry(shape: Geometry): Drawing {
	const base = startDrawing(
		shape.type === 'Point' ? 'point' : shape.type === 'LineString' ? 'line' : 'polygon'
	);
	const vertices =
		shape.type === 'Point'
			? [shape.coordinates]
			: shape.type === 'LineString'
				? shape.coordinates
				: shape.coordinates[0].slice(0, -1);
	return { ...base, vertices, finished: true };
}
