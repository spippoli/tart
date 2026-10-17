/**
 * The rows of the "current and proposed" list of the Submission page: each operation of a
 * round in words, with what it changes as the archive has it now (the API's comparison, by
 * the operation's position in the round).
 */
import { describeValue, operationOf, type ProposedOperation } from '#lib/contribution/proposed.ts';
import { operationsOf } from './rounds';

export interface OperationRow {
	operation: ProposedOperation;
	/** What the operation replaces, as text; `null` when it has no current value. */
	current: string | null;
	/** Whether the operation changes something that exists now (a field or an item). */
	compared: boolean;
	/** Set when comparing two rounds: the operation was not in the previous one. */
	fresh?: boolean;
}

export function operationRows(
	snapshot: unknown,
	currents: readonly { index: number; current?: unknown }[],
	fresh?: readonly boolean[]
): OperationRow[] {
	const byIndex = new Map(currents.map((each) => [each.index, each.current]));
	return operationsOf(snapshot).flatMap((raw, index) => {
		const operation = operationOf(raw);
		if (!operation) return [];
		const current = byIndex.get(index);
		return [
			{
				operation,
				current: current === null || current === undefined ? null : describeValue(current),
				compared: byIndex.has(index),
				fresh: fresh?.[index]
			}
		];
	});
}
