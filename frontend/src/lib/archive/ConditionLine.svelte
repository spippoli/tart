<script lang="ts">
	import { m } from '#lib/paraglide/messages.js';
	import ConditionSign from './ConditionSign.svelte';
	import { archiveContext } from './context.svelte';
	import {
		archiveDate,
		conditionWord,
		evidenceWords,
		type ApiDate,
		type ConditionView
	} from './records';

	/**
	 * A Condition, never without a date (ADR 0015): "Missing · since c. 2019 · last
	 * documented 3 Mar 2018", or "Unknown · state not documented". With `evidence`,
	 * the Evidence level of the event that sets it follows.
	 */
	let {
		condition,
		lastDocumented,
		evidence = false,
		sources = 0
	}: {
		condition: ConditionView;
		lastDocumented: ApiDate | null | undefined;
		evidence?: boolean;
		sources?: number;
	} = $props();
	const context = archiveContext();
	const parts = $derived.by(() => {
		const words = [conditionWord(condition.condition, context.locale)];
		if (!condition.since) {
			words.push(m.archive_condition_not_documented());
			return words;
		}
		words.push(m.archive_condition_since({ date: archiveDate(condition.since, context.dates) }));
		if (lastDocumented) {
			words.push(m.archive_last_documented({ date: archiveDate(lastDocumented, context.dates) }));
		}
		if (evidence && condition.evidence_level) {
			words.push(evidenceWords(condition.evidence_level, sources, context.locale));
		}
		return words;
	});
</script>

<span class="condition"><ConditionSign group={condition.group} />{parts.join(' · ')}</span>
