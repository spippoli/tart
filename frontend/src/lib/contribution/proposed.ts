/**
 * The proposed data of a Submission, read from a round's snapshot (Contribution and
 * moderation spec, Submission page). A snapshot is `{"operations": [...]}`, the JSON form
 * of the archive's changeset (ADR 0007): this turns each operation into rows of
 * `name: text` that a page can show in words.
 */

export type OperationType = 'create' | 'set' | 'add' | 'change' | 'remove';

export interface ProposedOperation {
	type: OperationType;
	/** The kind of the new record (`create`), a collection (`add`, `change`, `remove`), or a field (`set`). */
	subject: string;
	/** The values the operation proposes, as `[name, text]`. */
	entries: [string, string][];
}

/** A value as text: scalars as they are, anything structured as compact JSON. */
export function describeValue(value: unknown): string {
	if (value === null || value === undefined) return '';
	if (typeof value === 'string') return value;
	if (typeof value === 'number' || typeof value === 'boolean') return String(value);
	return JSON.stringify(value);
}

function entriesOf(value: unknown, fallbackName: string): [string, string][] {
	if (typeof value !== 'object' || value === null || Array.isArray(value)) {
		return [[fallbackName, describeValue(value)]];
	}
	return Object.entries(value)
		.filter(([, each]) => each !== null && !(Array.isArray(each) && each.length === 0))
		.map(([name, each]): [string, string] => [name, describeValue(each)]);
}

export function operationOf(raw: unknown): ProposedOperation | null {
	if (typeof raw !== 'object' || raw === null) return null;
	const operation = raw as Record<string, unknown>;
	switch (operation.op) {
		case 'create':
			return {
				type: 'create',
				subject: String(operation.kind ?? ''),
				entries: entriesOf(operation.record, 'record')
			};
		case 'set':
			return {
				type: 'set',
				subject: String(operation.field ?? ''),
				entries: [[String(operation.field ?? ''), describeValue(operation.value)]]
			};
		case 'add':
		case 'change':
			return {
				type: operation.op,
				subject: String(operation.collection ?? ''),
				entries: entriesOf(operation.item, String(operation.collection ?? ''))
			};
		case 'remove':
			return {
				type: 'remove',
				subject: String(operation.collection ?? ''),
				entries: [[String(operation.collection ?? ''), describeValue(operation.key)]]
			};
		default:
			return null;
	}
}

/** The operations of a snapshot; anything that is not an operation is left out. */
export function proposedOperations(snapshot: unknown): ProposedOperation[] {
	if (typeof snapshot !== 'object' || snapshot === null) return [];
	const operations = (snapshot as { operations?: unknown }).operations;
	if (!Array.isArray(operations)) return [];
	return operations.flatMap((each) => operationOf(each) ?? []);
}
