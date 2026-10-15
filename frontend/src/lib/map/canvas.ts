import type { Shape } from './signs';

/** Draws shapes, as `Sign.svelte` draws them in SVG, into a canvas context. */
export function drawShapes(context: CanvasRenderingContext2D, shapes: readonly Shape[]): void {
	for (const shape of shapes) {
		const path = new Path2D(shape.d);
		if (shape.fill) {
			context.fillStyle = shape.fill;
			context.fill(path);
		}
		if (shape.stroke) {
			context.strokeStyle = shape.stroke;
			context.lineWidth = shape.strokeWidth ?? 1;
			context.lineCap = shape.dash || !shape.fill ? 'round' : 'butt';
			context.setLineDash(shape.dash ? [...shape.dash] : []);
			context.stroke(path);
		}
	}
}

/** Renders placed parts into an image of `width` × `height` CSS px at `ratio`. */
export function renderImage(
	width: number,
	height: number,
	parts: readonly { x: number; y: number; shapes: readonly Shape[] }[],
	ratio: number
): ImageData {
	const canvas = document.createElement('canvas');
	canvas.width = Math.ceil(width * ratio);
	canvas.height = Math.ceil(height * ratio);
	const context = canvas.getContext('2d')!;
	context.scale(ratio, ratio);
	for (const part of parts) {
		context.save();
		context.translate(part.x, part.y);
		drawShapes(context, part.shapes);
		context.restore();
	}
	return context.getImageData(0, 0, canvas.width, canvas.height);
}
