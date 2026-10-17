/**
 * The operations of a Merge, a Duplicate retirement, and an Unmerge, as the editor changes
 * them (Contribution and moderation spec, Merge, Duplicate retirement, Unmerge; ADR 0018).
 *
 * A Submission stores only a changeset: the operations in their JSON form. The editor shows
 * the choices the API computed (`MergeReview`) and turns each choice into the presence or
 * absence of one operation, so that what is stored is exactly what is shown:
 *
 * - an item of the folded record is *kept* when an `add` operation on the survivor names it;
 * - an item of the survivor is *kept* unless a `remove` operation on it names it;
 * - a field takes the folded record's value when a `set` operation on the survivor says so;
 * - an Unmerge points a record back to the restored one through the operations that target it.
 *
 * Every function returns a new list and leaves its argument alone.
 */

export type Op = Record<string, unknown>;

export interface Entry {
	collection: string;
	key: unknown;
	item: unknown;
	origin: 'source' | 'into';
}

const same = (a: unknown, b: unknown): boolean => JSON.stringify(a) === JSON.stringify(b);

/** The key of a collection item in its JSON form, as the API names it. */
export function keyOf(collection: string, item: unknown): unknown {
	const value = item as Record<string, unknown> | null;
	switch (collection) {
		case 'attributions':
			return value?.artist;
		case 'history_events':
			return value?.id;
		case 'crew_memberships':
			return [value?.collective, value?.period ?? null];
	}
	return item;
}

const isMerge = (op: Op) => op.op === 'merge' || op.op === 'unmerge';

/** The Merge or Unmerge operation itself, which the editor never changes. */
export function mergeOperation(operations: Op[]): Op | undefined {
	return operations.find(isMerge);
}

/** The records the Submission works on: the folded one and the survivor. */
export function recordsOf(operations: Op[]): { source: number; into: number } | undefined {
	const op = mergeOperation(operations);
	return op ? { source: Number(op.source), into: Number(op.into) } : undefined;
}

function addOf(operations: Op[], into: number, entry: Entry): Op | undefined {
	return operations.find(
		(op) =>
			op.op === 'add' &&
			op.target === into &&
			op.collection === entry.collection &&
			same(keyOf(entry.collection, op.item), entry.key)
	);
}

function removeOf(operations: Op[], into: number, entry: Entry): Op | undefined {
	return operations.find(
		(op) =>
			op.op === 'remove' &&
			op.target === into &&
			op.collection === entry.collection &&
			same(op.key, entry.key)
	);
}

/** Whether the item ends up on the survivor. */
export function isKept(operations: Op[], into: number, entry: Entry): boolean {
	return entry.origin === 'source'
		? addOf(operations, into, entry) !== undefined
		: removeOf(operations, into, entry) === undefined;
}

/** Keep or drop an item of either record. */
export function setKept(operations: Op[], into: number, entry: Entry, keep: boolean): Op[] {
	if (isKept(operations, into, entry) === keep) return operations;
	if (entry.origin === 'source') {
		if (!keep) return operations.filter((op) => op !== addOf(operations, into, entry));
		const added: Op = {
			op: 'add',
			target: into,
			collection: entry.collection,
			item: entry.item
		};
		return insertBeforeMerge(operations, added);
	}
	if (keep) return operations.filter((op) => op !== removeOf(operations, into, entry));
	const removed: Op = { op: 'remove', target: into, collection: entry.collection, key: entry.key };
	return insertBeforeMerge(operations, removed);
}

function insertBeforeMerge(operations: Op[], op: Op): Op[] {
	const at = operations.findIndex(isMerge);
	return at < 0 ? [...operations, op] : [...operations.slice(0, at), op, ...operations.slice(at)];
}

/** An Alias added to the survivor can be edited before it is submitted. */
export function editAdded(operations: Op[], into: number, entry: Entry, item: unknown): Op[] {
	const found = addOf(operations, into, entry);
	return operations.map((op) => (op === found ? { ...op, item } : op));
}

/** The current text of an added item that is a plain string (an Alias). */
export function addedItem(operations: Op[], into: number, entry: Entry): unknown {
	return addOf(operations, into, entry)?.item;
}

function setOf(operations: Op[], into: number, field: string): Op | undefined {
	return operations.find((op) => op.op === 'set' && op.target === into && op.field === field);
}

/** Whether the survivor takes the folded record's value of the field. */
export function usesSourceField(operations: Op[], into: number, field: string): boolean {
	return setOf(operations, into, field) !== undefined;
}

/** The survivor keeps its own value, or takes the folded record's. */
export function chooseField(
	operations: Op[],
	into: number,
	field: string,
	value: unknown,
	useSource: boolean
): Op[] {
	if (usesSourceField(operations, into, field) === useSource) return operations;
	if (!useSource) return operations.filter((op) => op !== setOf(operations, into, field));
	return insertBeforeMerge(operations, { op: 'set', target: into, field, value });
}

function changeOf(
	operations: Op[],
	into: number,
	collection: string,
	key: unknown
): Op | undefined {
	return operations.find(
		(op) =>
			op.op === 'change' &&
			op.target === into &&
			op.collection === collection &&
			same(keyOf(collection, op.item), key)
	);
}

/** Whether the survivor takes the folded record's Attribution to the Artist. */
export function usesSourceAttribution(operations: Op[], into: number, artist: unknown): boolean {
	return changeOf(operations, into, 'attributions', artist) !== undefined;
}

export function chooseAttribution(
	operations: Op[],
	into: number,
	artist: unknown,
	item: unknown,
	useSource: boolean
): Op[] {
	if (usesSourceAttribution(operations, into, artist) === useSource) return operations;
	if (!useSource) {
		return operations.filter((op) => op !== changeOf(operations, into, 'attributions', artist));
	}
	return insertBeforeMerge(operations, {
		op: 'change',
		target: into,
		collection: 'attributions',
		item
	});
}

/** The kinds of History event that the merged result would hold: how many Creation events. */
export function creationEvents(operations: Op[], into: number, entries: Entry[]): number {
	return entries.filter(
		(entry) =>
			entry.collection === 'history_events' &&
			(entry.item as { type?: string }).type === 'created' &&
			isKept(operations, into, entry)
	).length;
}

// Unmerge.

/** The operations that point a record back to the restored one. */
export function repointing(operations: Op[], record: number): Op[] {
	return operations.filter((op) => !isMerge(op) && op.target === record);
}

export function isRepointed(operations: Op[], record: number): boolean {
	return repointing(operations, record).length > 0;
}

/**
 * Point a record back, or leave it where it is. `initial` is the changeset the Unmerge was
 * started with, which holds the operations to restore.
 */
export function setRepointed(
	operations: Op[],
	initial: Op[],
	record: number,
	point: boolean
): Op[] {
	if (isRepointed(operations, record) === point) return operations;
	if (!point) return operations.filter((op) => isMerge(op) || op.target !== record);
	return initial
		.filter((op) => !isMerge(op) && op.target === record)
		.reduce((all, op) => insertBeforeMerge(all, op), operations);
}
