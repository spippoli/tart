/** A representative position of a GeoJSON Point, LineString, or Polygon: `[longitude, latitude]`. */
export function representativePoint(geometry: {
	type: string;
	coordinates: unknown;
}): [number, number] | null {
	const positions: number[][] =
		geometry.type === 'Point'
			? [geometry.coordinates as number[]]
			: geometry.type === 'LineString'
				? (geometry.coordinates as number[][])
				: geometry.type === 'Polygon'
					? (geometry.coordinates as number[][][])[0].slice(0, -1)
					: [];
	if (positions.length === 0) return null;
	const mean = (index: number) =>
		positions.reduce((sum, position) => sum + position[index], 0) / positions.length;
	return [mean(0), mean(1)];
}

/** A `geo:` URI (RFC 5870), which a maps app opens; 6 decimals, about 10 cm. */
export function geoUri([longitude, latitude]: [number, number], radius?: number | null): string {
	const uncertainty = radius ? `;u=${radius}` : '';
	return `geo:${latitude.toFixed(6)},${longitude.toFixed(6)}${uncertainty}`;
}
