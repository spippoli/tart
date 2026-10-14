import { m } from '#lib/paraglide/messages.js';
import { conditionWord } from '#lib/archive/records.ts';
import type { Locale } from '#lib/paraglide/runtime.js';
import { CONDITION_GROUPS, queryString, type FilterState } from './state';

/** One active filter: what it says, and the state without it. */
export interface Chip {
	id: string;
	/** The visible text. */
	label: string;
	/** The state with this filter removed. */
	remaining: FilterState;
	/** The accessible name of the removal link. */
	removeLabel: string;
}

export interface ChipNames {
	locale: Locale;
	type: (key: string) => string;
	area: (id: number) => string;
	artist: string | null;
	series: string | null;
}

const groupName: Record<string, () => string> = {
	present: m.discovery_group_present,
	disappeared: m.discovery_group_disappeared,
	unknown: m.discovery_group_unknown
};

function range(from: number | null, to: number | null): string {
	if (from !== null && to !== null) return m.discovery_range_between({ from, to });
	return from !== null ? m.discovery_range_from({ from }) : m.discovery_range_to({ to: to ?? 0 });
}

/**
 * The active filters as removable chips (Discovery spec, Applying filters). A complete
 * Condition group is one chip; otherwise each selected Condition has its own.
 */
export function chipsOf(state: FilterState, names: ChipNames): Chip[] {
	const chips: Chip[] = [];
	const add = (id: string, label: string, remaining: Partial<FilterState>, name = label) =>
		chips.push({
			id,
			label,
			remaining: { ...state, ...remaining, page: 1 },
			removeLabel: m.discovery_chip_remove({ filter: name })
		});

	if (state.q) {
		add(
			'q',
			m.discovery_chip_search({ text: state.q }),
			{ q: null, order: state.order === 'relevance' ? null : state.order },
			m.discovery_chip_search({ text: state.q })
		);
	}
	if (state.condition.length > 0) {
		const complete = CONDITION_GROUPS.filter(({ conditions }) =>
			conditions.every((condition) => state.condition.includes(condition))
		);
		for (const { group, conditions } of complete) {
			add(
				`group-${group}`,
				m.discovery_chip_group({ name: groupName[group]() }),
				{ condition: state.condition.filter((condition) => !conditions.includes(condition)) },
				groupName[group]()
			);
		}
		const grouped = complete.flatMap(({ conditions }) => conditions);
		const rest = state.condition.filter((condition) => !grouped.includes(condition));
		for (const condition of rest) {
			const word = conditionWord(condition, names.locale);
			add(
				`condition-${condition}`,
				m.discovery_chip_condition({ name: word }),
				{ condition: state.condition.filter((other) => other !== condition) },
				word
			);
		}
	}
	for (const type of state.type) {
		const label = names.type(type);
		add(
			`type-${type}`,
			m.discovery_chip_type({ name: label }),
			{
				type: state.type.filter((other) => other !== type)
			},
			label
		);
	}
	for (const id of state.area) {
		const label = m.discovery_chip_area({ name: names.area(id) });
		add(`area-${id}`, label, { area: state.area.filter((other) => other !== id) });
	}
	for (const value of state.attribution) {
		const label = {
			unknown: m.discovery_attribution_unknown,
			attributed: m.discovery_attribution_attributed,
			disputed: m.discovery_attribution_disputed
		}[value]();
		add(
			`attribution-${value}`,
			m.discovery_chip_attribution({ name: label }),
			{
				attribution: state.attribution.filter((other) => other !== value)
			},
			label
		);
	}
	if (state.artist !== null) {
		const name = names.artist ?? String(state.artist);
		add('artist', m.discovery_chip_artist({ name }), { artist: null });
	}
	if (state.series !== null) {
		const name = names.series ?? String(state.series);
		add('series', m.discovery_chip_series({ name }), { series: null });
	}
	if (state.documentedFrom !== null || state.documentedTo !== null) {
		add(
			'documented',
			m.discovery_chip_documented({ range: range(state.documentedFrom, state.documentedTo) }),
			{ documentedFrom: null, documentedTo: null }
		);
	}
	if (state.createdFrom !== null || state.createdTo !== null) {
		add('created', m.discovery_chip_created({ range: range(state.createdFrom, state.createdTo) }), {
			createdFrom: null,
			createdTo: null
		});
	}
	return chips;
}

/** The state with no filter at all; the order, the selection, and the viewport stay. */
export function cleared(state: FilterState): FilterState {
	return {
		...state,
		q: null,
		order: state.order === 'relevance' ? null : state.order,
		condition: [],
		type: [],
		area: [],
		attribution: [],
		artist: null,
		series: null,
		documentedFrom: null,
		documentedTo: null,
		createdFrom: null,
		createdTo: null,
		page: 1
	};
}

export function hrefOf(path: string, state: FilterState, locale: Locale): string {
	return path + queryString(state, locale);
}
