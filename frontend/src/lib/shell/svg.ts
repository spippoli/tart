/** An SVG source as a `data:` URL: an <img> never runs its scripts. */
export function svgDataUrl(source: string): string {
	return `data:image/svg+xml,${encodeURIComponent(source)}`;
}
