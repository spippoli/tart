/**
 * A round against the previous one (Contribution and moderation spec, Submission page):
 * the operations of the current round, each marked new or the same as before, and the
 * operations of the previous round that it no longer has. Two operations are the same when
 * their JSON is.
 */

export function operationsOf(snapshot: unknown): unknown[] {
	if (typeof snapshot !== 'object' || snapshot === null) return [];
	const operations = (snapshot as { operations?: unknown }).operations;
	return Array.isArray(operations) ? operations : [];
}

/** JSON with the keys in order, so that the same value always has the same text. */
function canonical(value: unknown): string {
	if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
	if (typeof value === 'object' && value !== null) {
		const entries = Object.entries(value).sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0));
		return `{${entries.map(([key, each]) => `${JSON.stringify(key)}:${canonical(each)}`).join(',')}}`;
	}
	return JSON.stringify(value) ?? 'null';
}

export interface RoundDiff {
	/** The current round's operations, in order, with whether the previous round had them. */
	current: { operation: unknown; fresh: boolean }[];
	/** What the previous round had and the current one has not. */
	removed: unknown[];
}

export function diffRounds(previous: unknown, current: unknown): RoundDiff {
	const before = operationsOf(previous);
	const after = operationsOf(current);
	const beforeKeys = new Set(before.map(canonical));
	const afterKeys = new Set(after.map(canonical));
	return {
		current: after.map((operation) => ({
			operation,
			fresh: !beforeKeys.has(canonical(operation))
		})),
		removed: before.filter((operation) => !afterKeys.has(canonical(operation)))
	};
}
