/**
 * Whether the legend is open (Discovery spec, Map controls, legend, attribution):
 * open on the first visit, closed afterwards unless the visitor left it open,
 * remembered in `localStorage` as a convenience only. When storage is unavailable
 * or throws, every visit counts as the first.
 */
export const LEGEND_KEY = 'tart.map.legend';

type Storage = Pick<globalThis.Storage, 'getItem' | 'setItem'>;

/** The legend's state when a map appears; a first visit is recorded as seen. */
export function initialLegendOpen(storage: () => Storage = () => localStorage): boolean {
	try {
		const store = storage();
		const remembered = store.getItem(LEGEND_KEY);
		if (remembered === null) {
			store.setItem(LEGEND_KEY, 'closed');
			return true;
		}
		return remembered === 'open';
	} catch {
		return true;
	}
}

/** Records the visitor's choice. */
export function rememberLegend(open: boolean, storage: () => Storage = () => localStorage): void {
	try {
		storage().setItem(LEGEND_KEY, open ? 'open' : 'closed');
	} catch {
		// Storage unavailable: the choice lasts for this page only.
	}
}
