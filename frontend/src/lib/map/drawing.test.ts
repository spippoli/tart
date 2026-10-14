import { describe, expect, it } from 'vitest';
import {
	addVertex,
	deleteSelected,
	finish,
	fromGeometry,
	geometry,
	insertVertex,
	moveSelected,
	problem,
	selectVertex,
	selfIntersects,
	startDrawing,
	stepSelection,
	undo,
	type Drawing
} from './drawing';
import type { Point } from './coordinates';

const BOUNDARY = [12.23, 41.65, 12.86, 42.14] as const;
const A: Point = [12.47, 41.89];
const B: Point = [12.48, 41.89];
const C: Point = [12.48, 41.9];
const D: Point = [12.47, 41.9];

function polygon(): Drawing {
	return [A, B, C].reduce((drawing, p) => addVertex(drawing, p, BOUNDARY), startDrawing('polygon'));
}

// Contribution and moderation criterion 20: every drawing operation can be done in crosshair
// mode with the keyboard alone. The crosshair buttons are these operations at the map centre;
// no operation needs a pointer position other than the point it is given.
describe('AC 20: every drawing operation works from the crosshair', () => {
	it('adds vertices at the centre, then closes a polygon of three or more', () => {
		let drawing = startDrawing('polygon');
		drawing = addVertex(drawing, A, BOUNDARY);
		drawing = addVertex(drawing, B, BOUNDARY);
		expect(finish(drawing).last).toEqual({ type: 'rejected', problem: 'too_few_vertices' });
		drawing = addVertex(drawing, C, BOUNDARY);
		drawing = finish(drawing);
		expect(drawing.finished).toBe(true);
		expect(geometry(drawing)).toEqual({ type: 'Polygon', coordinates: [[A, B, C, A]] });
	});

	it('closes a line at two vertices', () => {
		let drawing = addVertex(startDrawing('line'), A, BOUNDARY);
		expect(finish(drawing).finished).toBe(false);
		drawing = finish(addVertex(drawing, B, BOUNDARY));
		expect(geometry(drawing)).toEqual({ type: 'LineString', coordinates: [A, B] });
	});

	it('a point is one vertex, and adding again moves it', () => {
		let drawing = addVertex(startDrawing('point'), A, BOUNDARY);
		drawing = addVertex(drawing, B, BOUNDARY);
		expect(drawing.vertices).toEqual([B]);
		expect(geometry(finish(drawing))).toEqual({ type: 'Point', coordinates: B });
	});

	it('steps the selection through the vertices, wrapping, without a pointer', () => {
		let drawing = polygon();
		drawing = stepSelection(drawing, 1);
		expect(drawing.selected).toBe(0);
		drawing = stepSelection(stepSelection(stepSelection(drawing, 1), 1), 1);
		expect(drawing.selected).toBe(0);
		expect(stepSelection(drawing, -1).selected).toBe(2);
		expect(stepSelection(startDrawing('line'), 1).last).toEqual({
			type: 'rejected',
			problem: 'nothing_to_do'
		});
	});

	it('moves the selected vertex to the centre', () => {
		const moved = moveSelected(selectVertex(polygon(), 1), D, BOUNDARY);
		expect(moved.vertices).toEqual([A, D, C]);
		expect(moved.selected).toBeNull();
		expect(moved.last).toEqual({ type: 'moved', index: 1 });
	});

	it('inserts a vertex after the selected one', () => {
		const inserted = insertVertex(polygon(), 0, D, BOUNDARY);
		expect(inserted.vertices).toEqual([A, D, B, C]);
		expect(inserted.last).toEqual({ type: 'inserted', index: 1 });
	});

	it('deletes the selected vertex', () => {
		const deleted = deleteSelected(selectVertex(polygon(), 1));
		expect(deleted.vertices).toEqual([A, C]);
		expect(deleted.last).toEqual({ type: 'deleted', index: 1 });
		expect(deleteSelected(polygon()).last).toEqual({ type: 'rejected', problem: 'nothing_to_do' });
	});

	it('undoes each operation in turn, down to the empty drawing', () => {
		let drawing = finish(polygon());
		drawing = deleteSelected(selectVertex(drawing, 0));
		drawing = insertVertex(drawing, 0, D, BOUNDARY);
		drawing = undo(drawing);
		expect(drawing.vertices).toEqual([B, C]);
		drawing = undo(drawing);
		expect(drawing.vertices).toEqual([A, B, C]);
		expect(drawing.finished).toBe(true);
		drawing = undo(drawing);
		expect(drawing.finished).toBe(false);
		while (drawing.history.length) drawing = undo(drawing);
		expect(drawing.vertices).toEqual([]);
		expect(undo(drawing).last).toEqual({ type: 'rejected', problem: 'nothing_to_do' });
	});

	it('editing a finished drawing reopens it', () => {
		const edited = addVertex(finish(polygon()), D, BOUNDARY);
		expect(edited.finished).toBe(false);
		expect(geometry(edited)).toBeNull();
	});
});

describe('rejections the form turns into text', () => {
	it('refuses a vertex outside the Instance boundary and keeps the drawing', () => {
		const drawing = polygon();
		const rejected = addVertex(drawing, [2.35, 48.85], BOUNDARY);
		expect(rejected.last).toEqual({ type: 'rejected', problem: 'outside_boundary' });
		expect(rejected.vertices).toEqual(drawing.vertices);
		expect(rejected.history).toEqual(drawing.history);
		expect(moveSelected(selectVertex(drawing, 0), [2.35, 48.85], BOUNDARY).last).toEqual({
			type: 'rejected',
			problem: 'outside_boundary'
		});
	});

	it('refuses to finish a self-intersecting polygon', () => {
		// A bow tie: A, C, B, D crosses itself.
		const bowTie = [A, C, B, D].reduce(
			(drawing, p) => addVertex(drawing, p, BOUNDARY),
			startDrawing('polygon')
		);
		expect(problem(bowTie)).toBe('self_intersecting');
		expect(finish(bowTie).last).toEqual({ type: 'rejected', problem: 'self_intersecting' });
		expect(geometry(bowTie)).toBeNull();
	});

	it('detects a polygon edge crossing or touching a non-neighbour edge', () => {
		expect(selfIntersects([A, B, C, D])).toBe(false);
		expect(selfIntersects([A, C, B, D])).toBe(true);
		// A vertex lying on a distant edge.
		expect(selfIntersects([A, B, C, [12.475, 41.89], D])).toBe(true);
		expect(selfIntersects([A, B, C])).toBe(false);
	});

	it('lets a line cross itself', () => {
		const line = [A, C, B, D].reduce(
			(drawing, p) => addVertex(drawing, p, BOUNDARY),
			startDrawing('line')
		);
		expect(problem(line)).toBeNull();
	});
});

describe('editing an existing geometry', () => {
	it('round-trips each shape through GeoJSON', () => {
		for (const shape of [
			{ type: 'Point', coordinates: A },
			{ type: 'LineString', coordinates: [A, B] },
			{ type: 'Polygon', coordinates: [[A, B, C, A]] }
		] as const) {
			expect(geometry(fromGeometry(shape))).toEqual(shape);
		}
	});
});
