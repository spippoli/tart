import { describe, expect, it } from 'vitest';
import { initialLegendOpen, LEGEND_KEY, rememberLegend } from './legend-memory';

function memoryStorage() {
	const items = new Map<string, string>();
	return {
		getItem: (key: string) => items.get(key) ?? null,
		setItem: (key: string, value: string) => void items.set(key, value)
	};
}

// Discovery criterion 13: open on the first visit, and working without localStorage.
describe('AC 13: the legend is remembered as a convenience only', () => {
	it('is open on the first visit and closed afterwards', () => {
		const storage = memoryStorage();
		expect(initialLegendOpen(() => storage)).toBe(true);
		expect(initialLegendOpen(() => storage)).toBe(false);
	});

	it('remembers the visitor leaving it open or closing it', () => {
		const storage = memoryStorage();
		initialLegendOpen(() => storage);
		rememberLegend(true, () => storage);
		expect(initialLegendOpen(() => storage)).toBe(true);
		rememberLegend(false, () => storage);
		expect(storage.getItem(LEGEND_KEY)).toBe('closed');
		expect(initialLegendOpen(() => storage)).toBe(false);
	});

	it('is open, and nothing throws, when storage is unavailable', () => {
		const unavailable = () => {
			throw new DOMException('denied', 'SecurityError');
		};
		expect(initialLegendOpen(unavailable)).toBe(true);
		expect(() => rememberLegend(false, unavailable)).not.toThrow();
	});
});
