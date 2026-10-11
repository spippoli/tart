/**
 * Display of Uncertain dates and periods (archive-records spec, ADR 0008, ADR 0015).
 *
 * Each precision x qualifier combination has its own message, so every UI language
 * can word it naturally; the date inside it is formatted by `Intl` in the UI
 * language and the Instance time zone. The archive domain (backend) owns the
 * validation, the derived range, and the chronological key.
 */
import { m } from '#lib/paraglide/messages.js';
import type { Locale } from '#lib/paraglide/runtime.js';

export const precisions = ['day', 'month', 'year', 'decade', 'unknown'] as const;
export const qualifiers = ['exact', 'circa', 'before', 'after'] as const;

export type Precision = (typeof precisions)[number];
export type KnownPrecision = Exclude<Precision, 'unknown'>;
export type Qualifier = (typeof qualifiers)[number];

/**
 * An Uncertain date as the archive stores it. Each value is an ISO calendar date,
 * the first day of the unit it names (`2016-03-01` is March 2016 at `month`
 * precision); `second` is present only with `exact`.
 */
export type UncertainDate =
	| { precision: 'unknown' }
	| {
			precision: KnownPrecision;
			qualifier: Qualifier;
			first: string;
			second?: string | null;
	  };

export interface Period {
	start?: UncertainDate | null;
	end?: UncertainDate | null;
}

export interface DateFormatContext {
	locale: Locale;
	/** The Instance time zone (IANA name). */
	timeZone: string;
}

type Options = { locale: Locale };
type SingleMessage = (inputs: { date: string }, options: Options) => string;

const singleMessages: Record<KnownPrecision, Record<Qualifier, SingleMessage>> = {
	day: {
		exact: m.uncertain_date_day_exact,
		circa: m.uncertain_date_day_circa,
		before: m.uncertain_date_day_before,
		after: m.uncertain_date_day_after
	},
	month: {
		exact: m.uncertain_date_month_exact,
		circa: m.uncertain_date_month_circa,
		before: m.uncertain_date_month_before,
		after: m.uncertain_date_month_after
	},
	year: {
		exact: m.uncertain_date_year_exact,
		circa: m.uncertain_date_year_circa,
		before: m.uncertain_date_year_before,
		after: m.uncertain_date_year_after
	},
	decade: {
		exact: m.uncertain_date_decade_exact,
		circa: m.uncertain_date_decade_circa,
		before: m.uncertain_date_decade_before,
		after: m.uncertain_date_decade_after
	}
};

const rangeMessages: Record<
	Exclude<KnownPrecision, 'decade'>,
	(inputs: { range: string }, options: Options) => string
> = {
	day: m.uncertain_date_day_exact_range,
	month: m.uncertain_date_month_exact_range,
	year: m.uncertain_date_year_exact_range
};

const precisionLabels: Record<Precision, (inputs: object, options: Options) => string> = {
	day: m.uncertain_date_precision_day,
	month: m.uncertain_date_precision_month,
	year: m.uncertain_date_precision_year,
	decade: m.uncertain_date_precision_decade,
	unknown: m.uncertain_date_precision_unknown
};

const qualifierLabels: Record<Qualifier, (inputs: object, options: Options) => string> = {
	exact: m.uncertain_date_qualifier_exact,
	circa: m.uncertain_date_qualifier_circa,
	before: m.uncertain_date_qualifier_before,
	after: m.uncertain_date_qualifier_after
};

const intlFields: Record<KnownPrecision, Intl.DateTimeFormatOptions> = {
	day: { day: 'numeric', month: 'short', year: 'numeric' },
	month: { month: 'long', year: 'numeric' },
	year: { year: 'numeric' },
	// A decade is named by its first year; its message adds the rest ("1990s", "anni 1990").
	decade: { year: 'numeric' }
};

/**
 * The instant at noon of a calendar day in the time zone, so that `Intl` shows that
 * same day there. Noon keeps clear of midnight and of daylight-saving changes.
 */
function noonIn(isoDate: string, timeZone: string): Date {
	const [year, month, day] = isoDate.split('-').map(Number);
	const noonUtc = Date.UTC(year, month - 1, day, 12);
	const parts = Object.fromEntries(
		new Intl.DateTimeFormat('en-US', {
			timeZone,
			hourCycle: 'h23',
			year: 'numeric',
			month: 'numeric',
			day: 'numeric',
			hour: 'numeric',
			minute: 'numeric'
		})
			.formatToParts(noonUtc)
			.map(({ type, value }) => [type, Number(value)])
	);
	const offset =
		Date.UTC(parts.year, parts.month - 1, parts.day, parts.hour, parts.minute) - noonUtc;
	return new Date(noonUtc - offset);
}

export function formatUncertainDate(
	date: UncertainDate,
	{ locale, timeZone }: DateFormatContext
): string {
	if (date.precision === 'unknown') return m.uncertain_date_unknown({}, { locale });
	const { precision, qualifier, first, second } = date;
	const intl = new Intl.DateTimeFormat(locale, { ...intlFields[precision], timeZone });
	const from = noonIn(first, timeZone);
	if (second && qualifier === 'exact') {
		const to = noonIn(second, timeZone);
		if (precision === 'decade') {
			return m.uncertain_date_decade_exact_range(
				{ from: intl.format(from), to: intl.format(to) },
				{ locale }
			);
		}
		return rangeMessages[precision]({ range: intl.formatRange(from, to) }, { locale });
	}
	return singleMessages[precision][qualifier]({ date: intl.format(from) }, { locale });
}

/** "from …", "until …", or both ends; `null` when the period has neither. */
export function formatPeriod({ start, end }: Period, context: DateFormatContext): string | null {
	const options = { locale: context.locale };
	if (start && end) {
		return m.period_range(
			{ start: formatUncertainDate(start, context), end: formatUncertainDate(end, context) },
			options
		);
	}
	if (start) return m.period_from({ start: formatUncertainDate(start, context) }, options);
	if (end) return m.period_until({ end: formatUncertainDate(end, context) }, options);
	return null;
}

export function precisionLabel(precision: Precision, locale: Locale): string {
	return precisionLabels[precision]({}, { locale });
}

export function qualifierLabel(qualifier: Qualifier, locale: Locale): string {
	return qualifierLabels[qualifier]({}, { locale });
}
